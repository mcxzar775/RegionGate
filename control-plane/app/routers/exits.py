from __future__ import annotations

import base64
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_admin
from app.models import (
    AdminUser,
    AuditLog,
    ExitNode,
    ExitStatus,
    Operation,
    VpngateCandidate,
)
from app.schemas import CandidateOut, ExitNodeOut, ExitNodeUpdate
from app.services.exit_provision import provision_exit
from app.services.vpngate import sync_candidates

router = APIRouter(prefix="/exits", tags=["exits"])


@router.get("", response_model=list[ExitNodeOut])
async def list_exits(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[AdminUser, Depends(get_current_admin)],
):
    result = await db.execute(select(ExitNode).order_by(ExitNode.created_at.desc()))
    return result.scalars().all()


@router.get("/candidates", response_model=list[CandidateOut])
async def list_candidates(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    region: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    stmt = select(VpngateCandidate).order_by(VpngateCandidate.score.desc()).limit(limit)
    if region:
        stmt = stmt.where(VpngateCandidate.region_code == region.upper())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/sync")
async def sync_vpngate(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[AdminUser, Depends(get_current_admin)],
):
    count = await sync_candidates(db)
    return {"synced": count}


@router.post("/candidates/{candidate_id}/add")
async def add_candidate(
    candidate_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    idempotency_key: Annotated[Optional[str], Header(alias="Idempotency-Key")] = None,
):
    if idempotency_key:
        recent = await db.execute(
            select(Operation).where(Operation.kind == "provision_exit").order_by(Operation.created_at.desc()).limit(30)
        )
        for op in recent.scalars():
            if (op.result or {}).get("idempotency_key") == idempotency_key:
                return {
                    "operation_id": str(op.id),
                    "exit_id": str(op.target_id) if op.target_id else None,
                    "status": op.status,
                    "replayed": True,
                }

    cand = await db.get(VpngateCandidate, candidate_id)
    if not cand:
        raise HTTPException(404, "Candidate not found")
    raw = cand.raw_meta or {}
    ovpn_b64 = raw.get("ovpn_b64") or ""
    if not ovpn_b64:
        raise HTTPException(409, "Candidate has no OpenVPN config; sync again")
    try:
        ovpn = base64.b64decode(ovpn_b64).decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(400, f"Invalid OpenVPN payload: {exc}") from exc

    exit_node = ExitNode(
        name=cand.hostname or cand.ip,
        region_code=cand.region_code,
        candidate_id=cand.id,
        status=ExitStatus.pending,
        public_ip=cand.ip,
        country=cand.region_code,
    )
    db.add(exit_node)
    await db.flush()
    db.add(
        AuditLog(
            actor_type="admin",
            actor_id=str(admin.id),
            action="exit.add_from_candidate",
            target_type="exit",
            target_id=str(exit_node.id),
            after={"candidate_id": str(cand.id), "region": cand.region_code, "ip": cand.ip},
        )
    )
    op = await provision_exit(db, exit_node, ovpn, idempotency_key=idempotency_key)
    return {
        "operation_id": str(op.id),
        "exit_id": str(exit_node.id),
        "status": op.status,
        "message": op.message,
        "replayed": False,
    }


@router.post("/{exit_id}/provision")
async def provision(
    exit_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[AdminUser, Depends(get_current_admin)],
):
    exit_node = await db.get(ExitNode, exit_id)
    if not exit_node:
        raise HTTPException(404, "Exit not found")
    ovpn = "dev tun\nproto tcp\nremote 203.0.113.10 443\n"
    if exit_node.candidate_id:
        cand = await db.get(VpngateCandidate, exit_node.candidate_id)
        if cand and (cand.raw_meta or {}).get("ovpn_b64"):
            ovpn = base64.b64decode(cand.raw_meta["ovpn_b64"]).decode("utf-8", errors="replace")
    op = await provision_exit(db, exit_node, ovpn)
    return {"operation_id": str(op.id), "status": op.status, "message": op.message}


@router.patch("/{exit_id}", response_model=ExitNodeOut)
async def update_exit(
    exit_id: UUID,
    req: ExitNodeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[AdminUser, Depends(get_current_admin)],
):
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
