from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.lead import Lead
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage
from app.schemas.whatsapp import MessageMediaCreate, MessageOut
from app.services.meta_whatsapp import send_meta_whatsapp_message

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

@router.post("/send-media", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_whatsapp_media(payload: MessageMediaCreate, db: AsyncSession = Depends(get_db)):
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

    allowed_types = ["image", "video", "audio", "document"]
    mtype = payload.media_type.lower()
    if mtype not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid media_type. Must be one of {allowed_types}")

    media_obj = {"link": payload.media_url}
    if payload.caption and mtype in ["image", "video", "document"]:
        media_obj["caption"] = payload.caption

    meta_res = await send_meta_whatsapp_message(target_phone, {"type": mtype, mtype: media_obj})
    ext_id = meta_res.get("messages", [{}])[0].get("id")
    msg = WhatsAppMessage(conversation_id=conv_id, sender="agent", content=payload.caption or f"[{mtype} sent]", message_type=mtype, media_url=payload.media_url, status="sent", external_message_id=ext_id)
    db.add(msg)
    await db.execute(update(WhatsAppConversation).where(WhatsAppConversation.id == conv_id).values(last_message_at=datetime.now(timezone.utc)))
    await db.commit()
    await db.refresh(msg)
    return msg
