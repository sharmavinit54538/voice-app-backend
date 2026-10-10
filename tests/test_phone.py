import pytest
from app.core.exceptions import InvalidPhoneNumberError
from app.core.phone import is_valid_phone_number, normalize_phone_number
from app.schemas.call import CallCreate
from app.schemas.campaign import CampaignRecipientCreate
from app.schemas.lead import LeadCreate
from app.schemas.whatsapp import MessageCreate, MessageTemplateCreate


def test_normalize_valid_indian_formats():
    expected = "+919876543210"

    # Standard 10 digit
    assert normalize_phone_number("9876543210") == expected

    # With +91
    assert normalize_phone_number("+919876543210") == expected

    # With 91 without plus
    assert normalize_phone_number("919876543210") == expected

    # With leading zero
    assert normalize_phone_number("09876543210") == expected

    # With spaces
    assert normalize_phone_number("+91 98765 43210") == expected
    assert normalize_phone_number("98765 43210") == expected

    # With dashes
    assert normalize_phone_number("+91-98765-43210") == expected
    assert normalize_phone_number("987-654-3210") == expected

    # With brackets and dots
    assert normalize_phone_number("(+91) 98765-43210") == expected
    assert normalize_phone_number("987.654.3210") == expected

    # Starting with 6, 7, 8, 9
    assert normalize_phone_number("6123456789") == "+916123456789"
    assert normalize_phone_number("7123456789") == "+917123456789"
    assert normalize_phone_number("8123456789") == "+918123456789"


def test_normalize_valid_international_formats():
    # US E.164
    assert normalize_phone_number("+14155552671") == "+14155552671"
    assert normalize_phone_number("+1 (415) 555-2671") == "+14155552671"

    # UK E.164
    assert normalize_phone_number("+447911123456") == "+447911123456"

    # With 00 international prefix
    assert normalize_phone_number("0014155552671") == "+14155552671"


def test_normalize_invalid_formats():
    invalid_numbers = [
        "",
        "   ",
        "abc1234567",
        "98765abcde",
        "+91 98765 #4321",
        "12345",  # too short
        "+91 12345",  # Indian number too short
        "+91 98765432109999",  # too long
        "1234567890",  # Indian number starting with 1
        "01234567890",  # Indian leading 0 starting with 1
        "911234567890",  # Indian 91 prefix starting with 1
    ]

    for inv in invalid_numbers:
        assert not is_valid_phone_number(inv)
        with pytest.raises(InvalidPhoneNumberError):
            normalize_phone_number(inv)


def test_pydantic_schema_phone_normalization():
    # LeadCreate schema
    lead = LeadCreate(name="Raj Sharma", phone=" 98765-43210 ")
    assert lead.phone == "+919876543210"

    # CallCreate schema
    call = CallCreate(
        phone_number="09876543210", direction="outbound", status="ongoing"
    )
    assert call.phone_number == "+919876543210"

    # CampaignRecipientCreate schema
    rec = CampaignRecipientCreate(phone_number="919876543210")
    assert rec.phone_number == "+919876543210"

    # MessageCreate schema
    msg = MessageCreate(phone_number="+91 98765 43210", content="Hello")
    assert msg.phone_number == "+919876543210"

    # MessageTemplateCreate schema
    tpl = MessageTemplateCreate(
        phone_number="9876543210", template_name="hello_world"
    )
    assert tpl.phone_number == "+919876543210"
