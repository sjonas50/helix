"""Event emission for real-time WebSocket notifications.

Called by orchestration engine and approval handlers to push events
to connected frontend clients.
"""

from datetime import UTC, datetime

import structlog

logger = structlog.get_logger()

# Import manager lazily to avoid circular imports
_manager = None


def _get_manager():
    global _manager
    if _manager is None:
        from helix.api.routes.ws import manager

        _manager = manager
    return _manager


async def emit_approval_request(
    org_id: str,
    approval_id: str,
    workflow_id: str,
    action_description: str,
    risk_level: str,
    sla_deadline: str | None = None,
) -> None:
    """Push approval request to all connected clients for an org."""
    mgr = _get_manager()
    await mgr.broadcast_to_org(
        org_id,
        {
            "type": "approval_request",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "data": {
                "approval_id": approval_id,
                "workflow_id": workflow_id,
                "action_description": action_description,
                "risk_level": risk_level,
                "sla_deadline": sla_deadline,
            },
        },
    )
    logger.info("event.approval_request", org_id=org_id, approval_id=approval_id)


async def emit_workflow_status(
    org_id: str,
    workflow_id: str,
    status: str,
    phase: str,
) -> None:
    """Push workflow status change to all connected clients."""
    mgr = _get_manager()
    await mgr.broadcast_to_org(
        org_id,
        {
            "type": "workflow_status",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "data": {
                "workflow_id": workflow_id,
                "status": status,
                "phase": phase,
            },
        },
    )
    logger.info(
        "event.workflow_status", org_id=org_id, workflow_id=workflow_id, status=status
    )


async def emit_agent_activity(
    org_id: str,
    agent_id: str,
    workflow_id: str,
    action: str,
    description: str,
) -> None:
    """Push agent activity to all connected clients."""
    mgr = _get_manager()
    await mgr.broadcast_to_org(
        org_id,
        {
            "type": "agent_activity",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "data": {
                "agent_id": agent_id,
                "workflow_id": workflow_id,
                "action": action,
                "description": description,
            },
        },
    )
    logger.info(
        "event.agent_activity", org_id=org_id, agent_id=agent_id, action=action
    )
