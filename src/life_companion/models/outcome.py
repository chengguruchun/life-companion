"""v0.2 Life Loop: Outcome, GapReport, feedback suggestions."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MetricName(str, Enum):
    SLEEP_HOURS = "sleep_hours"
    WORK_PROGRESS = "work_progress"  # 0–1
    LIFE_HAPPINESS = "life_happiness"  # 0–1
    FATIGUE = "fatigue"  # optional 0–1 (higher = more tired)


class Metrics(BaseModel):
    """Core life metrics. Values are absolute observations/targets."""

    sleep_hours: Optional[float] = Field(default=None, ge=0.0, le=24.0)
    work_progress: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    life_happiness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    fatigue: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    def as_dict(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for k in ("sleep_hours", "work_progress", "life_happiness", "fatigue"):
            v = getattr(self, k)
            if v is not None:
                out[k] = float(v)
        return out


class Outcome(BaseModel):
    """Recorded result of executing (or simulating) a proposal."""

    outcome_id: str = Field(default_factory=lambda: str(uuid4()))
    proposal_id: str
    trace_id: Optional[str] = None
    expected: Metrics
    actual: Metrics
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""
    decision_id: Optional[str] = None  # link to DecisionLog when present


class GapSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MetricGap(BaseModel):
    metric: str
    expected: float
    actual: float
    delta: float  # actual - expected
    severity: GapSeverity
    message: str


class FeedbackSuggestion(BaseModel):
    """Soft suggestion — never auto-mutates vision."""

    kind: str  # soft_preference | goal_tweak | schedule_hint | hypothesis
    target: str  # preference key, goal id, or "today"/"short_term"
    suggestion: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)


class GapReport(BaseModel):
    outcome_id: str
    proposal_id: str
    trace_id: Optional[str] = None
    gaps: list[MetricGap] = Field(default_factory=list)
    suggestions: list[FeedbackSuggestion] = Field(default_factory=list)
    summary: str = ""


class GoalTweakSuggestion(BaseModel):
    """Structured short-term/today tweak — not applied automatically."""

    layer: str  # today | short_term
    action: str  # add | reduce | reschedule | split
    title: str
    reason: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class FeedbackResult(BaseModel):
    """Result of writing conservative learnings into memory."""

    outcome_id: str
    trace_id: Optional[str] = None
    soft_preferences_written: dict[str, Any] = Field(default_factory=dict)
    hypotheses_appended: list[str] = Field(default_factory=list)
    goal_tweak_suggestions: list[GoalTweakSuggestion] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
