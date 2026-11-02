"""FastAPI dependencies: DB session, current admin/device."""

from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AdminUser, Device
from app.security import try_decode_token

bearer = HTTPBearer(auto_error=False)
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_admin(
    db: DbSession,
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer)],
) -> AdminUser:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = try_decode_token(creds.credentials)
    if not payload or payload.get("type") != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(AdminUser).where(AdminUser.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    return user


async def get_current_device(
    db: DbSession,
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer)],
) -> Device:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = try_decode_token(creds.credentials)
    if not payload or payload.get("type") != "device":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    device_id = payload.get("sub")
    revoke_version = payload.get("rv", 0)
    if not device_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(Device).where(Device.id == UUID(device_id)))
    device = result.scalar_one_or_none()
    if not device or device.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device revoked")
    if device.revoke_version != revoke_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    return device


async def get_optional_admin_or_device(
    db: DbSession,
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer)],
) -> tuple[Optional[AdminUser], Optional[Device]]:
    if not creds:
        return None, None
    payload = try_decode_token(creds.credentials)
    if not payload:
        return None, None
    if payload.get("type") == "admin":
        result = await db.execute(select(AdminUser).where(AdminUser.id == UUID(payload["sub"])))
        return result.scalar_one_or_none(), None
    if payload.get("type") == "device":
        result = await db.execute(select(Device).where(Device.id == UUID(payload["sub"])))
        return None, result.scalar_one_or_none()
    return None, None


def require_if_match(revision: int, if_match: Optional[str] = Header(None, alias="If-Match")) -> None:
    if if_match is None:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="If-Match header required for concurrent updates",
        )
    # Accept both bare number and quoted ETag style
    cleaned = if_match.strip().strip('"')
    try:
        expected = int(cleaned)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid If-Match") from exc
    if expected != revision:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Revision conflict: expected {revision}, got {expected}",
        )
