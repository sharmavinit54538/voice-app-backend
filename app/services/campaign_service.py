import uuid
from datetime import datetime, timezone
from sqlalchemy import update
from sqlalchemy.future import select
from app.core.config import WHATSAPP_ACCESS_TOKEN
from app.core.database import AsyncSessionLocal
from app.models.campaign import Campaign, CampaignRecipient
from app.services.meta_whatsapp import send_meta_whatsapp_message

async def execute_campaign_task(c_id: uuid.UUID, template_name: str):
    async with AsyncSessionLocal() as session:
        rec_res = await session.execute(
            select(CampaignRecipient).where(
                CampaignRecipient.campaign_id == c_id,
                CampaignRecipient.status == "queued"
            )
        )
        recipients, delivered, failed = rec_res.scalars().all(), 0, 0
        for rec in recipients:
            try:
                if not WHATSAPP_ACCESS_TOKEN:
                    raise ValueError("WhatsApp API token is not configured")
                meta_payload = {
                    "type": "template",
                    "template": {
                        "name": template_name or "hello_world",
                        "language": {"code": "en_US"}
                    }
                }
                meta_res = await send_meta_whatsapp_message(rec.phone_number, meta_payload)
                rec.status = "sent"
                rec.external_message_id = meta_res.get("messages", [{}])[0].get("id")
                rec.sent_at = datetime.now(timezone.utc)
                delivered += 1
            except Exception as ex:
                rec.status, rec.error_message = "failed", str(ex)
                failed += 1
        await session.execute(
            update(Campaign).where(Campaign.id == c_id).values(
                delivered_count=Campaign.delivered_count + delivered,
                failed_count=Campaign.failed_count + failed,
                status="completed"
            )
        )
        await session.commit()
