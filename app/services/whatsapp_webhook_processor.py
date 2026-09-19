from datetime import datetime, timezone
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead
from app.models.campaign import CampaignRecipient
from app.models.notification import Notification
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage

async def handle_webhook_statuses(statuses: list, db: AsyncSession):
    for st in statuses:
        ext_id, new_status = st.get("id"), st.get("status")
        if ext_id and new_status:
            await db.execute(update(WhatsAppMessage).where(WhatsAppMessage.external_message_id == ext_id).values(status=new_status))
            await db.execute(update(CampaignRecipient).where(CampaignRecipient.external_message_id == ext_id).values(status=new_status))

async def handle_webhook_messages(messages: list, db: AsyncSession):
    for m in messages:
        msg_id, sender_phone = m.get("id"), m.get("from")
        msg_type = m.get("type", "text")
        text_body = m.get("text", {}).get("body", "") if msg_type == "text" else f"[{msg_type} received]"
        if (await db.execute(select(WhatsAppMessage).where(WhatsAppMessage.external_message_id == msg_id))).scalar_one_or_none():
            continue
        conv = (await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.phone_number == sender_phone))).scalar_one_or_none()
        if not conv:
            lead = (await db.execute(select(Lead).where(Lead.phone == sender_phone))).scalar_one_or_none()
            if not lead:
                lead = Lead(name=f"WhatsApp User ({sender_phone})", phone=sender_phone, source="whatsapp")
                db.add(lead)
                await db.flush()
            conv = WhatsAppConversation(lead_id=lead.id, phone_number=sender_phone, unread_count=1)
            db.add(conv)
            await db.flush()
        else:
            conv.unread_count += 1
            conv.last_message_at = datetime.now(timezone.utc)
        db.add(WhatsAppMessage(conversation_id=conv.id, sender="user", content=text_body, message_type=msg_type, status="delivered", external_message_id=msg_id))
        db.add(Notification(title="New WhatsApp Message", message=f"Received from {sender_phone}: {text_body[:50]}", event_type="whatsapp_incoming", data={"conversation_id": str(conv.id), "phone": sender_phone}))
