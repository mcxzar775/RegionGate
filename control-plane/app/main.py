"""RegionGate control-plane FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app import __version__
from app.config import get_settings
from app.db import AsyncSessionLocal, Base, engine
from app.models import AdminUser, Region
from app.routers import auth, exits, nodes, ops, regions
from app.security import hash_password


async def _bootstrap() -> None:
    """Create tables (dev) and seed bootstrap admin + default regions."""
    settings = get_settings()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AdminUser).where(AdminUser.username == "admin"))
        if not result.scalar_one_or_none():
            db.add(
                AdminUser(
                    username="admin",
                    password_hash=hash_password(settings.admin_bootstrap_password),
                )
            )
        # Seed common regions if empty
        existing = await db.execute(select(Region).limit(1))
        if not existing.scalar_one_or_none():
            for code, name, prio in [
                ("JP", "日本", 10),
                ("US", "美国", 20),
                ("SG", "新加坡", 30),
                ("KR", "韩国", 40),
                ("HK", "香港", 50),
                ("TW", "台湾", 60),
                ("DE", "德国", 70),
                ("GB", "英国", 80),
            ]:
                db.add(Region(code=code, name=name, priority=prio))
        await db.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await _bootstrap()
    yield


app = FastAPI(
    title="RegionGate API",
    version=__version__,
    description="RegionGate control-plane — VLESS + XHTTP + REALITY baseline",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(auth.devices_router, prefix=API_PREFIX)
app.include_router(auth.enrollment_router, prefix=API_PREFIX)
app.include_router(regions.router, prefix=API_PREFIX)
app.include_router(exits.router, prefix=API_PREFIX)
app.include_router(nodes.router, prefix=API_PREFIX)
app.include_router(ops.router, prefix=API_PREFIX)


@app.get("/")
async def root() -> dict:
    return {
        "service": "regiongate-control-plane",
        "version": __version__,
        "protocol_baseline": "VLESS + XHTTP + REALITY (X25519)",
        "docs": "/docs",
    }
