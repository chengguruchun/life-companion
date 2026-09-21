"""CLI: demo --dry-run end-to-end without API keys (v0.3 Life Loop + HITL)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _cmd_demo(args: argparse.Namespace) -> int:
    from life_companion.agents.pipeline import run_proposal_pipeline
    from life_companion.agents.wiring import deepagents_available, try_create_live_stack
    from life_companion.demo_data import (
        sample_day_plan_proposal,
        sample_goal_tree,
        sample_hitl_email_proposal,
        sample_late_night_plan_proposal,
        sample_preference_proposal,
        sample_read_only_proposal,
    )
    from life_companion.loop.life_loop import run_life_loop_dry
    from life_companion.models.outcome import Metrics
    from life_companion.safety.hitl import HitlBlockedError, gate_execution
    from life_companion.safety.decision_log import DecisionLog
    from life_companion.store.json_store import LocalStore
    from life_companion.tools import stubs as stub_tools

    data_dir = Path(args.data_dir)
    store = LocalStore(data_dir)
    tree = sample_goal_tree()
    store.save_goals(tree)

    print("=== Life Companion demo (v0.3.1) ===")
    print(f"data_dir: {store.data_dir}")
    print(f"dry_run: {args.dry_run}")
    print(f"deepagents_available: {deepagents_available()}")
    print()

    cal = stub_tools.calendar_list_events()
    weather = stub_tools.weather_forecast("Hangzhou")
    print("[stub] calendar events:", len(cal.get("events", [])))
    print("[stub] weather:", weather.get("summary"))
    print()

    # --- v0.1 critic pipeline scenarios ---
    print("### v0.1 Critic pipeline")
    scenarios = [
        ("read_only_skip_critic", sample_read_only_proposal()),
        ("day_plan_bad_then_revise", sample_day_plan_proposal(bad=True)),
        ("day_plan_good", sample_day_plan_proposal(bad=False)),
        ("preference_write", sample_preference_proposal()),
    ]
    results = []
    for name, proposal in scenarios:
        print(f"--- scenario: {name} ---")
        result = run_proposal_pipeline(proposal, dry_run=args.dry_run, store=store)
        verdict = result.review.verdict.value if result.review else None
        print(f"  critic_invoked={result.critic_invoked} verdict={verdict} status={result.status}")
        for n in result.notes:
            print(f"  note: {n}")
        if result.review and result.review.objections:
            for o in result.review.objections:
                print(f"  objection[{o.severity}]: {o.code}: {o.message}")
        results.append(
            {
                "scenario": name,
                "proposal_id": result.proposal.proposal_id,
                "critic_invoked": result.critic_invoked,
                "verdict": verdict,
                "status": result.status,
                "revised": result.revised,
            }
        )
        print()

    # --- v0.2 Life Loop ---
    print("### v0.2 Life Loop (proposal → critic → simulate → outcome → gap → feedback)")
    life = run_life_loop_dry(
        sample_late_night_plan_proposal(),
        store=store,
        actual=Metrics(
            sleep_hours=5.5,
            work_progress=0.45,
            life_happiness=0.45,
            fatigue=0.7,
        ),
        human_approved=True,  # day plan is low safety; approve harmless
    )
    print(f"  pipeline_status={life.pipeline.status} hitl_blocked={life.hitl_blocked}")
    print(f"  trace_id: {life.context.get('trace_id')}")
    if life.execution:
        print(f"  execution: id={life.execution.execution_id} status={life.execution.status.value}")
    if life.decision:
        print(
            f"  decision_trace: {life.decision.trace_id} "
            f"effective_safety={life.decision.safety_level.value}"
        )
    if life.gap_report:
        print(f"  gap: {life.gap_report.summary}")
        for g in life.gap_report.gaps[:4]:
            print(f"    - {g.metric}: Δ={g.delta:.2f} [{g.severity.value}] {g.message}")
    if life.feedback:
        print(f"  soft_prefs: {list(life.feedback.soft_preferences_written)}")
        print(f"  goal_tweaks: {len(life.feedback.goal_tweak_suggestions)}")
        for t in life.feedback.goal_tweak_suggestions[:3]:
            print(f"    - [{t.layer}/{t.action}] {t.title}")
    for n in life.notes:
        print(f"  note: {n}")
    results.append(
        {
            "scenario": "life_loop_sleep_gap",
            "proposal_id": life.pipeline.proposal.proposal_id,
            "gap_summary": life.gap_report.summary if life.gap_report else None,
            "soft_prefs": list(life.feedback.soft_preferences_written) if life.feedback else [],
            "outcome_id": life.outcome.outcome_id if life.outcome else None,
        }
    )
    print()

    # --- v0.3 HITL / Decision Log ---
    print("### v0.3 HITL gate + Decision Log")
    dlog = DecisionLog(store.decisions_path)
    hitl_proposal = sample_hitl_email_proposal()
    # 1) blocked without approval
    blocked = False
    try:
        gate_execution(hitl_proposal, human_approved=False, decision_log=dlog)
    except HitlBlockedError as err:
        blocked = True
        print(f"  blocked_without_approval: True ({err})")
    # 2) approved
    rec = gate_execution(
        hitl_proposal,
        human_approved=True,
        human_feedback="ok to send",
        decision_log=dlog,
        critic_verdict="pass",
    )
    store.save_decision(rec)
    print(
        f"  approved_decision: {rec.final_decision} override={rec.human_override} "
        f"proposal_safety={rec.proposal_safety_level} effective={rec.effective_safety_level} "
        f"trace_id={rec.trace_id}"
    )
    # 3) forced override
    rec2 = gate_execution(
        sample_hitl_email_proposal(),
        human_approved=False,
        force=True,
        human_feedback="emergency override",
        decision_log=dlog,
    )
    store.save_decision(rec2)
    print(f"  forced_override: {rec2.final_decision} override={rec2.human_override}")
    print(f"  decision_log_rows: {len(dlog.read_all())}")
    results.append(
        {
            "scenario": "hitl_gate",
            "blocked_without_approval": blocked,
            "approved": rec.final_decision,
            "forced": rec2.final_decision,
            "decision_log_count": len(dlog.read_all()),
        }
    )
    print()

    if not args.dry_run:
        ok, agent, msg = try_create_live_stack(model=args.model)
        print(f"[live] {msg}")
        if ok:
            print("[live] planner agent created; invoke left to interactive use.")
            _ = agent

    print("=== summary ===")
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    return 0


def _cmd_schedule_list(_: argparse.Namespace) -> int:
    from life_companion.scheduling.hooks import (
        evening_review_hook,
        hard_reminder_hook,
        morning_plan_hook,
    )

    events = [
        morning_plan_hook(),
        evening_review_hook(),
        hard_reminder_hook("child_pickup"),
        hard_reminder_hook("sleep_window"),
    ]
    for e in events:
        print(f"{e.kind}\tat={e.at}\tpayload={e.payload}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="life-companion", description="Life Companion CLI")
    sub = p.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="End-to-end proposal→critic→life-loop→HITL demo")
    demo.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Use rule-based critic stub (default True; no API key)",
    )
    demo.add_argument(
        "--live",
        action="store_true",
        help="Attempt live deepagents path (needs deps + API key)",
    )
    demo.add_argument("--data-dir", default="data", help="Local store directory")
    demo.add_argument("--model", default=None, help="Override LIFE_COMPANION_MODEL")
    demo.set_defaults(func=_cmd_demo)

    sched = sub.add_parser("schedule-list", help="Show stub scheduling hooks")
    sched.set_defaults(func=_cmd_schedule_list)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "command", None) == "demo" and getattr(args, "live", False):
        args.dry_run = False
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
