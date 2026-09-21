"""CLI: demo --dry-run end-to-end without API keys."""

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
        sample_preference_proposal,
        sample_read_only_proposal,
    )
    from life_companion.store.json_store import LocalStore
    from life_companion.tools import stubs as stub_tools

    data_dir = Path(args.data_dir)
    store = LocalStore(data_dir)
    tree = sample_goal_tree()
    store.save_goals(tree)

    print("=== Life Companion demo ===")
    print(f"data_dir: {store.data_dir}")
    print(f"dry_run: {args.dry_run}")
    print(f"deepagents_available: {deepagents_available()}")
    print()

    # Stub context gathers
    cal = stub_tools.calendar_list_events()
    weather = stub_tools.weather_forecast("Hangzhou")
    print("[stub] calendar events:", len(cal.get("events", [])))
    print("[stub] weather:", weather.get("summary"))
    print()

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

    if not args.dry_run:
        ok, agent, msg = try_create_live_stack(model=args.model)
        print(f"[live] {msg}")
        if ok:
            print("[live] planner agent created; invoke left to interactive use.")
            _ = agent

    print("=== summary ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))
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

    demo = sub.add_parser("demo", help="End-to-end proposal→critic pipeline demo")
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
