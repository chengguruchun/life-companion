"""HITL gate for high / irreversible actions.

HITL decisions use **effective_safety_level** = max(proposal.safety_level,
tool_actions[*].safety_level) (with send/delete heuristics). A proposal that
self-declares LOW but includes a HIGH tool action is gated as HIGH.
"""

from __future__ import annotations

from typing import Optional

from life_companion.models.proposal import Proposal, ToolAction
from life_companion.models.safety import (
    HITL_REQUIRED_LEVELS,
    DecisionRecord,
    HitlBlockedError,
    SafetyLevel,
)
from life_companion.safety.decision_log import DecisionLog

_LEVEL_RANK = {
    SafetyLevel.LOW: 0,
    SafetyLevel.MEDIUM: 1,
    SafetyLevel.HIGH: 2,
    SafetyLevel.IRREVERSIBLE: 3,
}


def effective_safety_level(proposal: Proposal) -> SafetyLevel:
    """Max safety level across proposal and its tool_actions.

    This effective (max action) risk is what HITL uses — not proposal
    self-declaration alone.
    """
    level = getattr(proposal, "safety_level", None) or SafetyLevel.LOW
    if not isinstance(level, SafetyLevel):
        level = SafetyLevel(str(level))
    best = level
    for action in proposal.tool_actions or []:
        a_level = getattr(action, "safety_level", None) or SafetyLevel.LOW
        if not isinstance(a_level, SafetyLevel):
            a_level = SafetyLevel(str(a_level))
        # Heuristic: mutating HITL email/delete bumps to high/irreversible
        if a_level == SafetyLevel.LOW:
            tool = (action.tool or "").lower()
            requires = getattr(action, "requires_hitl", False) or getattr(
                action, "requires_hitl", False
            )
            if requires or "send" in tool or "delete" in tool:
                a_level = SafetyLevel.HIGH
            if "delete_goal" in tool or "cancel_others" in tool or "email_draft_send" in tool:
                a_level = (
                    SafetyLevel.IRREVERSIBLE
                    if "delete" in tool or "cancel_others" in tool
                    else SafetyLevel.HIGH
                )
        if _LEVEL_RANK[a_level] > _LEVEL_RANK[best]:
            best = a_level
    return best


def ensure_hitl_or_raise(
    proposal: Proposal,
    *,
    human_approved: bool = False,
    force: bool = False,
) -> SafetyLevel:
    """Block execute unless human_approved for high/irreversible *effective* risk.

    If force=True, allow through but caller must log human_override.
    """
    level = effective_safety_level(proposal)
    if level in HITL_REQUIRED_LEVELS and not human_approved and not force:
        raise HitlBlockedError(
            f"Execution blocked: effective_safety_level={level.value} "
            f"(proposal declared {getattr(proposal.safety_level, 'value', proposal.safety_level)}) "
            f"requires human_approved=True",
            safety_level=level,
            proposal_id=proposal.proposal_id,
        )
    return level


def _proposal_declared_level(proposal: Proposal) -> SafetyLevel:
    level = getattr(proposal, "safety_level", None) or SafetyLevel.LOW
    if not isinstance(level, SafetyLevel):
        level = SafetyLevel(str(level))
    return level


def gate_execution(
    proposal: Proposal,
    *,
    human_approved: bool = False,
    force: bool = False,
    human_feedback: Optional[str] = None,
    decision_log: Optional[DecisionLog] = None,
    critic_verdict: Optional[str] = None,
    critic_objections: Optional[list] = None,
    goals_involved: Optional[list[str]] = None,
    constraints: Optional[list[str]] = None,
    context: Optional[dict] = None,
) -> DecisionRecord:
    """Gate execute and append a DecisionRecord.

    Returns the decision record. Raises HitlBlockedError if blocked (still logs).
    Records both proposal_safety_level and effective_safety_level; ``safety_level``
    mirrors effective for backward compatibility. Propagates proposal.trace_id.
    """
    log = decision_log or DecisionLog()
    declared = _proposal_declared_level(proposal)
    level = effective_safety_level(proposal)
    objections = critic_objections or []
    obj_dicts = [
        o.model_dump() if hasattr(o, "model_dump") else dict(o) for o in objections
    ]
    trace_id = getattr(proposal, "trace_id", None)
    base_ctx = dict(context or {})
    if trace_id:
        base_ctx.setdefault("trace_id", trace_id)

    def _make_rec(**kwargs) -> DecisionRecord:
        return DecisionRecord(
            trace_id=trace_id,
            proposal_safety_level=declared,
            effective_safety_level=level,
            safety_level=level,
            **kwargs,
        )

    try:
        ensure_hitl_or_raise(proposal, human_approved=human_approved, force=force)
    except HitlBlockedError as err:
        rec = _make_rec(
            decision="blocked_hitl",
            context=base_ctx,
            goals_involved=goals_involved or [],
            constraints=constraints or [f"safety:{level.value}"],
            proposal_summary=proposal.summary,
            proposal_id=proposal.proposal_id,
            critic_objections=obj_dicts,
            critic_verdict=critic_verdict,
            final_decision="blocked_hitl",
            human_feedback=human_feedback,
            human_override=False,
            notes=[str(err), "HITL uses effective (max action) risk, not proposal self-declaration alone"],
        )
        log.append(rec)
        raise

    override = bool(force and level in HITL_REQUIRED_LEVELS and not human_approved)
    if human_approved and level in HITL_REQUIRED_LEVELS:
        final = "execute_approved"
        decision = "execute"
    elif override:
        final = "execute_forced_override"
        decision = "forced_override"
    else:
        final = "execute"
        decision = "execute"

    notes = []
    if human_approved:
        notes.append("HITL approved")
    elif override:
        notes.append("forced override")
    if declared != level:
        notes.append(
            f"effective_safety_level={level.value} > proposal_safety_level={declared.value}"
        )

    rec = _make_rec(
        decision=decision,
        context=base_ctx,
        goals_involved=goals_involved or [],
        constraints=constraints or [],
        proposal_summary=proposal.summary,
        proposal_id=proposal.proposal_id,
        critic_objections=obj_dicts,
        critic_verdict=critic_verdict,
        final_decision=final,
        human_feedback=human_feedback,
        human_override=override,
        notes=notes,
    )
    log.append(rec)
    return rec
