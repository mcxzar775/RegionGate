"""Two-phase exit provisioning with rollback. Dry-run safe."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExitNode, ExitStatus, Operation, OperationStatus
from app.services.agent_client import AgentClient


async def provision_exit(
    db: AsyncSession,
    exit_node: ExitNode,
    ovpn_content: str,
    *,
    idempotency_key: str | None = None,
) -> Operation:
    op = Operation(
        kind="provision_exit",
        status=OperationStatus.running,
        target_type="exit",
        target_id=exit_node.id,
        message="provisioning",
        result={"idempotency_key": idempotency_key} if idempotency_key else {},
    )
    db.add(op)
    exit_node.status = ExitStatus.provisioning
    await db.flush()

    client = AgentClient()
    slot_id = str(exit_node.id)
    try:
        created = await client.call(
            "create_slot", {"slot_id": slot_id, "region": exit_node.region_code}
        )
        if not created.get("ok"):
            raise RuntimeError(created.get("message") or "create_slot failed")

        started = await client.call(
            "start_openvpn", {"slot_id": slot_id, "ovpn_content": ovpn_content}
        )
        if not started.get("ok"):
            await client.call("destroy_slot", {"slot_id": slot_id})
            op.status = OperationStatus.rolled_back
            raise RuntimeError(started.get("message") or "start_openvpn failed")

        tested = await client.call("test_exit", {"slot_id": slot_id})
        if not tested.get("ok"):
            await client.call("destroy_slot", {"slot_id": slot_id})
            op.status = OperationStatus.rolled_back
            raise RuntimeError(tested.get("message") or "test_exit failed")

        data = tested.get("data") or {}
        exit_node.public_ip = data.get("public_ip") or exit_node.public_ip
        exit_node.country = data.get("country") or exit_node.region_code
        if data.get("latency_ms") is not None:
            exit_node.health_score = max(0, 100 - int(data["latency_ms"] // 10))
        exit_node.status = ExitStatus.ready
        exit_node.last_error = None
        op.status = OperationStatus.succeeded
        op.progress = 100
        op.message = "provisioned"
        op.result = {
            "idempotency_key": idempotency_key,
            "namespace": (created.get("data") or {}).get("namespace"),
            "outbound_tag": (created.get("data") or {}).get("outbound_tag"),
            "health": data,
        }
    except Exception as exc:
        if op.status != OperationStatus.rolled_back:
            op.status = OperationStatus.failed
        exit_node.status = ExitStatus.error
        exit_node.last_error = str(exc)
        op.message = str(exc)

    await db.commit()
    await db.refresh(op)
    return op
