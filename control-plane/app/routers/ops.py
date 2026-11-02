from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.db import get_db
from app.deps import get_current_admin
from app.models import AdminUser, AuditLog, Operation
from app.schemas import HealthOut, OperationOut

router = APIRouter(tags=["ops"])


@router.get("/health", response_model=HealthOut)
async def health(db: Annotated[AsyncSession, Depends(get_db)]) -> HealthOut:
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return HealthOut(
        status="ok" if db_ok else "degraded",
        version=__version__,
        database=db_ok,
    )


@router.get("/ready", response_model=HealthOut)
async def ready(db: Annotated[AsyncSession, Depends(get_db)]) -> HealthOut:
    return await health(db)


@router.get("/operations", response_model=list[OperationOut])
async def list_operations(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[AdminUser, Depends(get_current_admin)],
) -> list[Operation]:
    result = await db.execute(select(Operation).order_by(Operation.created_at.desc()).limit(100))
    return list(result.scalars().all())


@router.get("/operations/{op_id}", response_model=OperationOut)
async def get_operation(
    op_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[AdminUser, Depends(get_current_admin)],
) -> Operation:
    result = await db.execute(select(Operation).where(Operation.id == op_id))
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")
    return op


@router.get("/audit")
async def list_audit(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[AdminUser, Depends(get_current_admin)],
) -> list[dict]:
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100))
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "actor_type": r.actor_type,
            "actor_id": r.actor_id,
            "action": r.action,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "source_ip": r.source_ip,
            "request_id": r.request_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
