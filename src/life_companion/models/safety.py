"""v0.3 Runtime safety levels + decision log schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SafetyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    IRREVERSIBLE = "irreversible"


# Actions at or above this level require human_approved=True before execute.
HITL_REQUIRED_LEVELS = {SafetyLevel.HIGH, SafetyLevel.IRREVERSIBLE}


class DecisionRecord(BaseModel):
    """Append-only decision trace row.

    HITL / gating always uses *effective_safety_level* (max of proposal
    self-declared level and tool_actions), not proposal.safety_level alone.
    ``safety_level`` is kept as an alias of effective for backward compatibility.
    """

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: Optional[str] = None
    decision: str  # e.g. execute | ask_user | rejected | blocked_hitl | forced_override
    context: dict[str, Any] = Field(default_factory=dict)
    goals_involved: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    proposal_summary: str = ""
    proposal_id: Optional[str] = None
    critic_objections: list[dict[str, Any]] = Field(default_factory=list)
    critic_verdict: Optional[str] = None
    final_decision: str = ""
    outcome_id: Optional[str] = None
    human_feedback: Optional[str] = None
    human_override: bool = False
    # Declared on the proposal (self-assessment).
    proposal_safety_level: Optional[SafetyLevel] = None
    # Max(proposal, tool_actions) — what HITL actually uses.
    effective_safety_level: Optional[SafetyLevel] = None
    # Backward-compatible alias of effective_safety_level.
    safety_level: SafetyLevel = SafetyLevel.LOW
    notes: list[str] = Field(default_factory=list)


class HitlBlockedError(Exception):
    """Raised when execute is blocked pending human approval."""

    def __init__(self, message: str, *, safety_level: SafetyLevel, proposal_id: str) -> None:
        super().__init__(message)
        self.safety_level = safety_level
        self.proposal_id = proposal_id
