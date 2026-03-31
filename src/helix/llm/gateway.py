"""Multi-provider LLM gateway with fallback policies.

Adapted from Claude Code's 46K-line QueryEngine:
- CC uses while(true) retry loop with 3 silent model downgrades
- CC's circuit breaker limits consecutive failures to 3
- CC's system prompt splits static (cacheable) from dynamic sections

Key improvements:
- Multi-provider support (not just Anthropic)
- Transparent fallback with audit events (arch decision #5)
- Per-tenant rate limiting and cost tracking
- Configurable fallback policies per org
"""

import time
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from helix.config import get_settings

logger = structlog.get_logger()


class ModelConfig(BaseModel):
    """Configuration for a single LLM model."""

    model_id: str
    provider: str  # anthropic | openai | azure | bedrock
    input_cost_per_mtok: float  # $ per million input tokens
    output_cost_per_mtok: float  # $ per million output tokens
    max_context_tokens: int = 200000


# Default model registry — prices as of March 2026
MODEL_REGISTRY: dict[str, ModelConfig] = {
    "claude-opus-4-6": ModelConfig(
        model_id="claude-opus-4-6",
        provider="anthropic",
        input_cost_per_mtok=15.0,
        output_cost_per_mtok=75.0,
        max_context_tokens=200000,
    ),
    "claude-sonnet-4-6": ModelConfig(
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        input_cost_per_mtok=3.0,
        output_cost_per_mtok=15.0,
        max_context_tokens=200000,
    ),
    "claude-haiku-4-5": ModelConfig(
        model_id="claude-haiku-4-5",
        provider="anthropic",
        input_cost_per_mtok=0.8,
        output_cost_per_mtok=4.0,
        max_context_tokens=200000,
    ),
}


class FallbackPolicy(BaseModel):
    """Model fallback policy per org.

    Claude Code silently downgrades: Opus → Sonnet on 529 errors,
    non-streaming fallback on hang, exponential backoff on rate limits.
    We make fallback transparent and configurable (arch decision #5).
    """

    primary_model: str = "claude-sonnet-4-6"
    fallback_chain: list[str] = Field(
        default_factory=lambda: ["claude-haiku-4-5"]
    )
    allow_silent_downgrade: bool = True  # CC default; enterprise can set False
    max_retries: int = 3  # CC's circuit breaker threshold


class LLMRequest(BaseModel):
    """Request to the LLM gateway."""

    messages: list[dict[str, Any]]
    model: str | None = None  # None = use org's primary model
    tools: list[dict[str, Any]] = Field(default_factory=list)
    org_id: UUID
    workflow_id: UUID | None = None
    agent_id: UUID | None = None
    temperature: float = 0.0
    max_tokens: int = 4096


class LLMResponse(BaseModel):
    """Response from the LLM gateway."""

    id: UUID = Field(default_factory=uuid4)
    content: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    model_used: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0
    fallback_occurred: bool = False
    fallback_reason: str | None = None
    latency_ms: int = 0


class CircuitBreaker(BaseModel):
    """Circuit breaker for LLM provider health.

    Claude Code: circuit breaker at 3 consecutive failures.
    We add per-provider tracking and configurable cooldown.
    """

    provider: str
    consecutive_failures: int = 0
    max_failures: int = 3  # CC's threshold
    cooldown_seconds: int = 60
    last_failure_at: datetime | None = None
    is_open: bool = False  # True = provider is down, skip it

    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.consecutive_failures += 1
        self.last_failure_at = datetime.now()
        if self.consecutive_failures >= self.max_failures:
            self.is_open = True
            logger.warning(
                "circuit_breaker.opened",
                provider=self.provider,
                failures=self.consecutive_failures,
            )

    def record_success(self) -> None:
        """Record a success and reset the counter."""
        self.consecutive_failures = 0
        self.is_open = False

    def should_allow(self) -> bool:
        """Check if requests should be allowed through."""
        if not self.is_open:
            return True
        # Check if cooldown has elapsed
        if self.last_failure_at is not None:
            elapsed = (datetime.now() - self.last_failure_at).total_seconds()
            if elapsed >= self.cooldown_seconds:
                self.is_open = False  # Half-open: try one request
                return True
        return False


class TokenUsageTracker(BaseModel):
    """Track token usage per LLM call for billing attribution.

    Claude Code has no per-org cost tracking (single-user).
    We track every call for billing and cost center attribution.
    """

    org_id: UUID
    workflow_id: UUID | None = None
    agent_id: UUID | None = None
    user_id: UUID | None = None
    model_id: str
    provider: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    cost_center: str | None = None
    fallback_occurred: bool = False
    fallback_reason: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


def calculate_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
) -> float:
    """Calculate cost in USD for a given LLM call.

    Cache reads are typically 90% cheaper than regular input tokens.
    """
    config = MODEL_REGISTRY.get(model_id)
    if config is None:
        return 0.0

    input_cost = (input_tokens / 1_000_000) * config.input_cost_per_mtok
    output_cost = (output_tokens / 1_000_000) * config.output_cost_per_mtok
    cache_cost = (cache_read_tokens / 1_000_000) * config.input_cost_per_mtok * 0.1

    return round(input_cost + output_cost + cache_cost, 8)


