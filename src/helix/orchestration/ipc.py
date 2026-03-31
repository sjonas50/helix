"""Database-backed inter-agent messaging via PostgreSQL + Redis pub/sub."""

from uuid import UUID, uuid4

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


async def send_message(
    session: AsyncSession,
    workflow_id: UUID,
    org_id: UUID,
    sender_id: UUID,
    recipient_id: UUID | None,
    message_type: str,
    payload: dict,
) -> UUID:
    """Send a message between agents. recipient_id=None for broadcast."""
    msg_id = uuid4()
    await session.execute(
        text(
            """INSERT INTO agent_messages (id, workflow_id, org_id, sender_agent_id, recipient_agent_id, message_type, payload)
                VALUES (:id, :workflow_id, :org_id, :sender_id, :recipient_id, :message_type, :payload::jsonb)"""
        ),
        {
            "id": msg_id,
            "workflow_id": workflow_id,
            "org_id": org_id,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "message_type": message_type,
            "payload": str(payload).replace("'", '"'),
        },
    )
    logger.info("ipc.message_sent", msg_id=str(msg_id), type=message_type)
    return msg_id


async def receive_messages(
    session: AsyncSession, agent_id: UUID, workflow_id: UUID
) -> list[dict]:
    """Receive pending messages for an agent (direct + broadcast)."""
    result = await session.execute(
        text(
            """SELECT id, sender_agent_id, message_type, payload, created_at
                FROM agent_messages
                WHERE workflow_id = :workflow_id
                AND (recipient_agent_id = :agent_id OR recipient_agent_id IS NULL)
                AND delivered_at IS NULL
                ORDER BY created_at"""
        ),
        {"workflow_id": workflow_id, "agent_id": agent_id},
    )
    rows = result.fetchall()

    if rows:
        msg_ids = [row[0] for row in rows]
        for mid in msg_ids:
            await session.execute(
                text("UPDATE agent_messages SET delivered_at = now() WHERE id = :id"),
                {"id": mid},
            )

    return [
        {
            "id": row[0],
            "sender_id": row[1],
            "type": row[2],
            "payload": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]


async def broadcast(
    session: AsyncSession,
    workflow_id: UUID,
    org_id: UUID,
    sender_id: UUID,
    payload: dict,
) -> UUID:
    """Send a broadcast message to all agents in a workflow."""
    return await send_message(
        session, workflow_id, org_id, sender_id, None, "broadcast", payload
    )
