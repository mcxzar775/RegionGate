from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_admin
from app.models import AdminUser, Device, DeviceCredential, EnrollmentCode, Session
from app.schemas import (
    DeviceEnrollRequest,
    DeviceEnrollResponse,
    DeviceOut,
    EnrollmentCodeCreateResponse,
    LoginRequest,
    TokenResponse,
)
from app.security import create_access_token, create_refresh_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
devices_router = APIRouter(prefix="/devices", tags=["devices"])
enrollment_router = APIRouter(prefix="/enrollment", tags=["enrollment"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(AdminUser).where(AdminUser.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    settings = get_settings()
    access = create_access_token(str(user.id), "admin")
    refresh = create_refresh_token(str(user.id), "admin")
    db.add(Session(admin_user_id=user.id, refresh_token_hash=hash_password(refresh), expires_at=datetime.now(timezone.utc) + timedelta(days=30)))
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=settings.access_token_expire_minutes * 60)


@enrollment_router.post("/codes", response_model=EnrollmentCodeCreateResponse)
async def create_enrollment_code(db: Annotated[AsyncSession, Depends(get_db)], admin: Annotated[AdminUser, Depends(get_current_admin)]):
    settings = get_settings()
    code = secrets.token_urlsafe(16)
    db.add(EnrollmentCode(code_hash=hash_password(code), expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.enrollment_code_ttl_minutes), created_by=admin.id))
    await db.commit()
    return EnrollmentCodeCreateResponse(code=code, expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.enrollment_code_ttl_minutes))


@devices_router.post("/enroll", response_model=DeviceEnrollResponse)
async def enroll_device(req: DeviceEnrollRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(EnrollmentCode).where(EnrollmentCode.code_hash == hash_password(req.code)))
    code = result.scalar_one_or_none()
    if not code or code.used_at or code.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    device = Device(public_identity=req.public_identity, name=req.name)
    db.add(device)
    await db.flush()
    code.used_at = datetime.now(timezone.utc)
    access = create_access_token(str(device.id), "device")
    refresh = create_refresh_token(str(device.id), "device")
    db.add(DeviceCredential(device_id=device.id, refresh_token_hash=hash_password(refresh), expires_at=datetime.now(timezone.utc) + timedelta(days=90)))
    await db.commit()
    return DeviceEnrollResponse(device_id=device.id, access_token=access, refresh_token=refresh)


@devices_router.get("", response_model=list[DeviceOut])
async def list_devices(db: Annotated[AsyncSession, Depends(get_db)], admin: Annotated[AdminUser, Depends(get_current_admin)]):
    result = await db.execute(select(Device))
    return result.scalars().all()
