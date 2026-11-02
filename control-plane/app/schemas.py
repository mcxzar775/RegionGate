"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import BindingMode, ExitStatus, OperationStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth ---


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class EnrollmentCodeCreateResponse(BaseModel):
    code: str
    expires_at: datetime


class DeviceEnrollRequest(BaseModel):
    code: str
    public_identity: str
    name: str = ""


class DeviceEnrollResponse(BaseModel):
    device_id: UUID
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class DeviceOut(ORMModel):
    id: UUID
    public_identity: str
    name: str
    revoke_version: int
    enrolled_at: datetime
    last_seen_at: Optional[datetime]
    revoked_at: Optional[datetime]


# --- Regions ---


class RegionCreate(BaseModel):
    code: str = Field(min_length=2, max_length=8)
    name: str
    enabled: bool = True
    priority: int = 100
    min_health_score: int = 50


class RegionUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    min_health_score: Optional[int] = None


class RegionOut(ORMModel):
    code: str
    name: str
    enabled: bool
    priority: int
    min_health_score: int
    created_at: datetime
    updated_at: datetime


# --- Exits / Candidates ---


class ExitNodeOut(ORMModel):
    id: UUID
    name: str
    region_code: str
    status: ExitStatus
    public_ip: Optional[str]
    country: Optional[str]
    health_score: int
    last_error: Optional[str]
    revision: int
    created_at: datetime
    updated_at: datetime


class ExitNodeUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[ExitStatus] = None


class CandidateOut(ORMModel):
    id: UUID
    external_id: str
    region_code: str
    hostname: str
    ip: str
    score: int
    status: str
    last_synced_at: datetime


# --- App nodes ---


class AppNodeCreate(BaseModel):
    name: str
    binding_mode: BindingMode = BindingMode.fixed
    desired_region: Optional[str] = None
    fixed_exit_id: Optional[UUID] = None


class AppNodeUpdate(BaseModel):
    name: Optional[str] = None
    binding_mode: Optional[BindingMode] = None
    desired_region: Optional[str] = None
    fixed_exit_id: Optional[UUID] = None
    desired_state: Optional[str] = None


class NodeBindingUpdate(BaseModel):
    binding_mode: BindingMode
    desired_region: Optional[str] = None
    fixed_exit_id: Optional[UUID] = None


class AppNodeOut(ORMModel):
    id: UUID
    device_id: UUID
    name: str
    desired_region: Optional[str]
    binding_mode: BindingMode
    fixed_exit_id: Optional[UUID]
    active_exit_id: Optional[UUID]
    desired_state: str
    runtime_state: str
    revision: int
    config_revision: int
    created_at: datetime
    updated_at: datetime


class ClientConfigOut(BaseModel):
    revision: int
    expires_at: datetime
    config: dict[str, Any]
    signature: str


# --- Operations / health ---


class OperationOut(ORMModel):
    id: UUID
    kind: str
    status: OperationStatus
    target_type: Optional[str]
    target_id: Optional[UUID]
    progress: int
    message: Optional[str]
    created_at: datetime
    updated_at: datetime


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    database: bool
