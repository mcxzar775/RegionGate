"""Unix-socket client to Gateway Agent. Never shells out."""

from __future__ import annotations

import json
import logging
import socket
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class AgentError(Exception):
    def __init__(self, message: str, detail: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.detail = detail or {}


def call_agent(payload: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
    settings = get_settings()
    path = settings.agent_socket
    data = (json.dumps(payload) + "\n").encode("utf-8")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(path)
        sock.sendall(data)
        buf = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
            if b"\n" in buf:
                break
        line = buf.split(b"\n", 1)[0]
        result = json.loads(line.decode("utf-8"))
        if not result.get("ok"):
            raise AgentError(result.get("message") or result.get("error") or "agent failed", result)
        return result
    except FileNotFoundError as exc:
        raise AgentError(f"agent socket not found: {path}") from exc
    except OSError as exc:
        raise AgentError(f"agent connection failed: {exc}") from exc
    finally:
        sock.close()


def agent_health() -> dict[str, Any]:
    try:
        return call_agent({"command": "health"})
    except AgentError as exc:
        return {"ok": False, "error": str(exc)}


def create_slot(slot_id: str, region: str) -> dict[str, Any]:
    return call_agent({"command": "create_slot", "slot_id": slot_id, "region": region})


def start_openvpn(slot_id: str, ovpn_b64: str) -> dict[str, Any]:
    return call_agent(
        {"command": "start_openvpn", "slot_id": slot_id, "ovpn_b64": ovpn_b64}
    )


def test_exit(slot_id: str) -> dict[str, Any]:
    return call_agent({"command": "test_exit", "slot_id": slot_id})


def destroy_slot(slot_id: str) -> dict[str, Any]:
    return call_agent({"command": "destroy_slot", "slot_id": slot_id})
