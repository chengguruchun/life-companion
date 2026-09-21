"""Conservative feedback → preference/memory writes + goal-tweak suggestions."""

from __future__ import annotations

from typing import Any, Optional

from life_companion.loop.gap import analyze_gaps
from life_companion.models.outcome import (
    FeedbackResult,
    FeedbackSuggestion,
    GapReport,
    GoalTweakSuggestion,
    Outcome,
)
from life_companion.models.proposal import PreferenceWrite
from life_companion.store.json_store import LocalStore

_SOFT_PREFIX = "soft:"
_HYPOTHESIS_KEY = "_hypotheses"


def _to_goal_tweak(s: FeedbackSuggestion) -> Optional[GoalTweakSuggestion]:
    if s.kind != "goal_tweak":
        return None
    layer = s.target if s.target in ("today", "short_term") else "today"
    action = "reduce" if ("cut" in s.suggestion.lower() or "split" in s.suggestion.lower()) else "add"
    if "reschedule" in s.suggestion.lower() or "defer" in s.suggestion.lower():
        action = "reschedule"
    return GoalTweakSuggestion(
        layer=layer,
        action=action,
        title=s.suggestion[:80],
        reason="; ".join(s.evidence) or s.suggestion,
        confidence=s.confidence,
    )


def apply_feedback_loop(
    outcome: Outcome,
    *,
    store: Optional[LocalStore] = None,
    gap_report: Optional[GapReport] = None,
    persist: bool = True,
) -> FeedbackResult:
    """Write conservative learnings; never auto-mutate vision.

    Soft prefs are prefixed with ``soft:`` and confidence is capped.
    Goal tweaks are returned as suggestions only.
    """
    store = store or LocalStore()
    report = gap_report or analyze_gaps(outcome)

    soft_writes: list[PreferenceWrite] = []
    hypotheses: list[str] = []
    tweaks: list[GoalTweakSuggestion] = []
    notes: list[str] = []

    for sug in report.suggestions:
        if sug.kind == "soft_preference":
            conf = min(float(sug.confidence), 0.6)
            key = sug.target if sug.target.startswith(_SOFT_PREFIX) else f"{_SOFT_PREFIX}{sug.target}"
            soft_writes.append(
                PreferenceWrite(
                    key=key,
                    value={"hypothesis": sug.suggestion, "from_outcome": outcome.outcome_id},
                    confidence=conf,
                    rationale=f"life-loop soft pref from outcome {outcome.outcome_id}",
                )
            )
        elif sug.kind == "hypothesis":
            hypotheses.append(sug.suggestion)
        elif sug.kind == "goal_tweak":
            tw = _to_goal_tweak(sug)
            if tw:
                tweaks.append(tw)
        elif sug.kind == "schedule_hint":
            notes.append(f"schedule_hint: {sug.suggestion}")

    applied: dict[str, Any] = {}
    if persist and soft_writes:
        applied = store.apply_preference_writes(soft_writes, require_confirm=False)
        notes.append(f"Wrote {len(applied)} soft preference(s) (not hard-locked).")

    if persist and hypotheses:
        prefs = store.load_preferences()
        bucket = prefs.get(_HYPOTHESIS_KEY, {})
        items = list(bucket.get("items", [])) if isinstance(bucket, dict) else list(bucket or [])
        for h in hypotheses:
            items.append({"text": h, "outcome_id": outcome.outcome_id, "status": "hypothesis"})
        prefs[_HYPOTHESIS_KEY] = {
            "items": items,
            "note": "Observation→Hypothesis; not Confirmed (v0.4 pipeline)",
        }
        store.save_preferences(prefs)
        notes.append(f"Appended {len(hypotheses)} hypothesis(es) to memory.")

    if tweaks:
        notes.append(f"{len(tweaks)} goal-tweak suggestion(s) (not auto-applied to vision).")

    if persist:
        store.save_outcome(outcome)
        store.save_gap_report(report)

    return FeedbackResult(
        outcome_id=outcome.outcome_id,
        soft_preferences_written=applied,
        hypotheses_appended=hypotheses,
        goal_tweak_suggestions=tweaks,
        notes=notes,
    )
