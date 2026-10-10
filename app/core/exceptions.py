class AIServiceError(Exception):
    """Raised when an AI service (such as Google Gemini) encounters an error or is unconfigured."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvalidPhoneNumberError(ValueError):
    """Raised when a phone number cannot be parsed or validated into E.164 format."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
