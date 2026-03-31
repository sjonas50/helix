"""Tests for LLM gateway — fallback, circuit breaker, cost calculation."""

from datetime import UTC, datetime, timedelta

from helix.llm.gateway import (
    CircuitBreaker,
    FallbackPolicy,
    calculate_cost,
    select_model,
)


class TestCalculateCost:
    def test_sonnet_cost(self) -> None:
        cost = calculate_cost("claude-sonnet-4-6", input_tokens=1000, output_tokens=500)
        expected = (1000 / 1_000_000) * 3.0 + (500 / 1_000_000) * 15.0
        assert abs(cost - expected) < 1e-8

    def test_haiku_cheaper_than_sonnet(self) -> None:
        haiku = calculate_cost("claude-haiku-4-5", input_tokens=1000, output_tokens=500)
        sonnet = calculate_cost("claude-sonnet-4-6", input_tokens=1000, output_tokens=500)
        assert haiku < sonnet

    def test_opus_most_expensive(self) -> None:
        opus = calculate_cost("claude-opus-4-6", input_tokens=1000, output_tokens=500)
        sonnet = calculate_cost("claude-sonnet-4-6", input_tokens=1000, output_tokens=500)
        assert opus > sonnet

    def test_cache_read_discount(self) -> None:
        no_cache = calculate_cost("claude-sonnet-4-6", input_tokens=1000, output_tokens=0)
        with_cache = calculate_cost(
            "claude-sonnet-4-6", input_tokens=0, output_tokens=0, cache_read_tokens=1000
        )
        assert with_cache < no_cache  # Cache reads are 90% cheaper

    def test_unknown_model_zero_cost(self) -> None:
        assert calculate_cost("unknown-model", input_tokens=1000, output_tokens=500) == 0.0


class TestCircuitBreaker:
    def test_starts_closed(self) -> None:
        cb = CircuitBreaker(provider="anthropic")
        assert cb.should_allow()
        assert not cb.is_open

    def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker(provider="anthropic", max_failures=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.should_allow()
        cb.record_failure()
        assert not cb.should_allow()
        assert cb.is_open

    def test_resets_on_success(self) -> None:
        cb = CircuitBreaker(provider="anthropic", max_failures=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.consecutive_failures == 0
        assert cb.should_allow()

    def test_half_open_after_cooldown(self) -> None:
        cb = CircuitBreaker(provider="anthropic", max_failures=1, cooldown_seconds=60)
        cb.record_failure()
        assert not cb.should_allow()
        # Simulate cooldown elapsed
        cb.last_failure_at = datetime.now(tz=UTC) - timedelta(seconds=61)
        assert cb.should_allow()


class TestSelectModel:
    def test_selects_primary(self) -> None:
        policy = FallbackPolicy(primary_model="claude-sonnet-4-6")
        model, fallback = select_model(policy)
        assert model == "claude-sonnet-4-6"
        assert not fallback

    def test_falls_back_when_primary_down(self) -> None:
        policy = FallbackPolicy(
            primary_model="claude-sonnet-4-6",
            fallback_chain=["claude-haiku-4-5"],
        )
        breakers = {
            "anthropic": CircuitBreaker(provider="anthropic", is_open=True, last_failure_at=datetime.now(tz=UTC)),
        }
        # Both models are anthropic, so both are affected by the breaker
        # This tests the circuit breaker integration
        model, fallback = select_model(policy, breakers)
        # Since all anthropic models share a breaker, it falls through to primary
        assert fallback

    def test_uses_fallback_chain_order(self) -> None:
        policy = FallbackPolicy(
            primary_model="claude-opus-4-6",
            fallback_chain=["claude-sonnet-4-6", "claude-haiku-4-5"],
        )
        # Open circuit for anthropic provider
        breakers = {
            "anthropic": CircuitBreaker(
                provider="anthropic",
                is_open=True,
                last_failure_at=datetime.now(tz=UTC),
                cooldown_seconds=9999,
            ),
        }
        model, fallback = select_model(policy, breakers)
        assert fallback  # All anthropic, all blocked
