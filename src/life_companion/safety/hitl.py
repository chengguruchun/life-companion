"""HITL gate for high / irreversible actions."""

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
    """Max safety level across proposal and its tool_actions."""
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
            if action.requires_hitl or "send" in tool or "delete" in tool:
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
    """Block execute unless human_approved for high/irreversible.

    If force=True, allow through but caller must log human_override.
    """
    level = effective_safety_level(proposal)
    if level in HITL_REQUIRED_LEVELS and not human_approved and not force:
        raise HitlBlockedError(
            f"Execution blocked: safety_level={level.value} requires human_approved=True",
            safety_level=level,
            proposal_id=proposal.proposal_id,
        )
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
    """
    log = decision_log or DecisionLog()
    level = effective_safety_level(proposal)
    objections = critic_objections or []
    obj_dicts = [
        o.model_dump() if hasattr(o, "model_dump") else dict(o) for o in objections
    ]

    try:
        ensure_hitl_or_raise(proposal, human_approved=human_approved, force=force)
    except HitlBlockedError as err:
        rec = DecisionRecord(
            decision="blocked_hitl",
            context=context or {},
            goals_involved=goals_involved or [],
            constraints=constraints or [f"safety:{level.value}"],
            proposal_summary=proposal.summary,
            proposal_id=proposal.proposal_id,
            critic_objections=obj_dicts,
            critic_verdict=critic_verdict,
            final_decision="blocked_hitl",
            human_feedback=human_feedback,
            human_override=False,
            safety_level=level,
            notes=[str(err)],
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

    rec = DecisionRecord(
        decision=decision,
        context=context or {},
        goals_involved=goals_involved or [],
        constraints=constraints or [],
        proposal_summary=proposal.summary,
        proposal_id=proposal.proposal_id,
        critic_objections=obj_dicts,
        critic_verdict=critic_verdict,
        final_decision=final,
        human_feedback=human_feedback,
        human_override=override,
        safety_level=level,
        notes=["HITL approved"] if human_approved else (["forced override"] if override else []),
    )
    log.append(rec)
    return rec
