import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.lead import Lead
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage
from app.schemas.whatsapp import MessageCreate, MessageTemplateCreate, MessageOut
from app.services.meta_whatsapp import send_meta_whatsapp_message

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

@router.post("/send", response_model=MessageOut, status_code=201)
async def send_whatsapp_message(payload: MessageCreate, db: AsyncSession = Depends(get_db)):
    conv_id, target_phone = payload.conversation_id, payload.phone_number
    if conv_id:
        conv = (await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.id == conv_id))).scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        target_phone = conv.phone_number
    elif target_phone:
        conv = (await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.phone_number == target_phone))).scalar_one_or_none()
        if not conv:
            lead = (await db.execute(select(Lead).where(Lead.phone == target_phone))).scalar_one_or_none()
            conv = WhatsAppConversation(lead_id=lead.id if lead else None, phone_number=target_phone, unread_count=0)
            db.add(conv)
            await db.flush()
        conv_id = conv.id
    else:
        raise HTTPException(status_code=400, detail="conversation_id or phone_number is required")

    meta_res = await send_meta_whatsapp_message(target_phone, {"type": "text", "text": {"preview_url": False, "body": payload.content}})
    ext_id = meta_res.get("messages", [{}])[0].get("id")
    msg = WhatsAppMessage(conversation_id=conv_id, sender="agent", content=payload.content, message_type="text", media_url=payload.media_url, status="sent", external_message_id=ext_id)
    db.add(msg)
    await db.execute(update(WhatsAppConversation).where(WhatsAppConversation.id == conv_id).values(last_message_at=datetime.now(timezone.utc)))
    await db.commit()
    await db.refresh(msg)
    return msg

@router.post("/send-template", response_model=MessageOut, status_code=201)
async def send_whatsapp_template(payload: MessageTemplateCreate, db: AsyncSession = Depends(get_db)):
    conv = (await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.phone_number == payload.phone_number))).scalar_one_or_none()
    if not conv:
        conv = WhatsAppConversation(phone_number=payload.phone_number, unread_count=0)
        db.add(conv)
        await db.flush()
    meta_payload = {"type": "template", "template": {"name": payload.template_name, "language": {"code": payload.language_code or "en_US"}, "components": payload.components or []}}
    meta_res = await send_meta_whatsapp_message(payload.phone_number, meta_payload)
    ext_id = meta_res.get("messages", [{}])[0].get("id")
    msg = WhatsAppMessage(conversation_id=conv.id, sender="agent", content=f"[Template: {payload.template_name}]", message_type="template", status="sent", external_message_id=ext_id)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
