"""SQLAlchemy domain models matching brief section 10."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class BindingMode(str, enum.Enum):
    fixed = "fixed"
    automatic = "automatic"


class ExitStatus(str, enum.Enum):
    pending = "pending"
    provisioning = "provisioning"
    testing = "testing"
    ready = "ready"
    active = "active"
    degraded = "degraded"
    offline = "offline"
    error = "error"
    disabled = "disabled"
    deleting = "deleting"


class OperationStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    rolled_back = "rolled_back"
    rollback_failed = "rollback_failed"
    cancelled = "cancelled"


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    public_identity: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), default="")
    revoke_version: Mapped[int] = mapped_column(Integer, default=0)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    credentials: Mapped[list[DeviceCredential]] = relationship(back_populates="device")
    nodes: Mapped[list[AppNode]] = relationship(back_populates="device")


class DeviceCredential(Base):
    __tablename__ = "device_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    device: Mapped[Device] = relationship(back_populates="credentials")


class EnrollmentCode(Base):
    __tablename__ = "enrollment_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    code_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Region(Base):
    __tablename__ = "regions"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)  # ISO
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    min_health_score: Mapped[int] = mapped_column(Integer, default=50)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VpngateCandidate(Base):
    __tablename__ = "vpngate_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    region_code: Mapped[str] = mapped_column(String(8), ForeignKey("regions.code"), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="healthy")
    raw_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ExitNode(Base):
    __tablename__ = "exit_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    region_code: Mapped[str] = mapped_column(String(8), ForeignKey("regions.code"), nullable=False)
    candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vpngate_candidates.id"), nullable=True
    )
    status: Mapped[ExitStatus] = mapped_column(Enum(ExitStatus), default=ExitStatus.pending)
    public_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    health_score: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    slots: Mapped[list[ExitSlot]] = relationship(back_populates="exit_node")


class ExitSlot(Base):
    __tablename__ = "exit_slots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    exit_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exit_nodes.id"), nullable=False
    )
    namespace_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    outbound_tag: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    socks_host: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    socks_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    exit_node: Mapped[ExitNode] = relationship(back_populates="slots")


class AppNode(Base):
    __tablename__ = "app_nodes"
    __table_args__ = (UniqueConstraint("device_id", "id", name="uq_device_node"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    desired_region: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    binding_mode: Mapped[BindingMode] = mapped_column(Enum(BindingMode), default=BindingMode.fixed)
    fixed_exit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exit_nodes.id"), nullable=True
    )
    active_exit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exit_nodes.id"), nullable=True
    )
    desired_state: Mapped[str] = mapped_column(String(32), default="inactive")
    runtime_state: Mapped[str] = mapped_column(String(32), default="inactive")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    config_revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    device: Mapped[Device] = relationship(back_populates="nodes")
    xray_client: Mapped[Optional[XrayClient]] = relationship(
        back_populates="app_node", uselist=False
    )


class XrayClient(Base):
    __tablename__ = "xray_clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    app_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_nodes.id"), unique=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, default=_uuid)
    short_id: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    app_node: Mapped[AppNode] = relationship(back_populates="xray_client")


class Operation(Base):
    __tablename__ = "operations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[OperationStatus] = mapped_column(
        Enum(OperationStatus), default=OperationStatus.queued
    )
    target_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class HealthSample(Base):
    __tablename__ = "health_samples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    exit_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exit_nodes.id"), nullable=False
    )
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    public_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)  # admin / device / system
    actor_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    before: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
