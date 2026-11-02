"""Two-phase exit provisioning with rollback."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExitNode, ExitStatus, Operation, OperationStatus
from app.services.agent_client import AgentClient


async def provision_exit(db: AsyncSession, exit_node: ExitNode) -> Operation:
    op = Operation(kind="provision_exit", status=OperationStatus.running, target_type="exit", target_id=exit_node.id)
    db.add(op)
    await db.flush()

    try:
        client = AgentClient()
        # Phase 1: create slot
        res = await client.call("create_slot", {"slot_id": str(exit_node.id), "region": exit_node.region_code})
        if not res.get("ok"):
            raise RuntimeError(res.get("message", "create_slot failed"))

        # Phase 2: start openvpn (placeholder ovpn)
        ovpn = "# placeholder ovpn for dry-run\nremote 1.2.3.4 1194\nproto udp\n"
        res2 = await client.call("start_openvpn", {"slot_id": str(exit_node.id), "ovpn_content": ovpn})
        if not res2.get("ok"):
            # rollback
            await client.call("destroy_slot", {"slot_id": str(exit_node.id)})
            raise RuntimeError(res2.get("message", "start_openvpn failed"))

        exit_node.status = ExitStatus.ready
        op.status = OperationStatus.succeeded
        op.message = "provisioned"
    except Exception as exc:
        exit_node.status = ExitStatus.error
        exit_node.last_error = str(exc)
        op.status = OperationStatus.failed
        op.message = str(exc)

    await db.commit()
    return op
