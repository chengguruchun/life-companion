"""v0.3.1 light ExecutionRecord / Observation schemas (design boundary).

Pipeline boundary:
  Proposal → ExecutionRecord → Observation → Outcome → Gap → Feedback → Memory

Outcome is NOT equal to Action result. ExecutionRecord captures what was actually
attempted (tools, changes, errors). Observation is a thin note of what was seen
after execution (folded here as optional fields on ExecutionRecord for minimalism).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    DRY_RUN = "dry_run"


class ExecutionRecord(BaseModel):
    """What was actually attempted — not the semantic Outcome."""

    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    proposal_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.PLANNED
    tool_actions: list[dict[str, Any]] = Field(default_factory=list)
    actual_changes: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    # Thin Observation fold-in (keep minimal — full Observation type deferred)
    observation_notes: str = ""
    observed_signals: dict[str, Any] = Field(default_factory=dict)


class Observation(BaseModel):
    """Optional thin observation; dry-run may fold into ExecutionRecord instead."""

    observation_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str = ""
    execution_id: Optional[str] = None
    proposal_id: Optional[str] = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""
    signals: dict[str, Any] = Field(default_factory=dict)
