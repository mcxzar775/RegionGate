from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_admin
from app.models import AdminUser, Region
from app.schemas import RegionCreate, RegionOut

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("", response_model=list[RegionOut])
async def list_regions(db: Annotated[AsyncSession, Depends(get_db)], admin: Annotated[AdminUser, Depends(get_current_admin)]):
    result = await db.execute(select(Region).order_by(Region.priority))
    regions = result.scalars().all()
    return list(regions)


@router.post("", response_model=RegionOut)
async def create_region(req: RegionCreate, db: Annotated[AsyncSession, Depends(get_db)], admin: Annotated[AdminUser, Depends(get_current_admin)]):
    existing = await db.get(Region, req.code)
    if existing:
        raise HTTPException(400, "Region exists")
    region = Region(code=req.code, name=req.name, priority=req.priority or 100, enabled=True)
    db.add(region)
    await db.commit()
    await db.refresh(region)
    return region
