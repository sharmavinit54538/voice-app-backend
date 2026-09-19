from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import WHATSAPP_VERIFY_TOKEN
from app.core.database import get_db
from app.services.whatsapp_webhook_processor import (
    handle_webhook_statuses, handle_webhook_messages
)

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

@router.get("/webhook")
async def verify_meta_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook verification token mismatch")

@router.get("/webhook/verify")
async def verify_meta_webhook_alias(request: Request):
    return await verify_meta_webhook(request)

@router.post("/webhook")
async def process_meta_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            val = change.get("value", {})
            if "statuses" in val:
                await handle_webhook_statuses(val.get("statuses", []), db)
            if "messages" in val:
                await handle_webhook_messages(val.get("messages", []), db)
    await db.commit()
    return {"status": "processed"}
