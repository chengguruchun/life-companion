"""Expected vs actual gap analysis + structured feedback suggestions."""

from __future__ import annotations

from life_companion.models.outcome import (
    FeedbackSuggestion,
    GapReport,
    GapSeverity,
    MetricGap,
    Metrics,
    Outcome,
)

# Thresholds for severity (absolute delta)
_THRESHOLDS: dict[str, tuple[float, float]] = {
    # metric: (medium, high)
    "sleep_hours": (0.75, 1.5),
    "work_progress": (0.15, 0.3),
    "life_happiness": (0.15, 0.3),
    "fatigue": (0.15, 0.3),
}


def _severity(metric: str, abs_delta: float) -> GapSeverity:
    med, high = _THRESHOLDS.get(metric, (0.2, 0.4))
    if abs_delta >= high:
        return GapSeverity.HIGH
    if abs_delta >= med:
        return GapSeverity.MEDIUM
    return GapSeverity.LOW


def _gap_message(metric: str, expected: float, actual: float, delta: float) -> str:
    if metric == "sleep_hours":
        if delta < 0:
            return f"Sleep shortfall: expected {expected:.1f}h, got {actual:.1f}h (Δ={delta:.1f})."
        return f"Slept more than planned: expected {expected:.1f}h, got {actual:.1f}h."
    if metric == "work_progress":
        if delta < 0:
            return f"Work progress behind: expected {expected:.0%}, actual {actual:.0%}."
        return f"Work progress ahead: expected {expected:.0%}, actual {actual:.0%}."
    if metric == "life_happiness":
        if delta < 0:
            return f"Life happiness below target: expected {expected:.2f}, actual {actual:.2f}."
        return f"Life happiness above target: expected {expected:.2f}, actual {actual:.2f}."
    if metric == "fatigue":
        # higher fatigue is worse
        if delta > 0:
            return f"Fatigue elevated: expected {expected:.2f}, actual {actual:.2f}."
        return f"Fatigue lower than expected: expected {expected:.2f}, actual {actual:.2f}."
    return f"{metric}: expected {expected}, actual {actual}, Δ={delta}."


def _suggestions_for(gap: MetricGap) -> list[FeedbackSuggestion]:
    out: list[FeedbackSuggestion] = []
    if gap.metric == "sleep_hours" and gap.delta < 0 and gap.severity in (
        GapSeverity.MEDIUM,
        GapSeverity.HIGH,
    ):
        out.append(
            FeedbackSuggestion(
                kind="schedule_hint",
                target="today",
                suggestion="Reduce evening study / deep work after 22:00 to protect sleep window.",
                confidence=0.7 if gap.severity == GapSeverity.MEDIUM else 0.85,
                evidence=[gap.message],
            )
        )
        out.append(
            FeedbackSuggestion(
                kind="soft_preference",
                target="prefer_earlier_wind_down",
                suggestion="Hypothesis: earlier wind-down improves sleep_hours.",
                confidence=0.55,
                evidence=[gap.message],
            )
        )
        out.append(
            FeedbackSuggestion(
                kind="goal_tweak",
                target="short_term",
                suggestion="Consider cutting or splitting an evening learning today-task.",
                confidence=0.6,
                evidence=[gap.message],
            )
        )
    if gap.metric == "work_progress" and gap.delta < 0 and gap.severity != GapSeverity.LOW:
        out.append(
            FeedbackSuggestion(
                kind="schedule_hint",
                target="today",
                suggestion="Protect a morning deep-work block; defer low-priority entertainment.",
                confidence=0.65,
                evidence=[gap.message],
            )
        )
        out.append(
            FeedbackSuggestion(
                kind="hypothesis",
                target="memory",
                suggestion="Hypothesis: fragmented mornings reduce work_progress.",
                confidence=0.5,
                evidence=[gap.message],
            )
        )
    if gap.metric == "life_happiness" and gap.delta < 0 and gap.severity != GapSeverity.LOW:
        out.append(
            FeedbackSuggestion(
                kind="goal_tweak",
                target="today",
                suggestion="Add or keep a short recovery activity (walk / family time).",
                confidence=0.65,
                evidence=[gap.message],
            )
        )
        out.append(
            FeedbackSuggestion(
                kind="soft_preference",
                target="protect_evening_walk",
                suggestion="Hypothesis: protecting evening walk lifts life_happiness.",
                confidence=0.55,
                evidence=[gap.message],
            )
        )
    if gap.metric == "fatigue" and gap.delta > 0 and gap.severity != GapSeverity.LOW:
        out.append(
            FeedbackSuggestion(
                kind="schedule_hint",
                target="today",
                suggestion="Insert a recovery break; avoid stacking late meetings + deep work.",
                confidence=0.6,
                evidence=[gap.message],
            )
        )
    return out


def analyze_gaps(outcome: Outcome) -> GapReport:
    """Compare expected vs actual metrics and produce GapReport + suggestions."""
    exp = outcome.expected.as_dict()
    act = outcome.actual.as_dict()
    keys = sorted(set(exp) | set(act))
    gaps: list[MetricGap] = []
    suggestions: list[FeedbackSuggestion] = []

    for key in keys:
        if key not in exp or key not in act:
            continue
        e, a = exp[key], act[key]
        delta = a - e
        # fatigue: positive delta is bad; others: negative delta is bad for severity focus
        abs_delta = abs(delta)
        if abs_delta < 1e-9:
            continue
        sev = _severity(key, abs_delta)
        # ignore tiny lows for sleep if < 0.25h
        if key == "sleep_hours" and abs_delta < 0.25:
            continue
        gap = MetricGap(
            metric=key,
            expected=e,
            actual=a,
            delta=delta,
            severity=sev,
            message=_gap_message(key, e, a, delta),
        )
        gaps.append(gap)
        suggestions.extend(_suggestions_for(gap))

    high = sum(1 for g in gaps if g.severity == GapSeverity.HIGH)
    med = sum(1 for g in gaps if g.severity == GapSeverity.MEDIUM)
    if not gaps:
        summary = "No material gaps; outcome matched expectations."
    else:
        summary = f"Found {len(gaps)} gap(s) (high={high}, medium={med})."

    return GapReport(
        outcome_id=outcome.outcome_id,
        proposal_id=outcome.proposal_id,
        gaps=gaps,
        suggestions=suggestions,
        summary=summary,
    )
