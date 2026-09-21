"""Proposal → (optional) critic → at most one revise → execute/ask path."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from life_companion.agents.critic_gate import should_invoke_critic
from life_companion.agents.dry_run_critic import apply_suggested_fixes, rule_based_critic
from life_companion.models.proposal import Proposal, Review, Verdict
from life_companion.store.json_store import LocalStore


@dataclass
class PipelineResult:
    proposal: Proposal
    review: Optional[Review]
    revised: bool
    critic_invoked: bool
    critic_skipped_reason: Optional[str]
    status: str  # execute | ask_user | rejected | skipped_execute_dry
    notes: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


def run_proposal_pipeline(
    proposal: Proposal,
    *,
    dry_run: bool = True,
    store: Optional[LocalStore] = None,
    live_critic: Any = None,
) -> PipelineResult:
    """Run critic gate + at most one revise round.

    dry_run=True: deterministic rule-based critic (no API key).
    live_critic: optional callable(proposal) -> Review when dry_run=False.
    """
    notes: list[str] = []
    store = store or LocalStore()

    invoke = should_invoke_critic(proposal)
    if not invoke:
        reason = None
        if proposal.user_override_skip_critic:
            reason = "user_override_skip_critic"
            store.log_critic_override(proposal.proposal_id, reason)
            notes.append("Critic skipped by user override; logged.")
        else:
            reason = "trigger_gate_skip"
            notes.append("Critic skipped (read-only / trivial).")
        return PipelineResult(
            proposal=proposal,
            review=None,
            revised=False,
            critic_invoked=False,
            critic_skipped_reason=reason,
            status="execute" if not dry_run else "skipped_execute_dry",
            notes=notes,
        )

    # Critic
    if dry_run or live_critic is None:
        review = rule_based_critic(proposal, revised=False)
        notes.append("Used rule-based critic stub (dry-run).")
    else:
        review = live_critic(proposal)
        notes.append("Used live critic.")

    revised = False
    current = proposal

    if review.verdict == Verdict.CONDITIONAL_PASS:
        current = apply_suggested_fixes(current, review)
        revised = True
        notes.append("Planner revised once after conditional_pass.")
        if dry_run or live_critic is None:
            review = rule_based_critic(current, revised=True)
        else:
            review = live_critic(current)
        notes.append("Second critic pass after revise.")

    if review.verdict == Verdict.REJECT:
        return PipelineResult(
            proposal=current,
            review=review,
            revised=revised,
            critic_invoked=True,
            critic_skipped_reason=None,
            status="ask_user" if revised else "rejected",
            notes=notes + ["Rejected or still failing after one revise — ask user."],
        )

    if review.verdict == Verdict.CONDITIONAL_PASS:
        # After one revise still conditional → ask user (DESIGN: at most one revise)
        return PipelineResult(
            proposal=current,
            review=review,
            revised=revised,
            critic_invoked=True,
            critic_skipped_reason=None,
            status="ask_user",
            notes=notes + ["Still conditional after one revise — ask user."],
        )

    # pass
    status = "skipped_execute_dry" if dry_run else "execute"
    return PipelineResult(
        proposal=current,
        review=review,
        revised=revised,
        critic_invoked=True,
        critic_skipped_reason=None,
        status=status,
        notes=notes,
    )
