from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.phone import normalize_phone_number
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage
from app.schemas.whatsapp import MessageOut, MessageTemplateCreate
from app.services.meta_whatsapp import send_meta_whatsapp_message

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])


@router.post("/send-template", response_model=MessageOut, status_code=201)
async def send_whatsapp_template(
    payload: MessageTemplateCreate, db: AsyncSession = Depends(get_db)
) -> WhatsAppMessage:
    norm_phone = normalize_phone_number(payload.phone_number)
    conv = (
        await db.execute(
            select(WhatsAppConversation).where(
                WhatsAppConversation.phone_number == norm_phone
            )
        )
    ).scalar_one_or_none()
    if not conv:
        conv = WhatsAppConversation(
            phone_number=norm_phone, unread_count=0
        )
        db.add(conv)
        await db.flush()
    meta_payload = {
        "type": "template",
        "template": {
            "name": payload.template_name,
            "language": {"code": payload.language_code or "en_US"},
            "components": payload.components or [],
        },
    }
    meta_res = await send_meta_whatsapp_message(norm_phone, meta_payload)
    ext_id = meta_res.get("messages", [{}])[0].get("id")
    msg = WhatsAppMessage(
        conversation_id=conv.id,
        sender="agent",
        content=f"[Template: {payload.template_name}]",
        message_type="template",
        status="sent",
        external_message_id=ext_id,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
