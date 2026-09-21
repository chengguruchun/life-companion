"""Proposal / critic review schemas from DESIGN.md."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from life_companion.models.safety import SafetyLevel


class ProposalType(str, Enum):
    PLAN_DAY = "plan_day"
    MUTATE_GOALS = "mutate_goals"
    WRITE_PREFERENCE = "write_preference"
    SEND_EMAIL = "send_email"
    OTHER = "other"


class Verdict(str, Enum):
    PASS = "pass"
    CONDITIONAL_PASS = "conditional_pass"
    REJECT = "reject"


class TodayPlanBlock(BaseModel):
    start: str  # HH:MM local
    end: str
    title: str
    linked_goal_id: Optional[str] = None
    notes: str = ""


class PreferenceWrite(BaseModel):
    key: str
    value: Any
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str = ""


class ToolAction(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    mutating: bool = False
    requires_hitl: bool = False
    safety_level: SafetyLevel = SafetyLevel.LOW


class Proposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    type: ProposalType
    summary: str
    goal_changes: Optional[list[dict[str, Any]]] = None
    today_plan: Optional[list[TodayPlanBlock]] = None
    preference_writes: Optional[list[PreferenceWrite]] = None
    tool_actions: Optional[list[ToolAction]] = None
    rationale: str = ""  # how it serves 工作顺利 / 生活开心
    safety_level: SafetyLevel = SafetyLevel.LOW
    user_override_skip_critic: bool = False  # 「按这个执行」


class Objection(BaseModel):
    code: str
    message: str
    severity: str = "medium"  # low | medium | high


class Review(BaseModel):
    proposal_id: str
    verdict: Verdict
    objections: list[Objection] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