def select_model(
    policy: FallbackPolicy,
    circuit_breakers: dict[str, CircuitBreaker] | None = None,
) -> tuple[str, bool]:
    """Select the best available model based on policy and provider health.

    Returns (model_id, fallback_occurred).

    Claude Code silently switches models. We track the fallback
    for audit trail compliance.
    """
    breakers = circuit_breakers or {}

    # Try primary model
    primary_config = MODEL_REGISTRY.get(policy.primary_model)
    if primary_config:
        breaker = breakers.get(primary_config.provider)
        if breaker is None or breaker.should_allow():
            return policy.primary_model, False

    # Try fallback chain
    for fallback_model in policy.fallback_chain:
        config = MODEL_REGISTRY.get(fallback_model)
        if config:
            breaker = breakers.get(config.provider)
            if breaker is None or breaker.should_allow():
                logger.info(
                    "llm.fallback",
                    primary=policy.primary_model,
                    selected=fallback_model,
                )
                return fallback_model, True

    # All models unavailable — return primary and let it fail
    logger.error("llm.all_models_unavailable", policy=policy.model_dump())
    return policy.primary_model, True


async def _call_anthropic(
    request: LLMRequest, model_id: str
) -> tuple[str, int, int, int, list[dict[str, Any]]]:
    """Call Anthropic Messages API and return (content, input_tokens, output_tokens, cache_read_tokens, tool_calls)."""
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Separate system messages from user/assistant messages
    system_parts: list[str] = []
    non_system: list[dict[str, Any]] = []
    for msg in request.messages:
        if msg.get("role") == "system":
            system_parts.append(msg["content"])
        else:
            non_system.append(msg)

    kwargs: dict[str, Any] = {
        "model": model_id,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "messages": non_system,
    }
    if system_parts:
        kwargs["system"] = "\n".join(system_parts)
    if request.tools:
        kwargs["tools"] = request.tools

    response = await client.messages.create(**kwargs)

    content = ""
    tool_calls: list[dict[str, Any]] = []
    for block in response.content:
        if block.type == "text":
            content += block.text
        elif block.type == "tool_use":
            tool_calls.append(
                {"id": block.id, "name": block.name, "input": block.input}
            )

    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    return content, usage.input_tokens, usage.output_tokens, cache_read, tool_calls


async def _call_openai(
    request: LLMRequest, model_id: str
) -> tuple[str, int, int, int, list[dict[str, Any]]]:
    """Call OpenAI Chat Completions API and return (content, input_tokens, output_tokens, cache_read_tokens, tool_calls)."""
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    kwargs: dict[str, Any] = {
        "model": model_id,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "messages": request.messages,
    }
    if request.tools:
        kwargs["tools"] = request.tools

    response = await client.chat.completions.create(**kwargs)

    choice = response.choices[0]
    content = choice.message.content or ""
    tool_calls: list[dict[str, Any]] = []
    if choice.message.tool_calls:
        for tc in choice.message.tool_calls:
            tool_calls.append(
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": tc.function.arguments,
                }
            )

    usage = response.usage
    input_tokens = usage.prompt_tokens if usage else 0
    output_tokens = usage.completion_tokens if usage else 0
    return content, input_tokens, output_tokens, 0, tool_calls


async def call_llm(
    request: LLMRequest,
    policy: FallbackPolicy | None = None,
    breakers: dict[str, CircuitBreaker] | None = None,
) -> LLMResponse:
    """Execute an LLM call with fallback and circuit-breaker support.

    Args:
        request: The LLM request with messages, model preference, and metadata.
        policy: Fallback policy to use. Defaults to a standard policy.
        breakers: Circuit breakers keyed by provider name.

    Returns:
        Populated LLMResponse with content, usage, cost, and latency.
    """
    if policy is None:
        policy = FallbackPolicy(
            primary_model=request.model or "claude-sonnet-4-6",
        )
    elif request.model:
        policy = policy.model_copy(update={"primary_model": request.model})

    breakers = breakers or {}

    # Build ordered list of models to try: primary + fallback chain
    models_to_try = [policy.primary_model, *policy.fallback_chain]
    last_error: Exception | None = None

    for idx, model_id in enumerate(models_to_try):
        config = MODEL_REGISTRY.get(model_id)
        if config is None:
            logger.warning("llm.unknown_model", model_id=model_id)
            continue

        breaker = breakers.get(config.provider)
        if breaker and not breaker.should_allow():
            logger.info("llm.circuit_open", provider=config.provider, model=model_id)
            continue

        fallback_occurred = idx > 0
        start = time.monotonic()

        try:
            if config.provider == "anthropic":
                content, in_tok, out_tok, cache_tok, tool_calls = await _call_anthropic(
                    request, model_id
                )
            elif config.provider == "openai":
                content, in_tok, out_tok, cache_tok, tool_calls = await _call_openai(
                    request, model_id
                )
            else:
                raise ValueError(f"Unsupported provider: {config.provider}")

            elapsed_ms = int((time.monotonic() - start) * 1000)
            cost = calculate_cost(model_id, in_tok, out_tok, cache_tok)

            if breaker:
                breaker.record_success()

            logger.info(
                "llm.call_success",
                model=model_id,
                provider=config.provider,
                input_tokens=in_tok,
                output_tokens=out_tok,
                latency_ms=elapsed_ms,
                fallback=fallback_occurred,
            )

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                model_used=model_id,
                provider=config.provider,
                input_tokens=in_tok,
                output_tokens=out_tok,
                cache_read_tokens=cache_tok,
                cost_usd=cost,
                fallback_occurred=fallback_occurred,
                fallback_reason=str(last_error) if fallback_occurred else None,
                latency_ms=elapsed_ms,
            )

        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            last_error = exc
            logger.warning(
                "llm.call_failed",
                model=model_id,
                provider=config.provider,
                error=str(exc),
                latency_ms=elapsed_ms,
            )
            if breaker:
                breaker.record_failure()
            continue

    # All models exhausted
    raise RuntimeError(
        f"All LLM models failed. Last error: {last_error}"
    )
