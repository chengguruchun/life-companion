"""Conservative feedback → preference/memory writes + goal-tweak suggestions.

v0.2 provisional / legacy memory representation
----------------------------------------------
``soft:*`` preference keys and the ``_hypotheses`` bucket are a **v0.2 provisional
/ legacy** memory representation. They are intentionally low-confidence and must
not be treated as confirmed beliefs.

v0.4 will migrate this store to MemoryEntry / Evidence
(see ``docs/v0.4-memory-confidence.md``). Until then every soft write is tagged
``provisional=True`` / ``legacy_v02=True``.
"""

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

# v0.2 provisional / legacy representation (migrate in v0.4 → MemoryEntry/Evidence)
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

    Soft prefs are prefixed with ``soft:`` (v0.2 provisional / legacy) and
    confidence is capped. Goal tweaks are returned as suggestions only.
    Propagates ``trace_id`` when present on the outcome.
    """
    store = store or LocalStore()
    report = gap_report or analyze_gaps(outcome)
    if getattr(outcome, "trace_id", None) and not getattr(report, "trace_id", None):
        report = report.model_copy(update={"trace_id": outcome.trace_id})

    soft_writes: list[PreferenceWrite] = []
    hypotheses: list[str] = []
    tweaks: list[GoalTweakSuggestion] = []
    notes: list[str] = []

    for sug in report.suggestions:
        if sug.kind == "soft_preference":
            conf = min(float(sug.confidence), 0.6)
            key = sug.target if sug.target.startswith(_SOFT_PREFIX) else f"{_SOFT_PREFIX}{sug.target}"
            # v0.2 provisional / legacy payload — v0.4 migrates to MemoryEntry
            soft_writes.append(
                PreferenceWrite(
                    key=key,
                    value={
                        "hypothesis": sug.suggestion,
                        "from_outcome": outcome.outcome_id,
                        "provisional": True,
                        "legacy_v02": True,
                    },
                    confidence=conf,
                    rationale=f"life-loop soft pref from outcome {outcome.outcome_id} (v0.2 provisional)",
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
        # Ensure top-level provisional markers on stored soft entries
        prefs = store.load_preferences()
        for k in list(applied.keys()):
            entry = prefs.get(k)
            if isinstance(entry, dict):
                entry["provisional"] = True
                entry["legacy_v02"] = True
                prefs[k] = entry
        store.save_preferences(prefs)
        notes.append(
            f"Wrote {len(applied)} soft preference(s) (v0.2 provisional / legacy; not hard-locked)."
        )

    if persist and hypotheses:
        prefs = store.load_preferences()
        bucket = prefs.get(_HYPOTHESIS_KEY, {})
        items = list(bucket.get("items", [])) if isinstance(bucket, dict) else list(bucket or [])
        for h in hypotheses:
            items.append(
                {
                    "text": h,
                    "outcome_id": outcome.outcome_id,
                    "status": "hypothesis",
                    "provisional": True,
                    "legacy_v02": True,
                    "trace_id": getattr(outcome, "trace_id", None),
                }
            )
        prefs[_HYPOTHESIS_KEY] = {
            "items": items,
            "note": (
                "v0.2 provisional / legacy hypothesis bucket. "
                "Observation→Hypothesis; not Confirmed. "
                "v0.4 migrates to MemoryEntry/Evidence (docs/v0.4-memory-confidence.md)."
            ),
            "provisional": True,
            "legacy_v02": True,
        }
        store.save_preferences(prefs)
        notes.append(f"Appended {len(hypotheses)} provisional hypothesis(es) to legacy memory.")

    if tweaks:
        notes.append(f"{len(tweaks)} goal-tweak suggestion(s) (not auto-applied to vision).")

    if persist:
        store.save_outcome(outcome)
        store.save_gap_report(report)

    return FeedbackResult(
        outcome_id=outcome.outcome_id,
        trace_id=getattr(outcome, "trace_id", None),
        soft_preferences_written=applied,
        hypotheses_appended=hypotheses,
        goal_tweak_suggestions=tweaks,
        notes=notes,
    )
