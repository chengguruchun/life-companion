"""Store + schema roundtrip tests."""

from __future__ import annotations

from pathlib import Path

from life_companion.demo_data import sample_goal_tree
from life_companion.models.proposal import (
    PreferenceWrite,
    Proposal,
    ProposalType,
    Review,
    TodayPlanBlock,
    Verdict,
)
from life_companion.store.json_store import LocalStore


def test_goal_tree_roundtrip(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    tree = sample_goal_tree()
    store.save_goals(tree)
    loaded = store.load_goals()
    assert loaded.vision[0].title == tree.vision[0].title
    assert len(loaded.today) == len(tree.today)
    assert loaded.long_term[0].id == "lt1"


def test_preference_roundtrip(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    applied = store.apply_preference_writes(
        [PreferenceWrite(key="evening_walk", value=True, confidence=0.9, rationale="habit")]
    )
    assert applied["evening_walk"] is True
    prefs = store.load_preferences()
    assert prefs["evening_walk"]["value"] is True


def test_proposal_review_schema_roundtrip() -> None:
    proposal = Proposal(
        type=ProposalType.PLAN_DAY,
        summary="x",
        today_plan=[TodayPlanBlock(start="09:00", end="10:00", title="Deep work")],
        rationale="工作顺利",
    )
    raw = proposal.model_dump_json()
    again = Proposal.model_validate_json(raw)
    assert again.proposal_id == proposal.proposal_id
    assert again.today_plan[0].title == "Deep work"

    review = Review(
        proposal_id=proposal.proposal_id,
        verdict=Verdict.PASS,
    )
    r2 = Review.model_validate_json(review.model_dump_json())
    assert r2.verdict == Verdict.PASS
