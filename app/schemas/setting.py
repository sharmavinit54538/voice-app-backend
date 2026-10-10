from typing import Any

from pydantic import BaseModel


class SettingUpdate(BaseModel):
    key: str
    value: dict[str, Any]
