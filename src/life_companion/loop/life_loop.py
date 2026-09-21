"""End-to-end Life Loop dry-run orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from life_companion.agents.pipeline import PipelineResult, run_proposal_pipeline
from life_companion.loop.feedback import apply_feedback_loop
from life_companion.loop.gap import analyze_gaps
from life_companion.models.outcome import FeedbackResult, GapReport, Metrics, Outcome
from life_companion.models.proposal import Proposal
from life_companion.models.safety import DecisionRecord
from life_companion.safety.decision_log import DecisionLog
from life_companion.safety.hitl import (
    HitlBlockedError,
    effective_safety_level,
    gate_execution,
)
from life_companion.store.json_store import LocalStore


@dataclass
class LifeLoopResult:
    pipeline: PipelineResult
    decision: Optional[DecisionRecord]
    outcome: Optional[Outcome]
    gap_report: Optional[GapReport]
    feedback: Optional[FeedbackResult]
    hitl_blocked: bool = False
    notes: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


def _default_expected(proposal: Proposal) -> Metrics:
    sleep = 7.5
    work = 0.7
    happy = 0.7
    fatigue = 0.3
    for b in proposal.today_plan or []:
        if b.start >= "22:00":
            sleep = 6.5
            fatigue = 0.5
        title_l = b.title.lower()
        if "walk" in title_l or "散步" in b.title:
            happy = 0.8
        if "deep" in title_l or "work" in title_l or "coding" in title_l:
            work = 0.75
    return Metrics(
        sleep_hours=sleep,
        work_progress=work,
        life_happiness=happy,
        fatigue=fatigue,
    )


def run_life_loop_dry(
    proposal: Proposal,
    *,
    actual: Optional[Metrics] = None,
    expected: Optional[Metrics] = None,
    store: Optional[LocalStore] = None,
    human_approved: bool = False,
    force: bool = False,
    simulate_execute: bool = True,
) -> LifeLoopResult:
    """Dry-run Life Loop (no API keys).

    proposal → critic pipeline → HITL gate → simulate execute →
    outcome → gap → feedback → memory (+ decision log).
    """
    store = store or LocalStore()
    notes: list[str] = []
    dlog = DecisionLog(store.decisions_path)

    pipe = run_proposal_pipeline(proposal, dry_run=True, store=store)
    notes.extend(pipe.notes)

    decision: Optional[DecisionRecord] = None
    outcome: Optional[Outcome] = None
    gap_report: Optional[GapReport] = None
    feedback: Optional[FeedbackResult] = None

    if pipe.status in ("rejected", "ask_user"):
        notes.append(f"Skipping execute/outcome: pipeline status={pipe.status}")
        decision = DecisionRecord(
            decision=pipe.status,
            proposal_summary=pipe.proposal.summary,
            proposal_id=pipe.proposal.proposal_id,
            critic_verdict=pipe.review.verdict.value if pipe.review else None,
            critic_objections=[
                o.model_dump() for o in (pipe.review.objections if pipe.review else [])
            ],
            final_decision=pipe.status,
            safety_level=effective_safety_level(pipe.proposal),
            notes=list(notes),
        )
        dlog.append(decision)
        store.save_decision(decision)
        return LifeLoopResult(
            pipeline=pipe,
            decision=decision,
            outcome=None,
            gap_report=None,
            feedback=None,
            notes=notes,
        )

    try:
        goals = []
        for b in pipe.proposal.today_plan or []:
            gid = getattr(b, "linked_goal_id", None)
            if gid:
                goals.append(gid)
        decision = gate_execution(
            pipe.proposal,
            human_approved=human_approved,
            force=force,
            decision_log=dlog,
            critic_verdict=pipe.review.verdict.value if pipe.review else "skipped",
            critic_objections=list(pipe.review.objections) if pipe.review else [],
            goals_involved=goals,
            constraints=list(store.load_goals().hard_constraints),
            context={"dry_run": True, "pipeline_status": pipe.status},
        )
        store.save_decision(decision)
        notes.append(
            f"Decision logged: {decision.final_decision} (safety={decision.safety_level.value})"
        )
    except HitlBlockedError as err:
        notes.append(f"HITL blocked: {err}")
        blocked = dlog.find_by_proposal(pipe.proposal.proposal_id)
        decision = blocked[-1] if blocked else None
        if decision:
            store.save_decision(decision)
        return LifeLoopResult(
            pipeline=pipe,
            decision=decision,
            outcome=None,
            gap_report=None,
            feedback=None,
            hitl_blocked=True,
            notes=notes,
        )

    if not simulate_execute:
        notes.append("simulate_execute=False; stopping after decision.")
        return LifeLoopResult(
            pipeline=pipe,
            decision=decision,
            outcome=None,
            gap_report=None,
            feedback=None,
            notes=notes,
        )

    exp = expected or _default_expected(pipe.proposal)
    act = actual or Metrics(
        sleep_hours=max(0.0, (exp.sleep_hours or 7.0) - 1.5),
        work_progress=min(1.0, (exp.work_progress or 0.7) * 0.7),
        life_happiness=max(0.0, (exp.life_happiness or 0.7) - 0.2),
        fatigue=min(1.0, (exp.fatigue or 0.3) + 0.25),
    )
    notes.append("Simulated execute + recorded outcome (dry-run).")

    outcome = Outcome(
        proposal_id=pipe.proposal.proposal_id,
        expected=exp,
        actual=act,
        notes="dry-run simulated outcome",
        decision_id=decision.decision_id if decision else None,
    )
    gap_report = analyze_gaps(outcome)
    notes.append(gap_report.summary)
    feedback = apply_feedback_loop(
        outcome, store=store, gap_report=gap_report, persist=True
    )
    notes.extend(feedback.notes)

    if decision is not None:
        linked = decision.model_copy(
            update={
                "outcome_id": outcome.outcome_id,
                "notes": list(decision.notes) + ["outcome linked"],
            }
        )
        store.save_decision(linked)
        decision = linked

    return LifeLoopResult(
        pipeline=pipe,
        decision=decision,
        outcome=outcome,
        gap_report=gap_report,
        feedback=feedback,
        notes=notes,
    )
