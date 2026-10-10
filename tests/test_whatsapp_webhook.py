import pytest
from httpx import AsyncClient
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage


@pytest.mark.asyncio
async def test_webhook_matches_existing_lead_with_normalized_phone(
    client: AsyncClient, db_session: AsyncSession
):
    # 1. Create a lead with standard normalised phone
    lead = Lead(
        name="Existing Client",
        phone="+919876543210",
        source="website",
    )
    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)

    # 2. Meta sends webhook with "from": "919876543210" (without '+')
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550234567",
                                "phone_number_id": "123456789",
                            },
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.HBgLMzk4NzY1NDMyMTAVAgASGBQz",
                                    "timestamp": "1710000000",
                                    "text": {"body": "Interested in 3BHK"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    response = await client.post("/api/whatsapp/webhook", json=payload)
    assert response.status_code == 200

    # 3. Verify no duplicate lead was created
    all_leads = (await db_session.execute(select(Lead))).scalars().all()
    assert len(all_leads) == 1
    assert all_leads[0].id == lead.id
    assert all_leads[0].name == "Existing Client"

    # 4. Verify conversation is linked to existing lead
    conv = (
        await db_session.execute(
            select(WhatsAppConversation).where(
                WhatsAppConversation.phone_number == "+919876543210"
            )
        )
    ).scalar_one_or_none()
    assert conv is not None
    assert conv.lead_id == lead.id

    # 5. Verify message was recorded
    msg = (
        await db_session.execute(
            select(WhatsAppMessage).where(
                WhatsAppMessage.conversation_id == conv.id
            )
        )
    ).scalar_one_or_none()
    assert msg is not None
    assert msg.content == "Interested in 3BHK"


@pytest.mark.asyncio
async def test_webhook_creates_new_lead_with_normalized_phone_if_not_exists(
    client: AsyncClient, db_session: AsyncSession
):
    # Meta sends incoming message from a new contact with leading 0 or unformatted
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "09876543210",
                                    "id": "wamid.NEW_MSG_001",
                                    "text": {"body": "Hi, need pricing details"},
                                    "type": "text",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    response = await client.post("/api/whatsapp/webhook", json=payload)
    assert response.status_code == 200

    # Verify lead was created with normalised phone (+919876543210)
    lead = (
        await db_session.execute(
            select(Lead).where(Lead.phone == "+919876543210")
        )
    ).scalar_one_or_none()
    assert lead is not None
    assert lead.phone == "+919876543210"
