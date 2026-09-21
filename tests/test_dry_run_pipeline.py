"""Dry-run proposal pipeline tests (no API key)."""

from pathlib import Path

from life_companion.agents.pipeline import run_proposal_pipeline
from life_companion.demo_data import (
    sample_day_plan_proposal,
    sample_preference_proposal,
    sample_read_only_proposal,
)
from life_companion.models.proposal import Verdict
from life_companion.store.json_store import LocalStore


def test_read_only_skips_critic(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    result = run_proposal_pipeline(
        sample_read_only_proposal(), dry_run=True, store=store
    )
    assert result.critic_invoked is False
    assert result.review is None


def test_bad_day_plan_revises_then_pass(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    result = run_proposal_pipeline(
        sample_day_plan_proposal(bad=True), dry_run=True, store=store
    )
    assert result.critic_invoked is True
    assert result.revised is True
    assert result.review is not None
    assert result.review.verdict == Verdict.PASS
    assert result.status == "skipped_execute_dry"
    # Pickup overlap should be moved
    starts = [b.start for b in (result.proposal.today_plan or [])]
    assert all(not ("17:30" <= s < "18:00") for s in starts)


def test_good_day_plan_passes(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    result = run_proposal_pipeline(
        sample_day_plan_proposal(bad=False), dry_run=True, store=store
    )
    assert result.review is not None
    assert result.review.verdict == Verdict.PASS
    assert result.revised is False


def test_weak_preference_conditional_then_pass(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    result = run_proposal_pipeline(
        sample_preference_proposal(), dry_run=True, store=store
    )
    assert result.critic_invoked is True
    assert result.revised is True
    assert result.review is not None
    assert result.review.verdict == Verdict.PASS
