"""Goal tree domain models (Vision → Long-term → Short-term → Today)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class GoalLayer(str, Enum):
    VISION = "vision"
    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"
    TODAY = "today"


class GoalNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    layer: GoalLayer
    title: str
    description: str = ""
    parent_id: Optional[str] = None
    deadline: Optional[date] = None
    success_criteria: list[str] = Field(default_factory=list)
    status: str = "active"  # active | done | cut | paused
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TodayTask(BaseModel):
    """Only this layer enters the calendar."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    linked_goal_id: Optional[str] = None
    estimated_minutes: int = 30
    priority: int = Field(default=3, ge=1, le=5)  # 1=highest
    status: str = "todo"  # todo | doing | done | deferred
    notes: str = ""


class GoalTree(BaseModel):
    vision: list[GoalNode] = Field(default_factory=list)
    long_term: list[GoalNode] = Field(default_factory=list)
    short_term: list[GoalNode] = Field(default_factory=list)
    today: list[TodayTask] = Field(default_factory=list)
    hard_constraints: list[str] = Field(
        default_factory=lambda: [
            "sleep_window",
            "child_pickup",
            "important_anniversaries",
        ]
    )

    def all_nodes(self) -> list[GoalNode]:
        return [*self.vision, *self.long_term, *self.short_term]
