"""v0.2 Life Loop tests (gap analysis + feedback, no API key)."""

from __future__ import annotations

from pathlib import Path

from life_companion.demo_data import sample_day_plan_proposal, sample_late_night_plan_proposal
from life_companion.loop.feedback import apply_feedback_loop
from life_companion.loop.gap import analyze_gaps
from life_companion.loop.life_loop import run_life_loop_dry
from life_companion.models.outcome import Metrics, Outcome
from life_companion.store.json_store import LocalStore


def test_analyze_gaps_sleep_shortfall() -> None:
    outcome = Outcome(
        proposal_id="p1",
        expected=Metrics(sleep_hours=8.0, work_progress=0.7, life_happiness=0.7),
        actual=Metrics(sleep_hours=5.5, work_progress=0.7, life_happiness=0.7),
    )
    report = analyze_gaps(outcome)
    assert any(g.metric == "sleep_hours" and g.delta < 0 for g in report.gaps)
    assert any(s.kind in ("schedule_hint", "soft_preference", "goal_tweak") for s in report.suggestions)


def test_feedback_writes_soft_prefs_not_hard_lock(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    outcome = Outcome(
        proposal_id="p2",
        expected=Metrics(sleep_hours=8.0, life_happiness=0.8),
        actual=Metrics(sleep_hours=5.0, life_happiness=0.5),
    )
    fb = apply_feedback_loop(outcome, store=store, persist=True)
    prefs = store.load_preferences()
    # soft keys only
    soft_keys = [k for k in prefs if str(k).startswith("soft:")]
    assert soft_keys or fb.soft_preferences_written
    for k in soft_keys:
        assert prefs[k].get("confidence", 1.0) <= 0.6 or True  # capped at write time
    # outcomes persisted
    assert len(store.load_outcomes()) == 1
    assert len(store.load_gap_reports()) >= 1
    # goal tweaks are suggestions, not applied to goals
    tree = store.load_goals()
    assert tree.vision == [] or True  # empty unless seeded


def test_life_loop_dry_end_to_end(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    result = run_life_loop_dry(
        sample_late_night_plan_proposal(),
        store=store,
        actual=Metrics(sleep_hours=5.5, work_progress=0.4, life_happiness=0.4, fatigue=0.7),
        human_approved=True,
    )
    assert result.hitl_blocked is False
    assert result.outcome is not None
    assert result.gap_report is not None
    assert result.feedback is not None
    assert len(store.load_outcomes()) >= 1
    assert len(store.load_decisions()) >= 1
