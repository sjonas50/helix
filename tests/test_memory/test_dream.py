"""Tests for Dream Cycle — 4-phase memory consolidation."""

import uuid
from datetime import datetime, timedelta

from helix.memory.dream import (
    DreamPhase,
    DreamTriggerConfig,
    SessionSignal,
    consolidate_phase,
    gather_phase,
    orient_phase,
    prune_phase,
    run_dream_cycle,
    should_trigger_dream,
)
from helix.memory.store import create_memory


class TestShouldTriggerDream:
    def test_triggers_when_no_prior_run(self) -> None:
        assert should_trigger_dream(last_run_at=None, sessions_since_last_run=5)

    def test_does_not_trigger_too_soon(self) -> None:
        recent = datetime.now() - timedelta(hours=12)
        assert not should_trigger_dream(last_run_at=recent, sessions_since_last_run=10)

    def test_does_not_trigger_too_few_sessions(self) -> None:
        old = datetime.now() - timedelta(hours=48)
        assert not should_trigger_dream(last_run_at=old, sessions_since_last_run=2)

    def test_triggers_when_both_gates_pass(self) -> None:
        old = datetime.now() - timedelta(hours=48)
        assert should_trigger_dream(last_run_at=old, sessions_since_last_run=10)

    def test_custom_config(self) -> None:
        config = DreamTriggerConfig(min_hours_between_runs=1, min_sessions_between_runs=1)
        recent = datetime.now() - timedelta(hours=2)
        assert should_trigger_dream(last_run_at=recent, sessions_since_last_run=1, config=config)


class TestOrientPhase:
    def test_groups_by_topic(self) -> None:
        org = uuid.uuid4()
        memories = [
            create_memory(org_id=org, topic="onboarding", content="step 1"),
            create_memory(org_id=org, topic="onboarding", content="step 2"),
            create_memory(org_id=org, topic="pricing", content="tier 1"),
        ]
        index = orient_phase(memories)
        assert len(index) == 2
        assert len(index["onboarding"]) == 2
        assert len(index["pricing"]) == 1

    def test_excludes_invalidated(self) -> None:
        org = uuid.uuid4()
        active = create_memory(org_id=org, topic="a", content="active")
        stale = create_memory(org_id=org, topic="b", content="stale")
        stale.valid_until = datetime.now()

        index = orient_phase([active, stale])
        assert len(index) == 1
        assert "a" in index


class TestGatherPhase:
    def test_filters_low_confidence(self) -> None:
        signals = [
            SessionSignal(
                session_id=uuid.uuid4(),
                signal_type="correction",
                content="fix",
                confidence=0.8,
            ),
            SessionSignal(
                session_id=uuid.uuid4(),
                signal_type="theme",
                content="noise",
                confidence=0.1,
            ),
        ]
        filtered = gather_phase(signals, min_confidence=0.3)
        assert len(filtered) == 1
        assert filtered[0].signal_type == "correction"


class TestConsolidatePhase:
    def test_creates_new_records(self) -> None:
        org = uuid.uuid4()
        signals = [
            SessionSignal(
                session_id=uuid.uuid4(),
                signal_type="decision",
                content="Use PostgreSQL for all state",
                confidence=0.9,
            ),
        ]
        new, invalidated = consolidate_phase({}, signals, org)
        assert len(new) == 1
        assert new[0].topic == "decision"
        assert "PostgreSQL" in new[0].content

    def test_strips_pii_during_consolidation(self) -> None:
        org = uuid.uuid4()
        signals = [
            SessionSignal(
                session_id=uuid.uuid4(),
                signal_type="contact",
                content="Reach out to john@example.com",
                confidence=0.9,
            ),
        ]
        config = DreamTriggerConfig(pii_strip_enabled=True)
        new, _ = consolidate_phase({}, signals, org, config)
        assert "john@example.com" not in new[0].content
        assert "[EMAIL_REDACTED]" in new[0].content

    def test_invalidates_old_records_on_topic_overlap(self) -> None:
        org = uuid.uuid4()
        old = create_memory(org_id=org, topic="decision", content="old decision")
        signals = [
            SessionSignal(
                session_id=uuid.uuid4(),
                signal_type="decision",
                content="new decision",
                confidence=0.9,
            ),
        ]
        topic_index = {"decision": [old]}
        new, invalidated = consolidate_phase(topic_index, signals, org)
        assert len(invalidated) == 1
        assert invalidated[0].id == old.id


class TestPrunePhase:
    def test_no_pruning_under_limit(self) -> None:
        org = uuid.uuid4()
        records = [create_memory(org_id=org, topic=f"t{i}", content=f"c{i}") for i in range(5)]
        pruned = prune_phase(records, max_records=10)
        assert len(pruned) == 0

    def test_prunes_oldest_when_over_limit(self) -> None:
        org = uuid.uuid4()
        records = []
        for i in range(10):
            entry = create_memory(org_id=org, topic=f"t{i}", content=f"c{i}")
            entry.valid_from = datetime.now() - timedelta(days=10 - i)
            records.append(entry)

        pruned = prune_phase(records, max_records=7)
        assert len(pruned) == 3
        # Should prune the 3 oldest
        for p in pruned:
            assert p.valid_until is not None


class TestRunDreamCycle:
    def test_full_cycle(self) -> None:
        org = uuid.uuid4()
        existing = [
            create_memory(org_id=org, topic="ops", content="existing process"),
        ]
        signals = [
            SessionSignal(
                session_id=uuid.uuid4(),
                signal_type="correction",
                content="Update: use async for all I/O",
                confidence=0.85,
            ),
            SessionSignal(
                session_id=uuid.uuid4(),
                signal_type="decision",
                content="Chose LangGraph over custom FSM",
                confidence=0.9,
            ),
        ]
        result = run_dream_cycle(org, existing, signals)
        assert result.phase == DreamPhase.COMPLETE
        assert result.completed_at is not None
        assert result.records_created >= 1
        assert result.sessions_processed >= 1

    def test_cycle_with_no_signals(self) -> None:
        org = uuid.uuid4()
        result = run_dream_cycle(org, [], [])
        assert result.phase == DreamPhase.COMPLETE
        assert result.records_created == 0
        assert result.records_pruned == 0
