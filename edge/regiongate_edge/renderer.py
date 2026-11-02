"""Render Xray config for VLESS + XHTTP + REALITY."""

from __future__ import annotations

from typing import Any


def render_xray_config(
    clients: list[dict],
    reality_private_key: str,
    short_ids: list[str],
    dest: str = "www.microsoft.com:443",
    server_name: str = "www.microsoft.com",
) -> dict[str, Any]:
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
                    "dest": dest,
                    "xver": 0,
                    "serverNames": [server_name],
                    "privateKey": reality_private_key,
                    "shortIds": short_ids
                }
            }
        }],
        "outbounds": [{"protocol": "freedom"}]
    }


def render_client_config(uuid: str, short_id: str, public_key: str, host: str) -> dict[str, Any]:
    return {
        "protocol": "vless",
        "settings": {"id": uuid, "flow": ""},
        "streamSettings": {
            "network": "xhttp",
            "security": "reality",
            "realitySettings": {
                "serverName": host,
                "publicKey": public_key,
                "shortId": short_id
            }
        }
    }
