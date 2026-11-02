"""Unix socket server for privileged operations."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
from typing import Any

from regiongate_agent.config import get_settings
from regiongate_agent.runner import DryRunRunner, PrivilegedRunner
from regiongate_agent.whitelist import check_peer_credentials

logger = logging.getLogger(__name__)


class AgentServer:
    def __init__(self) -> None:
        settings = get_settings()
        self.socket_path = settings.agent_socket
        self.runner = DryRunRunner() if settings.dry_run else PrivilegedRunner()
        self.server: asyncio.AbstractServer | None = None

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            # SO_PEERCRED check
            sock = writer.get_extra_info("socket")
            if not check_peer_credentials(sock):
                writer.write(b'{"ok": false, "message": "unauthorized"}\n')
                await writer.drain()
                return

            data = await reader.readline()
            if not data:
                return
            req = json.loads(data.decode())
            method = req.get("method")
            params = req.get("params", {})

            handler = getattr(self.runner, method, None)
            if not handler:
                resp = {"ok": False, "message": f"unknown method {method}"}
            else:
                result = handler(**params) if isinstance(params, dict) else handler()
                resp = {"ok": result.ok, "message": result.message, "data": result.data}

            writer.write((json.dumps(resp) + "\n").encode())
            await writer.drain()
        except Exception as exc:
            logger.exception("client error")
            writer.write(json.dumps({"ok": False, "message": str(exc)}).encode() + b"\n")
            await writer.drain()
        finally:
            writer.close()

    async def start(self) -> None:
        os.makedirs(os.path.dirname(self.socket_path), exist_ok=True)
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        self.server = await asyncio.start_unix_server(self.handle_client, path=self.socket_path)
        os.chmod(self.socket_path, 0o660)
        logger.info("agent listening on %s", self.socket_path)
        async with self.server:
            await self.server.serve_forever()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(AgentServer().start())
