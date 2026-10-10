import re
from typing import Optional
from app.core.exceptions import InvalidPhoneNumberError


def normalize_phone_number(
    phone: Optional[str], default_country_code: str = "+91"
) -> str:
    """
    Normalises phone numbers to E.164 standard format.
    Default country: India (+91).

    Supported formats:
    - E.164 format: '+919876543210', '+14155552671'
    - Formatted with spaces, dashes, brackets: '+91 98765 43210', '+91-98765-43210', '(+91) 98765-43210'
    - Indian 10-digit local: '9876543210' -> '+919876543210'
    - Indian with leading 0: '09876543210' -> '+919876543210'
    - Indian with 91 prefix without plus: '919876543210' -> '+919876543210'
    - International with 00 prefix: '0014155552671' -> '+14155552671'

    Raises:
        InvalidPhoneNumberError: If the phone number is empty or cannot be converted to a valid E.164 number.
    """
    if not phone or not isinstance(phone, str):
        raise InvalidPhoneNumberError("Phone number cannot be empty.")

    cleaned = phone.strip()
    if not cleaned:
        raise InvalidPhoneNumberError("Phone number cannot be empty.")

    # Check for invalid characters (allowed: digits, +, -, (, ), ., space)
    if re.search(r"[^\d+\-().\s]", cleaned):
        raise InvalidPhoneNumberError(
            f"Invalid characters in phone number: '{phone}'"
        )

    # Strip formatting characters
    cleaned = re.sub(r"[\s\-().]", "", cleaned)

    # Handle 00 prefix for international
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]

    # If it starts with '+', validate international / E.164
    if cleaned.startswith("+"):
        digits_only = cleaned[1:]
        if not digits_only.isdigit():
            raise InvalidPhoneNumberError(
                f"Invalid phone number format: '{phone}'"
            )
        if len(digits_only) < 7 or len(digits_only) > 15:
            raise InvalidPhoneNumberError(
                f"Phone number must contain between 7 and 15 digits (E.164): '{phone}'"
            )

        # If it's an Indian number (+91...)
        if digits_only.startswith("91"):
            indian_local = digits_only[2:]
            if len(indian_local) != 10:
                raise InvalidPhoneNumberError(
                    f"Indian phone numbers must have 10 digits after +91, got {len(indian_local)}: '{phone}'"
                )
            if not re.match(r"^[6-9]\d{9}$", indian_local):
                raise InvalidPhoneNumberError(
                    f"Indian mobile number must start with 6, 7, 8, or 9: '{phone}'"
                )
            return f"+91{indian_local}"

        return f"+{digits_only}"

    # Only digits remain
    if not cleaned.isdigit():
        raise InvalidPhoneNumberError(f"Invalid phone number: '{phone}'")

    # Leading 0 (Indian 10-digit number with leading 0 e.g. 09876543210)
    if cleaned.startswith("0") and len(cleaned) == 11:
        indian_local = cleaned[1:]
        if re.match(r"^[6-9]\d{9}$", indian_local):
            return f"+91{indian_local}"
        raise InvalidPhoneNumberError(
            f"Invalid 10-digit Indian phone number starting with 0: '{phone}'"
        )

    # 12 digits starting with 91 (e.g. 919876543210)
    if len(cleaned) == 12 and cleaned.startswith("91"):
        indian_local = cleaned[2:]
        if re.match(r"^[6-9]\d{9}$", indian_local):
            return f"+91{indian_local}"
        raise InvalidPhoneNumberError(
            f"Invalid 10-digit Indian phone number starting with 91: '{phone}'"
        )

    # Standard 10-digit Indian mobile number (e.g. 9876543210)
    if len(cleaned) == 10:
        if re.match(r"^[6-9]\d{9}$", cleaned):
            return f"+91{cleaned}"
        raise InvalidPhoneNumberError(
            f"Indian 10-digit phone number must start with 6, 7, 8, or 9: '{phone}'"
        )

    # If it's 11-15 digits without '+', check if valid international
    if 11 <= len(cleaned) <= 15:
        return f"+{cleaned}"

    raise InvalidPhoneNumberError(
        f"Unable to parse phone number into E.164 format: '{phone}'"
    )


def is_valid_phone_number(phone: Optional[str]) -> bool:
    """Helper to check if a phone number can be normalized."""
    try:
        normalize_phone_number(phone)
        return True
    except (InvalidPhoneNumberError, ValueError):
        return False
