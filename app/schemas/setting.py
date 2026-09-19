from typing import Dict, Any
from pydantic import BaseModel

class SettingUpdate(BaseModel):
    key: str
    value: Dict[str, Any]
