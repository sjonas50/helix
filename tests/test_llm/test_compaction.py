"""Tests for context compaction engine."""


from helix.llm.compaction import (
    CompactionConfig,
    calculate_output_headroom,
    create_micro_compaction_reference,
    estimate_tokens,
    should_auto_compact,
    should_micro_compact,
)


class TestShouldAutoCompact:
    def test_below_threshold(self) -> None:
        assert not should_auto_compact(100_000)  # 50% of 200K

    def test_at_threshold(self) -> None:
        # 83.5% of 200K = 167K
        assert should_auto_compact(167_000)

    def test_above_threshold(self) -> None:
        assert should_auto_compact(180_000)

    def test_custom_config(self) -> None:
        config = CompactionConfig(auto_compaction_pct=50.0, max_context_tokens=100_000)
        assert not should_auto_compact(49_000, config)
        assert should_auto_compact(50_000, config)


class TestShouldMicroCompact:
    def test_small_output(self) -> None:
        assert not should_micro_compact(1000)  # 1KB < 8KB threshold

    def test_large_output(self) -> None:
        assert should_micro_compact(10_000)  # 10KB > 8KB threshold

    def test_custom_threshold(self) -> None:
        config = CompactionConfig(micro_compaction_threshold_bytes=4096)
        assert should_micro_compact(5000, config)
        assert not should_micro_compact(3000, config)


class TestMicroCompactionReference:
    def test_creates_reference(self) -> None:
        ref = create_micro_compaction_reference(
            tool_name="list_opportunities",
            output_size_bytes=50_000,
            storage_key="s3://helix-artifacts/abc123",
        )
        assert ref["type"] == "micro_compaction_reference"
        assert ref["tool_name"] == "list_opportunities"
        assert ref["output_size_bytes"] == 50_000
        assert "s3://" in ref["storage_key"]


class TestEstimateTokens:
    def test_rough_estimate(self) -> None:
        text = "a" * 400
        assert estimate_tokens(text) == 100  # ~4 chars per token


class TestOutputHeadroom:
    def test_default_headroom(self) -> None:
        # 100% - 83.5% = 16.5% of 200K = 33K
        headroom = calculate_output_headroom()
        assert headroom == 33000

    def test_custom_headroom(self) -> None:
        config = CompactionConfig(auto_compaction_pct=80.0, max_context_tokens=100_000)
        headroom = calculate_output_headroom(config)
        assert headroom == 20_000
