"""Execution layer: real or dry-run / fake runner for privileged ops."""

from __future__ import annotations

import logging
import secrets
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional

from regiongate_agent.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SlotState:
    slot_id: str
    namespace: str
    outbound_tag: str
    socks_host: str = "10.200.0.2"
    socks_port: int = 1080
    openvpn_running: bool = False
    status: str = "created"


@dataclass
class RunnerResult:
    ok: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)


class BaseRunner:
    def create_slot(self, slot_id: str, region: str) -> RunnerResult: ...
    def destroy_slot(self, slot_id: str) -> RunnerResult: ...
    def start_openvpn(self, slot_id: str, ovpn_content: str) -> RunnerResult: ...
    def stop_openvpn(self, slot_id: str) -> RunnerResult: ...
    def test_exit(self, slot_id: str) -> RunnerResult: ...
    def list_slots(self) -> RunnerResult: ...
    def health(self) -> RunnerResult: ...


class DryRunRunner(BaseRunner):
    """In-memory fake for CI and non-privileged environments."""

    def __init__(self) -> None:
        self.slots: dict[str, SlotState] = {}
        self.settings = get_settings()

    def create_slot(self, slot_id: str, region: str) -> RunnerResult:
        if slot_id in self.slots:
            return RunnerResult(False, "slot already exists")
        ns = f"{self.settings.namespace_prefix}{region.lower()}-{secrets.token_hex(3)}"
        tag = f"exit-{slot_id}"
        self.slots[slot_id] = SlotState(
            slot_id=slot_id,
            namespace=ns,
            outbound_tag=tag,
        )
        logger.info("dry-run create_slot %s ns=%s", slot_id, ns)
        return RunnerResult(
            True,
            "created",
            {
                "slot_id": slot_id,
                "namespace": ns,
                "outbound_tag": tag,
                "socks_host": self.slots[slot_id].socks_host,
                "socks_port": self.slots[slot_id].socks_port,
            },
        )

    def destroy_slot(self, slot_id: str) -> RunnerResult:
        if slot_id not in self.slots:
            return RunnerResult(False, "slot not found")
        del self.slots[slot_id]
        return RunnerResult(True, "destroyed", {"slot_id": slot_id})

    def start_openvpn(self, slot_id: str, ovpn_content: str) -> RunnerResult:
        from regiongate_agent.whitelist import validate_ovpn_content

        issues = validate_ovpn_content(ovpn_content)
        if issues:
            return RunnerResult(False, "ovpn validation failed", {"issues": issues})
        slot = self.slots.get(slot_id)
        if not slot:
            return RunnerResult(False, "slot not found")
        slot.openvpn_running = True
        slot.status = "connected"
        return RunnerResult(True, "openvpn started (dry-run)", {"slot_id": slot_id})

    def stop_openvpn(self, slot_id: str) -> RunnerResult:
        slot = self.slots.get(slot_id)
        if not slot:
            return RunnerResult(False, "slot not found")
        slot.openvpn_running = False
        slot.status = "stopped"
        return RunnerResult(True, "openvpn stopped", {"slot_id": slot_id})

    def test_exit(self, slot_id: str) -> RunnerResult:
        slot = self.slots.get(slot_id)
        if not slot or not slot.openvpn_running:
            return RunnerResult(False, "exit not ready")
        # Simulated health result
        return RunnerResult(
            True,
            "ok",
            {
                "slot_id": slot_id,
                "public_ip": "203.0.113.10",
                "country": "JP",
                "latency_ms": 42,
                "dns_ok": True,
            },
        )

    def list_slots(self) -> RunnerResult:
        data = {
            sid: {
                "namespace": s.namespace,
                "outbound_tag": s.outbound_tag,
                "status": s.status,
                "openvpn_running": s.openvpn_running,
            }
            for sid, s in self.slots.items()
        }
        return RunnerResult(True, "ok", {"slots": data})

    def health(self) -> RunnerResult:
        return RunnerResult(
            True,
            "ok",
            {"dry_run": True, "slots": len(self.slots), "version": "0.1.0"},
        )


class PrivilegedRunner(BaseRunner):
    """Real namespace / OpenVPN operations. Only for Staging with capabilities."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.slots: dict[str, SlotState] = {}

    def _run(self, argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
        # Always argv list + absolute paths — never shell=True
        return subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    # ... (full implementation in local copy; dry-run is default for test VPS)
