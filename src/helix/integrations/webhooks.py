"""Inbound webhook handler for integration events.

Receives events from external systems (Jira issue updated, Salesforce deal closed)
and routes them to workflow triggers.
"""

import hashlib
import hmac
from typing import Any
from uuid import UUID

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class WebhookEvent(BaseModel):
    """An inbound webhook event from an external integration."""

    integration_id: UUID
    provider: str
    event_type: str
    payload: dict[str, Any]
    signature: str | None = None


class WebhookResult(BaseModel):
    """Result of processing a webhook event."""

    accepted: bool
    workflow_triggered: bool = False
    workflow_id: UUID | None = None
    reason: str = ""


def verify_signature(
    payload_bytes: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """Verify webhook signature. Supports HMAC-SHA256 (most providers)."""
    expected = hmac.new(secret.encode(), payload_bytes, getattr(hashlib, algorithm)).hexdigest()
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Provider → supported event types
# ---------------------------------------------------------------------------

TRIGGER_MAP: dict[str, list[str]] = {
    "jira": ["issue_created", "issue_updated", "issue_transitioned"],
    "salesforce": ["opportunity_updated", "deal_closed", "lead_created"],
    "github": ["pull_request_opened", "issue_opened", "push"],
    "zendesk": ["ticket_created", "ticket_updated", "sla_breach"],
    "servicenow": ["incident_created", "incident_escalated"],
    "slack": ["message_posted", "reaction_added"],
    "hubspot": ["deal_stage_changed", "contact_created"],
}


async def process_webhook(event: WebhookEvent) -> WebhookResult:
    """Process an inbound webhook event and optionally trigger a workflow."""
    logger.info("webhook.received", provider=event.provider, event_type=event.event_type)

    supported_events = TRIGGER_MAP.get(event.provider, [])
    if event.event_type not in supported_events:
        return WebhookResult(
            accepted=True,
            reason=f"Event {event.event_type} not mapped to workflow trigger",
        )

    # In production: dispatch workflow via Celery
    logger.info("webhook.trigger", provider=event.provider, event_type=event.event_type)
    return WebhookResult(
        accepted=True,
        workflow_triggered=True,
        reason=f"Triggered workflow for {event.event_type}",
    )
