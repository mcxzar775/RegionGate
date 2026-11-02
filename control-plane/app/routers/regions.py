from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_admin
from app.models import AdminUser, Region
from app.schemas import RegionCreate, RegionOut, RegionUpdate

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("", response_model=list[RegionOut])
async def list_regions(db: Annotated[AsyncSession, Depends(get_db)]) -> list[Region]:
    result = await db.execute(select(Region).order_by(Region.priority, Region.code))
    return list(result.scalars().all())


@router.post("", response_model=RegionOut, status_code=201)
async def create_region(
    body: RegionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[AdminUser, Depends(get_current_admin)],
) -> Region:
    existing = await db.execute(select(Region).where(Region.code == body.code.upper()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Region already exists")
    region = Region(
        code=body.code.upper(),
        name=body.name,
        enabled=body.enabled,
        priority=body.priority,
        min_health_score=body.min_health_score,
    )
    db.add(region)
    await db.flush()
    return region


@router.patch("/{code}", response_model=RegionOut)
async def update_region(
    code: str,
    body: RegionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[AdminUser, Depends(get_current_admin)],
) -> Region:
    result = await db.execute(select(Region).where(Region.code == code.upper()))
    region = result.scalar_one_or_none()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(region, k, v)
    await db.flush()
    return region


@router.delete("/{code}", status_code=204)
async def delete_region(
    code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[AdminUser, Depends(get_current_admin)],
) -> None:
    result = await db.execute(select(Region).where(Region.code == code.upper()))
    region = result.scalar_one_or_none()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    await db.delete(region)
    await db.flush()
