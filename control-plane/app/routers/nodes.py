from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_admin, get_current_device
from app.models import AdminUser, AppNode, Device
from app.schemas import AppNodeCreate, AppNodeOut, AppNodeUpdate, NodeBindingUpdate

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("", response_model=list[AppNodeOut])
async def list_nodes(db: Annotated[AsyncSession, Depends(get_db)], admin: Annotated[AdminUser, Depends(get_current_admin)]):
    result = await db.execute(select(AppNode))
    return result.scalars().all()


@router.post("", response_model=AppNodeOut)
async def create_node(req: AppNodeCreate, db: Annotated[AsyncSession, Depends(get_db)], device: Annotated[Device, Depends(get_current_device)]):
    node = AppNode(device_id=device.id, name=req.name, binding_mode=req.binding_mode, desired_region=req.desired_region, fixed_exit_id=req.fixed_exit_id)
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


@router.patch("/{node_id}", response_model=AppNodeOut)
async def update_node(node_id: UUID, req: AppNodeUpdate, db: Annotated[AsyncSession, Depends(get_db)], device: Annotated[Device, Depends(get_current_device)]):
    node = await db.get(AppNode, node_id)
    if not node or node.device_id != device.id:
        raise HTTPException(404)
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(node, field, value)
    node.revision += 1
    await db.commit()
    await db.refresh(node)
    return node


@router.post("/{node_id}/bind")
async def update_binding(node_id: UUID, req: NodeBindingUpdate, db: Annotated[AsyncSession, Depends(get_db)], device: Annotated[Device, Depends(get_current_device)]):
    node = await db.get(AppNode, node_id)
    if not node or node.device_id != device.id:
        raise HTTPException(404)
    node.binding_mode = req.binding_mode
    node.desired_region = req.desired_region
    node.fixed_exit_id = req.fixed_exit_id
    node.revision += 1
    await db.commit()
    return {"ok": True, "revision": node.revision}
