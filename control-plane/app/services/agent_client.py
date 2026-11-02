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
        while b"\n" not in buf:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
        if not buf:
            raise AgentError("empty agent response")
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


class AgentClient:
    """Speaks the agent protocol: {method, params}."""

    async def call(self, method: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        try:
            return call_agent({"method": method, "params": params or {}})
        except AgentError as exc:
            return {"ok": False, "message": str(exc), "detail": exc.detail}


def agent_health() -> dict[str, Any]:
    try:
        return call_agent({"method": "health", "params": {}})
    except AgentError as exc:
        return {"ok": False, "error": str(exc)}
