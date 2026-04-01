"""Tests for LLM-powered signal extraction in the Gather phase."""

from unittest.mock import AsyncMock, patch

import pytest

from helix.memory.gather import ExtractedSignals, extract_signals_from_memories


class TestExtractSignals:
    @pytest.mark.asyncio
    async def test_empty_memories_returns_empty(self):
        signals = await extract_signals_from_memories([])
        assert signals == []

    @pytest.mark.asyncio
    async def test_extracts_signals_from_memories(self):
        # Mock structured_call to return test signals
        mock_result = ExtractedSignals(
            corrections=["Use async for all I/O"],
            decisions=["Chose LangGraph over custom FSM"],
            themes=["Team is focused on performance"],
        )
        with patch(
            "helix.llm.structured.structured_call",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            memories = [
                {
                    "topic": "architecture",
                    "content": "Decided to use LangGraph",
                    "source_system": "slack",
                },
                {
                    "topic": "performance",
                    "content": "Switched to async I/O",
                    "source_system": "jira",
                },
            ]
            signals = await extract_signals_from_memories(memories)
            assert len(signals) == 3  # 1 correction + 1 decision + 1 theme
            types = {s.signal_type for s in signals}
            assert types == {"correction", "decision", "theme"}

    @pytest.mark.asyncio
    async def test_handles_llm_failure_gracefully(self):
        with patch(
            "helix.llm.structured.structured_call",
            new_callable=AsyncMock,
            side_effect=Exception("API error"),
        ):
            signals = await extract_signals_from_memories(
                [{"topic": "test", "content": "test", "source_system": "test"}]
            )
            assert signals == []  # Graceful degradation

    @pytest.mark.asyncio
    async def test_caps_at_50_memories(self):
        mock_result = ExtractedSignals(corrections=[], decisions=[], themes=[])
        with patch(
            "helix.llm.structured.structured_call",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_call:
            memories = [
                {"topic": f"t{i}", "content": f"c{i}", "source_system": "test"}
                for i in range(100)
            ]
            await extract_signals_from_memories(memories)
            # Check prompt doesn't include all 100
            prompt = mock_call.call_args[0][0]
            assert prompt.count("[test]") <= 50

    @pytest.mark.asyncio
    async def test_signal_confidence_values(self):
        mock_result = ExtractedSignals(
            corrections=["fix X"],
            decisions=["use Y"],
            themes=["pattern Z"],
        )
        with patch(
            "helix.llm.structured.structured_call",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            signals = await extract_signals_from_memories(
                [{"topic": "t", "content": "c", "source_system": "s"}]
            )
            by_type = {s.signal_type: s for s in signals}
            assert by_type["correction"].confidence == 0.8
            assert by_type["decision"].confidence == 0.9
            assert by_type["theme"].confidence == 0.7

    @pytest.mark.asyncio
    async def test_all_signals_share_session_id(self):
        mock_result = ExtractedSignals(
            corrections=["a"],
            decisions=["b"],
            themes=["c"],
        )
        with patch(
            "helix.llm.structured.structured_call",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            signals = await extract_signals_from_memories(
                [{"topic": "t", "content": "c", "source_system": "s"}]
            )
            session_ids = {s.session_id for s in signals}
            assert len(session_ids) == 1  # All grouped under one session
