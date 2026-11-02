from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_admin
from app.models import AdminUser, ExitNode, ExitStatus, VpngateCandidate
from app.schemas import ExitNodeOut, ExitNodeUpdate
from app.services.exit_provision import provision_exit

router = APIRouter(prefix="/exits", tags=["exits"])


@router.get("", response_model=list[ExitNodeOut])
async def list_exits(db: Annotated[AsyncSession, Depends(get_db)], admin: Annotated[AdminUser, Depends(get_current_admin)]):
    result = await db.execute(select(ExitNode).order_by(ExitNode.created_at.desc()))
    return result.scalars().all()


@router.post("/sync")
async def sync_vpngate(db: Annotated[AsyncSession, Depends(get_db)], admin: Annotated[AdminUser, Depends(get_current_admin)]):
    from app.services.vpngate import sync_candidates
    count = await sync_candidates(db)
    return {"synced": count}


@router.post("/{exit_id}/provision")
async def provision(exit_id: UUID, db: Annotated[AsyncSession, Depends(get_db)], admin: Annotated[AdminUser, Depends(get_current_admin)]):
    exit_node = await db.get(ExitNode, exit_id)
    if not exit_node:
        raise HTTPException(404, "Exit not found")
    op = await provision_exit(db, exit_node)
    return {"operation_id": str(op.id), "status": op.status}


@router.patch("/{exit_id}", response_model=ExitNodeOut)
async def update_exit(exit_id: UUID, req: ExitNodeUpdate, db: Annotated[AsyncSession, Depends(get_db)], admin: Annotated[AdminUser, Depends(get_current_admin)]):
    exit_node = await db.get(ExitNode, exit_id)
    if not exit_node:
        raise HTTPException(404)
    if req.name is not None:
        exit_node.name = req.name
    if req.status is not None:
        exit_node.status = req.status
    await db.commit()
    await db.refresh(exit_node)
    return exit_node
