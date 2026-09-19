import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import hash_password
from app.core.dependencies import require_owner
from app.models.user import User
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("", response_model=List[UserOut])
async def list_users(_: User = Depends(require_owner), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).order_by(User.created_at.desc()))
    return res.scalars().all()

@router.get("/{user_id}", response_model=UserOut)
async def get_user_by_id(user_id: uuid.UUID, _: User = Depends(require_owner), db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate, _: User = Depends(require_owner), db: AsyncSession = Depends(get_db)):
    if (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(
        email=payload.email, full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role if payload.role in ("OWNER", "ADMIN") else "ADMIN",
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
