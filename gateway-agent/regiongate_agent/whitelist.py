"""OpenVPN config and agent command whitelist validation."""

from __future__ import annotations

import re
import socket
import struct
from typing import Any

FORBIDDEN_DIRECTIVES = {
    "script-security",
    "up",
    "down",
    "route-up",
    "route-pre-down",
    "ipchange",
    "learn-address",
    "auth-user-pass-verify",
    "client-connect",
    "client-disconnect",
    "tls-verify",
    "plugin",
    "management",
    "management-client",
    "setenv",
    "setenv-safe",
    "cd",
    "chroot",
    "user",
    "group",
    "daemon",
    "writepid",
    "status",
    "log",
    "log-append",
    "syslog",
}

ALLOWED_COMMANDS = {
    "ping",
    "create_slot",
    "destroy_slot",
    "start_openvpn",
    "stop_openvpn",
    "test_exit",
    "list_slots",
    "health",
}

MAX_OVPN_BYTES = 256 * 1024


def check_peer_credentials(sock: socket.socket) -> bool:
    """SO_PEERCRED. Test VPS allows root only."""
    try:
        creds = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        if isinstance(creds, bytes) and len(creds) >= 12:
            _pid, uid, _gid = struct.unpack("@iii", creds[:12])
            return uid == 0
        return False
    except Exception:
        return False


def validate_agent_request(payload: dict[str, Any]) -> None:
    cmd = payload.get("command") or payload.get("method")
    if not cmd or cmd not in ALLOWED_COMMANDS:
        raise ValueError(f"command not allowed: {cmd!r}")
    allowed_keys = {
        "command",
        "method",
        "params",
        "slot_id",
        "namespace",
        "ovpn_b64",
        "ovpn_content",
        "region",
        "request_id",
    }
    extra = set(payload.keys()) - allowed_keys
    if extra:
        raise ValueError(f"extra fields rejected: {sorted(extra)}")


def validate_ovpn_content(content: str) -> list[str]:
    issues: list[str] = []
    if len(content.encode("utf-8")) > MAX_OVPN_BYTES:
        issues.append("ovpn too large")
    if "\x00" in content:
        issues.append("binary null in ovpn")

    has_remote = False
    has_dev_tun = False
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        if stripped.startswith("<") or stripped.startswith("</"):
            continue
        token = re.split(r"\s+", stripped, maxsplit=1)[0].lower()
        if token in FORBIDDEN_DIRECTIVES:
            issues.append(f"forbidden directive: {token}")
        if token == "remote":
            has_remote = True
        if token == "dev" and "tun" in stripped.lower():
            has_dev_tun = True
        if token == "dev-type" and "tun" in stripped.lower():
            has_dev_tun = True

    if not has_remote:
        issues.append("missing remote")
    if not has_dev_tun:
        issues.append("missing TUN device directive")
    return issues
