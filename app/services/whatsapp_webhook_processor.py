from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.phone import normalize_phone_number
from app.models.campaign import CampaignRecipient
from app.models.lead import Lead
from app.models.notification import Notification
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage


async def handle_webhook_statuses(
    statuses: List[Dict[str, Any]], db: AsyncSession
) -> None:
    for st in statuses:
        ext_id, new_status = st.get("id"), st.get("status")
        if ext_id and new_status:
            await db.execute(
                update(WhatsAppMessage)
                .where(WhatsAppMessage.external_message_id == ext_id)
                .values(status=new_status)
            )
            await db.execute(
                update(CampaignRecipient)
                .where(CampaignRecipient.external_message_id == ext_id)
                .values(status=new_status)
            )


async def handle_webhook_messages(
    messages: List[Dict[str, Any]], db: AsyncSession
) -> None:
    for m in messages:
        msg_id, raw_sender_phone = m.get("id"), m.get("from")
        if not raw_sender_phone:
            continue

        try:
            norm_sender_phone = normalize_phone_number(raw_sender_phone)
        except Exception:
            norm_sender_phone = (
                f"+{raw_sender_phone}"
                if not raw_sender_phone.startswith("+")
                else raw_sender_phone
            )

        msg_type = m.get("type", "text")
        text_body = (
            m.get("text", {}).get("body", "")
            if msg_type == "text"
            else f"[{msg_type} received]"
        )

        # Check for deduplication of incoming message by external_message_id
        if (
            await db.execute(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.external_message_id == msg_id
                )
            )
        ).scalar_one_or_none():
            continue

        # Find existing conversation by normalized phone number
        conv = (
            await db.execute(
                select(WhatsAppConversation).where(
                    WhatsAppConversation.phone_number == norm_sender_phone
                )
            )
        ).scalar_one_or_none()

        if not conv:
            # Match lead by normalized phone number to prevent duplicate leads
            lead = (
                await db.execute(
                    select(Lead).where(Lead.phone == norm_sender_phone)
                )
            ).scalar_one_or_none()

            if not lead:
                lead = Lead(
                    name=f"WhatsApp User ({norm_sender_phone})",
                    phone=norm_sender_phone,
                    source="whatsapp",
                )
                db.add(lead)
                await db.flush()

            conv = WhatsAppConversation(
                lead_id=lead.id,
                phone_number=norm_sender_phone,
                unread_count=1,
            )
            db.add(conv)
            await db.flush()
        else:
            conv.unread_count += 1
            conv.last_message_at = datetime.now(timezone.utc)

        db.add(
            WhatsAppMessage(
                conversation_id=conv.id,
                sender="user",
                content=text_body,
                message_type=msg_type,
                status="delivered",
                external_message_id=msg_id,
            )
        )
        db.add(
            Notification(
                title="New WhatsApp Message",
                message=f"Received from {norm_sender_phone}: {text_body[:50]}",
                event_type="whatsapp_incoming",
                data={
                    "conversation_id": str(conv.id),
                    "phone": norm_sender_phone,
                },
            )
        )
