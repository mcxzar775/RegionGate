from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import get_settings
from app.db import engine, async_session
from app.models import AdminUser, Base
from app.routers import auth, exits, nodes, ops, regions
from app.security import hash_password

settings = get_settings()


async def bootstrap_admin() -> None:
    async with async_session() as session:
        result = await session.execute(select(AdminUser).limit(1))
        if result.scalar_one_or_none() is not None:
            return
        admin = AdminUser(
            username="admin",
            password_hash=hash_password(settings.admin_bootstrap_password),
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print(f"[bootstrap] created admin user 'admin' with bootstrap password")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await bootstrap_admin()
    yield


app = FastAPI(title="RegionGate Control Plane", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(auth.devices_router, prefix="/api/v1")
app.include_router(auth.enrollment_router, prefix="/api/v1")
app.include_router(exits.router, prefix="/api/v1")
app.include_router(nodes.router, prefix="/api/v1")
app.include_router(ops.router, prefix="/api/v1")
app.include_router(regions.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"status": "ok", "service": "regiongate-control-plane"}
