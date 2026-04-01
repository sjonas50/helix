"""Tests for webhook data ingest pipeline."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helix.integrations.ingest import (
    compute_content_hash,
    ingest_webhook_to_memory,
    normalize_webhook_payload,
)


class TestComputeContentHash:
    def test_deterministic(self) -> None:
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("hello world")
        assert h1 == h2

    def test_different_content_different_hash(self) -> None:
        h1 = compute_content_hash("hello")
        h2 = compute_content_hash("world")
        assert h1 != h2

    def test_returns_hex_string(self) -> None:
        h = compute_content_hash("test")
        assert len(h) == 64  # SHA-256 hex is 64 chars
        assert all(c in "0123456789abcdef" for c in h)


class TestNormalizeSlack:
    def test_valid_message(self) -> None:
        payload = {
            "event": {
                "text": "This is a long enough slack message for indexing",
                "channel": "C123",
                "user": "U456",
                "ts": "1234567890.123456",
            }
        }
        result = normalize_webhook_payload("slack", "message_posted", payload)
        assert result is not None
        assert result["topic"] == "slack:C123"
        assert "U456" in result["content"]
        assert result["source_id"] == "C123:1234567890.123456"
        assert result["entity_type"] == "message"
        assert "slack.com/archives/C123" in result["source_url"]

    def test_short_message_skipped(self) -> None:
        payload = {"event": {"text": "hi", "channel": "C123", "user": "U456", "ts": "1"}}
        result = normalize_webhook_payload("slack", "message_posted", payload)
        assert result is None

    def test_wrong_event_type_skipped(self) -> None:
        payload = {"event": {"text": "something long enough to pass", "channel": "C1"}}
        result = normalize_webhook_payload("slack", "reaction_added", payload)
        assert result is None

    def test_empty_text_skipped(self) -> None:
        payload = {"event": {"text": "", "channel": "C123", "user": "U456", "ts": "1"}}
        result = normalize_webhook_payload("slack", "message_posted", payload)
        assert result is None


class TestNormalizeJira:
    def test_valid_issue(self) -> None:
        payload = {
            "issue": {
                "key": "PROJ-42",
                "self": "https://jira.example.com/rest/api/2/issue/12345",
                "fields": {
                    "summary": "Fix login bug",
                    "description": "Users cannot log in when password contains special chars.",
                },
            }
        }
        result = normalize_webhook_payload("jira", "issue_created", payload)
        assert result is not None
        assert result["topic"] == "jira:PROJ-42"
        assert "Fix login bug" in result["content"]
        assert result["source_id"] == "PROJ-42"
        assert result["entity_type"] == "issue"

    def test_missing_key_skipped(self) -> None:
        payload = {"issue": {"fields": {"summary": "No key"}}}
        result = normalize_webhook_payload("jira", "issue_created", payload)
        assert result is None

    def test_no_description(self) -> None:
        payload = {
            "issue": {
                "key": "PROJ-1",
                "fields": {"summary": "Title only", "description": None},
            }
        }
        result = normalize_webhook_payload("jira", "issue_created", payload)
        assert result is not None
        assert "\n" not in result["content"]


class TestNormalizeGitHub:
    def test_issue_opened(self) -> None:
        payload = {
            "issue": {
                "number": 99,
                "id": 55555,
                "title": "Bug in auth module",
                "body": "Detailed description of the bug.",
                "html_url": "https://github.com/org/repo/issues/99",
            }
        }
        result = normalize_webhook_payload("github", "issue_opened", payload)
        assert result is not None
        assert result["topic"] == "github:issue:99"
        assert "Bug in auth module" in result["content"]
        assert result["source_id"] == "55555"
        assert result["source_url"] == "https://github.com/org/repo/issues/99"
        assert result["entity_type"] == "issue"

    def test_pull_request_opened(self) -> None:
        payload = {
            "pull_request": {
                "number": 42,
                "id": 77777,
                "title": "Add feature X",
                "body": "This PR adds feature X.",
                "html_url": "https://github.com/org/repo/pull/42",
            }
        }
        result = normalize_webhook_payload("github", "pull_request_opened", payload)
        assert result is not None
        assert result["topic"] == "github:pr:42"
        assert result["entity_type"] == "pull_request"

    def test_unsupported_event_skipped(self) -> None:
        result = normalize_webhook_payload("github", "push", {"ref": "refs/heads/main"})
        assert result is None


class TestNormalizeUnknownProvider:
    def test_unknown_provider_returns_none(self) -> None:
        result = normalize_webhook_payload("unknown_saas", "something", {})
        assert result is None


class TestIngestWebhookToMemory:
    @pytest.mark.asyncio
    async def test_unsupported_event_returns_none(self) -> None:
        session = AsyncMock()
        org_id = uuid.uuid4()
        result = await ingest_webhook_to_memory(
            session, org_id, "slack", "reaction_added", {}
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_dedup_skips_existing(self) -> None:
        session = AsyncMock()
        # Simulate existing record found
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (uuid.uuid4(),)
        session.execute.return_value = mock_result

        org_id = uuid.uuid4()
        payload = {
            "event": {
                "text": "This message is long enough for indexing purposes",
                "channel": "C1",
                "user": "U1",
                "ts": "123.456",
            }
        }
        result = await ingest_webhook_to_memory(
            session, org_id, "slack", "message_posted", payload
        )
        assert result is None

    @pytest.mark.asyncio
    @patch("helix.integrations.ingest.embed_text", new_callable=AsyncMock)
    async def test_successful_ingest(self, mock_embed: AsyncMock) -> None:
        mock_embed.return_value = [0.1] * 1536  # Non-zero embedding

        session = AsyncMock()
        # First execute = dedup check (no existing)
        dedup_result = MagicMock()
        dedup_result.fetchone.return_value = None
        # Second execute = INSERT
        insert_result = MagicMock()
        session.execute.side_effect = [dedup_result, insert_result]

        org_id = uuid.uuid4()
        payload = {
            "issue": {
                "key": "TEST-1",
                "self": "https://jira.example.com/issue/1",
                "fields": {"summary": "Test issue", "description": "A test."},
            }
        }
        result = await ingest_webhook_to_memory(
            session, org_id, "jira", "issue_created", payload
        )
        assert result is not None
        assert session.commit.called
        # Verify embed was called with content containing the Jira key
        call_args = mock_embed.call_args[0][0]
        assert "TEST-1" in call_args

    @pytest.mark.asyncio
    @patch("helix.integrations.ingest.embed_text", new_callable=AsyncMock)
    async def test_zero_vector_stored_as_none(self, mock_embed: AsyncMock) -> None:
        """When no OpenAI key is set, embed_text returns [0.0]*1536. Should store None."""
        mock_embed.return_value = [0.0] * 1536

        session = AsyncMock()
        dedup_result = MagicMock()
        dedup_result.fetchone.return_value = None
        insert_result = MagicMock()
        session.execute.side_effect = [dedup_result, insert_result]

        org_id = uuid.uuid4()
        payload = {
            "issue": {
                "number": 1,
                "id": 100,
                "title": "Test issue title here",
                "body": "Body content.",
                "html_url": "https://github.com/o/r/issues/1",
            }
        }
        result = await ingest_webhook_to_memory(
            session, org_id, "github", "issue_opened", payload
        )
        assert result is not None
        # The INSERT call is the second execute — check embedding param is None
        insert_call = session.execute.call_args_list[1]
        params = insert_call[0][1]
        assert params["embedding"] is None
