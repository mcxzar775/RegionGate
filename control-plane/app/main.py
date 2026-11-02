from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import engine
from app.models import Base
from app.routers import auth, exits, nodes, ops, regions

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
