"""v0.3 HITL gate + decision log tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from life_companion.demo_data import sample_day_plan_proposal, sample_hitl_email_proposal
from life_companion.models.safety import SafetyLevel
from life_companion.safety.decision_log import DecisionLog
from life_companion.safety.hitl import (
    HitlBlockedError,
    effective_safety_level,
    ensure_hitl_or_raise,
    gate_execution,
)
from life_companion.store.json_store import LocalStore


def test_effective_safety_level_email_is_high() -> None:
    p = sample_hitl_email_proposal()
    level = effective_safety_level(p)
    assert level in (SafetyLevel.HIGH, SafetyLevel.IRREVERSIBLE)


def test_hitl_blocks_without_approval() -> None:
    p = sample_hitl_email_proposal()
    with pytest.raises(HitlBlockedError):
        ensure_hitl_or_raise(p, human_approved=False)


def test_hitl_allows_with_approval() -> None:
    p = sample_hitl_email_proposal()
    level = ensure_hitl_or_raise(p, human_approved=True)
    assert level in (SafetyLevel.HIGH, SafetyLevel.IRREVERSIBLE)


def test_gate_logs_block_and_approve(tmp_path: Path) -> None:
    dlog = DecisionLog(tmp_path / "decisions.jsonl")
    p = sample_hitl_email_proposal()
    with pytest.raises(HitlBlockedError):
        gate_execution(p, human_approved=False, decision_log=dlog)
    rows = dlog.read_all()
    assert rows and rows[-1].final_decision in ("blocked_hitl", "blocked")
    rec = gate_execution(
        p, human_approved=True, human_feedback="lgtm", decision_log=dlog
    )
    assert "execute" in rec.final_decision
    assert rec.human_override is False
    assert len(dlog.read_all()) >= 2


def test_force_override_logged(tmp_path: Path) -> None:
    dlog = DecisionLog(tmp_path / "decisions.jsonl")
    p = sample_hitl_email_proposal()
    rec = gate_execution(
        p, human_approved=False, force=True, human_feedback="emergency", decision_log=dlog
    )
    assert rec.human_override is True
    assert "force" in rec.final_decision or "override" in rec.final_decision


def test_low_safety_day_plan_no_hitl_required() -> None:
    p = sample_day_plan_proposal(bad=False)
    # should not raise
    ensure_hitl_or_raise(p, human_approved=False)
    assert effective_safety_level(p) in (SafetyLevel.LOW, SafetyLevel.MEDIUM)


def test_decision_log_roundtrip(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    dlog = DecisionLog(store.decisions_path)
    p = sample_hitl_email_proposal()
    rec = gate_execution(p, human_approved=True, decision_log=dlog)
    store.save_decision(rec)
    loaded = store.load_decisions()
    assert any(r.decision_id == rec.decision_id for r in loaded)
    assert dlog.find_by_id(rec.decision_id) is not None
    assert dlog.find_by_proposal(p.proposal_id)
