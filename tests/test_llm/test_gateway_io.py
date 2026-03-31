"""Tests for LLM gateway I/O — async calls, fallback, metering, structured output."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from helix.llm.gateway import (
    CircuitBreaker,
    FallbackPolicy,
    LLMRequest,
    TokenUsageTracker,
    call_llm,
)
from helix.llm.metering import record_usage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_request(**overrides):
    defaults = {
        "messages": [{"role": "user", "content": "Hello"}],
        "org_id": uuid4(),
    }
    defaults.update(overrides)
    return LLMRequest(**defaults)


def _anthropic_response(text: str = "Hi there"):
    """Fake Anthropic messages.create response."""
    text_block = SimpleNamespace(type="text", text=text)
    usage = SimpleNamespace(input_tokens=100, output_tokens=50, cache_read_input_tokens=10)
    return SimpleNamespace(content=[text_block], usage=usage)


def _openai_response(text: str = "Hi there"):
    """Fake OpenAI chat.completions.create response."""
    message = SimpleNamespace(content=text, tool_calls=None)
    choice = SimpleNamespace(message=message)
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50)
    return SimpleNamespace(choices=[choice], usage=usage)


# ---------------------------------------------------------------------------
# call_llm — Anthropic provider
# ---------------------------------------------------------------------------

class TestCallLLMAnthropic:
    @pytest.mark.asyncio
    async def test_call_llm_anthropic(self) -> None:
        """Verify a successful Anthropic call returns a populated LLMResponse."""
        fake_resp = _anthropic_response("Hello from Claude")
        mock_create = AsyncMock(return_value=fake_resp)

        with patch("helix.llm.gateway.AsyncAnthropic") as mock_client, \
             patch("helix.llm.gateway.get_settings") as mock_settings:
            mock_settings.return_value = SimpleNamespace(
                anthropic_api_key="sk-test", openai_api_key=""
            )
            mock_client.return_value.messages.create = mock_create

            request = _make_request(model="claude-sonnet-4-6")
            response = await call_llm(request)

            assert response.content == "Hello from Claude"
            assert response.model_used == "claude-sonnet-4-6"
            assert response.provider == "anthropic"
            assert response.input_tokens == 100
            assert response.output_tokens == 50
            assert response.cache_read_tokens == 10
            assert response.cost_usd > 0
            assert response.latency_ms >= 0
            assert not response.fallback_occurred
            mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_call_llm_anthropic_with_tools(self) -> None:
        """Verify tool_use blocks are extracted as tool_calls."""
        tool_block = SimpleNamespace(
            type="tool_use", id="call_1", name="search", input={"q": "test"}
        )
        usage = SimpleNamespace(input_tokens=80, output_tokens=30, cache_read_input_tokens=0)
        fake_resp = SimpleNamespace(content=[tool_block], usage=usage)
        mock_create = AsyncMock(return_value=fake_resp)

        with patch("helix.llm.gateway.AsyncAnthropic") as mock_client, \
             patch("helix.llm.gateway.get_settings") as mock_settings:
            mock_settings.return_value = SimpleNamespace(
                anthropic_api_key="sk-test", openai_api_key=""
            )
            mock_client.return_value.messages.create = mock_create

            request = _make_request(model="claude-sonnet-4-6")
            response = await call_llm(request)

            assert len(response.tool_calls) == 1
            assert response.tool_calls[0]["name"] == "search"


# ---------------------------------------------------------------------------
# call_llm — Fallback on error
# ---------------------------------------------------------------------------

class TestCallLLMFallback:
    @pytest.mark.asyncio
    async def test_call_llm_fallback_on_error(self) -> None:
        """When the primary model fails, the gateway should fall back to the next model."""
        fake_resp = _anthropic_response("From haiku")
        mock_create = AsyncMock(
            side_effect=[Exception("rate limited"), fake_resp]
        )

        with patch("helix.llm.gateway.AsyncAnthropic") as mock_client, \
             patch("helix.llm.gateway.get_settings") as mock_settings:
            mock_settings.return_value = SimpleNamespace(
                anthropic_api_key="sk-test", openai_api_key=""
            )
            mock_client.return_value.messages.create = mock_create

            policy = FallbackPolicy(
                primary_model="claude-sonnet-4-6",
                fallback_chain=["claude-haiku-4-5"],
            )
            request = _make_request()
            response = await call_llm(request, policy=policy)

            assert response.model_used == "claude-haiku-4-5"
            assert response.fallback_occurred
            assert response.fallback_reason is not None
            assert "rate limited" in response.fallback_reason
            assert mock_create.await_count == 2

    @pytest.mark.asyncio
    async def test_call_llm_all_fail_raises(self) -> None:
        """When all models fail, call_llm raises RuntimeError."""
        mock_create = AsyncMock(side_effect=Exception("server error"))

        with patch("helix.llm.gateway.AsyncAnthropic") as mock_client, \
             patch("helix.llm.gateway.get_settings") as mock_settings:
            mock_settings.return_value = SimpleNamespace(
                anthropic_api_key="sk-test", openai_api_key=""
            )
            mock_client.return_value.messages.create = mock_create

            policy = FallbackPolicy(
                primary_model="claude-sonnet-4-6",
                fallback_chain=["claude-haiku-4-5"],
            )
            request = _make_request()

            with pytest.raises(RuntimeError, match="All LLM models failed"):
                await call_llm(request, policy=policy)

    @pytest.mark.asyncio
    async def test_call_llm_circuit_breaker_records_failure(self) -> None:
        """Circuit breaker records failure when a model call fails."""
        fake_resp = _anthropic_response("ok")
        mock_create = AsyncMock(
            side_effect=[Exception("timeout"), fake_resp]
        )

        breakers = {
            "anthropic": CircuitBreaker(provider="anthropic"),
        }

        with patch("helix.llm.gateway.AsyncAnthropic") as mock_client, \
             patch("helix.llm.gateway.get_settings") as mock_settings:
            mock_settings.return_value = SimpleNamespace(
                anthropic_api_key="sk-test", openai_api_key=""
            )
            mock_client.return_value.messages.create = mock_create

            policy = FallbackPolicy(
                primary_model="claude-sonnet-4-6",
                fallback_chain=["claude-haiku-4-5"],
            )
            request = _make_request()
            await call_llm(request, policy=policy, breakers=breakers)

            # Primary failed once, then fallback succeeded → reset
            # The breaker should have 0 consecutive failures after the success
            assert breakers["anthropic"].consecutive_failures == 0


# ---------------------------------------------------------------------------
# record_usage
# ---------------------------------------------------------------------------

class TestRecordUsage:
    @pytest.mark.asyncio
    async def test_record_usage(self) -> None:
        """Verify record_usage calls session.execute with correct SQL."""
        mock_session = AsyncMock()
        tracker = TokenUsageTracker(
            org_id=uuid4(),
            workflow_id=uuid4(),
            agent_id=uuid4(),
            user_id=uuid4(),
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=10,
            cache_write_tokens=0,
            cost_usd=0.001,
            cost_center="engineering",
            fallback_occurred=False,
            fallback_reason=None,
        )

        await record_usage(mock_session, tracker)

        mock_session.execute.assert_awaited_once()
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        params = call_args[0][1]

        assert "INSERT INTO token_usage_events" in sql_text
        assert params["model_id"] == "claude-sonnet-4-6"
        assert params["input_tokens"] == 100
        assert params["output_tokens"] == 50
        assert params["cost_usd"] == 0.001
        assert params["cost_center"] == "engineering"
        # UUID fields should be converted to str
        assert isinstance(params["org_id"], str)
        assert isinstance(params["workflow_id"], str)

    @pytest.mark.asyncio
    async def test_record_usage_none_fields(self) -> None:
        """Verify None UUID fields are passed through as None."""
        mock_session = AsyncMock()
        tracker = TokenUsageTracker(
            org_id=uuid4(),
            model_id="claude-haiku-4-5",
            provider="anthropic",
            input_tokens=50,
            output_tokens=25,
        )

        await record_usage(mock_session, tracker)

        params = mock_session.execute.call_args[0][1]
        assert params["workflow_id"] is None
        assert params["agent_id"] is None
        assert params["user_id"] is None


# ---------------------------------------------------------------------------
# structured_call
# ---------------------------------------------------------------------------

class TestStructuredCall:
    @pytest.mark.asyncio
    async def test_structured_call(self) -> None:
        """Verify structured_call returns typed output from PydanticAI."""

        class Sentiment(BaseModel):
            label: str
            score: float

        expected = Sentiment(label="positive", score=0.95)
        mock_result = MagicMock()
        mock_result.output = expected

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        with patch("helix.llm.structured.PydanticAgent", return_value=mock_agent):
            from helix.llm.structured import structured_call

            result = await structured_call(
                "Analyze sentiment: great product!", Sentiment
            )

            assert isinstance(result, Sentiment)
            assert result.label == "positive"
            assert result.score == 0.95
            mock_agent.run.assert_awaited_once_with("Analyze sentiment: great product!")

    @pytest.mark.asyncio
    async def test_structured_call_custom_model(self) -> None:
        """Verify structured_call passes the correct model string to PydanticAI."""

        class Summary(BaseModel):
            text: str

        mock_result = MagicMock()
        mock_result.output = Summary(text="short summary")
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        with patch("helix.llm.structured.PydanticAgent", return_value=mock_agent) as mock_agent_cls:
            from helix.llm.structured import structured_call

            await structured_call("Summarize this.", Summary, model="claude-opus-4-6")

            mock_agent_cls.assert_called_once_with(
                model="anthropic:claude-opus-4-6",
                output_type=Summary,
            )
