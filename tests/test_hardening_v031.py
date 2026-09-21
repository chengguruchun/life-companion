"""v0.3.1 hardening: effective safety + trace_id propagation."""

from __future__ import annotations

from pathlib import Path

import pytest

from life_companion.demo_data import sample_hitl_email_proposal, sample_late_night_plan_proposal
from life_companion.loop.life_loop import run_life_loop_dry
from life_companion.models.outcome import Metrics
from life_companion.models.proposal import Proposal, ProposalType, ToolAction
from life_companion.models.safety import SafetyLevel
from life_companion.safety.decision_log import DecisionLog
from life_companion.safety.hitl import (
    HitlBlockedError,
    effective_safety_level,
    gate_execution,
)
from life_companion.store.json_store import LocalStore


def test_effective_safety_level_maxes_tool_actions() -> None:
    """Proposal declares LOW but tool is HIGH → effective HIGH (HITL uses effective)."""
    p = Proposal(
        type=ProposalType.SEND_EMAIL,
        summary="draft then send",
        safety_level=SafetyLevel.LOW,
        tool_actions=[
            ToolAction(
                tool="email_draft_send",
                args={"to": "a@b.c"},
                mutating=True,
                requires_hitl=True,
                safety_level=SafetyLevel.HIGH,
            )
        ],
    )
    assert p.safety_level == SafetyLevel.LOW
    assert effective_safety_level(p) == SafetyLevel.HIGH
    with pytest.raises(HitlBlockedError) as ei:
        gate_execution(p, human_approved=False)
    assert ei.value.safety_level == SafetyLevel.HIGH


def test_gate_records_proposal_and_effective_levels(tmp_path: Path) -> None:
    dlog = DecisionLog(tmp_path / "decisions.jsonl")
    p = Proposal(
        type=ProposalType.SEND_EMAIL,
        summary="send",
        safety_level=SafetyLevel.LOW,
        tool_actions=[
            ToolAction(
                tool="email_draft_send",
                mutating=True,
                requires_hitl=True,
                safety_level=SafetyLevel.HIGH,
            )
        ],
    )
    with pytest.raises(HitlBlockedError):
        gate_execution(p, human_approved=False, decision_log=dlog)
    rec = dlog.read_all()[-1]
    assert rec.proposal_safety_level == SafetyLevel.LOW
    assert rec.effective_safety_level == SafetyLevel.HIGH
    assert rec.safety_level == SafetyLevel.HIGH  # alias of effective
    assert rec.trace_id == p.trace_id


def test_trace_id_propagates_through_life_loop(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    proposal = sample_late_night_plan_proposal()
    tid = proposal.trace_id
    result = run_life_loop_dry(
        proposal,
        store=store,
        human_approved=True,
        actual=Metrics(
            sleep_hours=5.5, work_progress=0.4, life_happiness=0.4, fatigue=0.7
        ),
    )
    assert result.hitl_blocked is False
    assert result.decision is not None
    assert result.outcome is not None
    assert result.feedback is not None
    assert result.execution is not None
    assert result.decision.trace_id == tid
    assert result.outcome.trace_id == tid
    assert result.execution.trace_id == tid
    assert result.feedback.trace_id == tid
    assert result.context.get("trace_id") == tid
    # soft prefs marked provisional / legacy_v02
    prefs = store.load_preferences()
    soft = {k: v for k, v in prefs.items() if str(k).startswith("soft:")}
    assert soft
    for v in soft.values():
        assert v.get("provisional") is True
        assert v.get("legacy_v02") is True
    hyp = prefs.get("_hypotheses")
    assert isinstance(hyp, dict)
    assert hyp.get("provisional") is True
    assert hyp.get("legacy_v02") is True
