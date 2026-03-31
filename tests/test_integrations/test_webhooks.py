"""Tests for inbound webhook handler."""

import hashlib
import hmac
import uuid

import pytest

from helix.integrations.webhooks import (
    TRIGGER_MAP,
    WebhookEvent,
    process_webhook,
    verify_signature,
)


class TestVerifySignature:
    def test_valid_signature(self) -> None:
        secret = "webhook-secret-123"
        payload = b'{"event": "issue_created"}'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert verify_signature(payload, sig, secret) is True

    def test_invalid_signature(self) -> None:
        secret = "webhook-secret-123"
        payload = b'{"event": "issue_created"}'
        assert verify_signature(payload, "bad-signature", secret) is False

    def test_different_payload_fails(self) -> None:
        secret = "webhook-secret-123"
        payload = b'{"event": "issue_created"}'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        tampered = b'{"event": "issue_deleted"}'
        assert verify_signature(tampered, sig, secret) is False


class TestProcessWebhook:
    @pytest.mark.asyncio
    async def test_known_event_triggers_workflow(self) -> None:
        event = WebhookEvent(
            integration_id=uuid.uuid4(),
            provider="jira",
            event_type="issue_created",
            payload={"issue_key": "PROJ-123"},
        )
        result = await process_webhook(event)
        assert result.accepted is True
        assert result.workflow_triggered is True

    @pytest.mark.asyncio
    async def test_unknown_event_no_trigger(self) -> None:
        event = WebhookEvent(
            integration_id=uuid.uuid4(),
            provider="jira",
            event_type="unknown_event_type",
            payload={},
        )
        result = await process_webhook(event)
        assert result.accepted is True
        assert result.workflow_triggered is False

    @pytest.mark.asyncio
    async def test_unknown_provider_no_trigger(self) -> None:
        event = WebhookEvent(
            integration_id=uuid.uuid4(),
            provider="nonexistent",
            event_type="something",
            payload={},
        )
        result = await process_webhook(event)
        assert result.accepted is True
        assert result.workflow_triggered is False


class TestSupportedProviders:
    def test_supported_providers(self) -> None:
        expected = {
            "jira",
            "salesforce",
            "github",
            "zendesk",
            "servicenow",
            "slack",
            "hubspot",
        }
        assert set(TRIGGER_MAP.keys()) == expected

    def test_each_provider_has_events(self) -> None:
        for provider, events in TRIGGER_MAP.items():
            assert len(events) >= 2, f"{provider} has fewer than 2 events"
