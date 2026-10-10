from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_API_VERSION,
    WHATSAPP_PHONE_NUMBER_ID,
)
from app.core.phone import normalize_phone_number


async def send_meta_whatsapp_message(
    to_phone: str, payload_data: dict
) -> dict[str, Any]:
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp Cloud API credentials are not configured.",
        )

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    norm_phone = normalize_phone_number(to_phone)
    # Meta WhatsApp Cloud API expects country code + number without '+'
    clean_phone = norm_phone.lstrip("+")
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        **payload_data,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, headers=headers, json=body)
        res_data = response.json()
        if response.status_code not in (200, 201):
            error_msg = res_data.get("error", {}).get("message", response.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Meta WhatsApp API Error: {error_msg}",
            )
        return res_data
