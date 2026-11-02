"""Render Xray config for VLESS + XHTTP + REALITY."""

from __future__ import annotations

from typing import Any


def render_xray_config(clients: list[dict], reality_public_key: str, short_ids: list[str]) -> dict[str, Any]:
    return {
        "inbounds": [{
            "port": 443,
            "protocol": "vless",
            "settings": {
                "clients": [
                    {"id": c["uuid"], "email": c["email"], "flow": ""} for c in clients
                ],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "xhttp",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": "www.microsoft.com:443",
                    "xver": 0,
                    "serverNames": ["www.microsoft.com"],
                    "privateKey": "PLACEHOLDER_PRIVATE_KEY",
                    "shortIds": short_ids
                }
            }
        }],
        "outbounds": [{"protocol": "freedom"}]
    }
