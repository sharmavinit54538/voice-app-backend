from fastapi import APIRouter, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_owner
from app.models.setting import Setting
from app.models.user import User
from app.schemas.setting import SettingUpdate

router = APIRouter(prefix="/api/settings", tags=["Settings"])

@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Setting).where(Setting.is_sensitive == False))
    return {row.key: row.value for row in res.scalars().all()}

@router.patch("")
async def update_setting(
    payload: SettingUpdate,
    _: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Setting).where(Setting.key == payload.key))
    sett = res.scalar_one_or_none()
    if sett:
        sett.value = payload.value
    else:
        sett = Setting(key=payload.key, value=payload.value, is_sensitive=False)
        db.add(sett)
    await db.commit()
    return {"success": True, "setting": {sett.key: sett.value}}
