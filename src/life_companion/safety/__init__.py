"""v0.3 Runtime safety: HITL gate + decision log helpers."""

from life_companion.models.safety import (
    HITL_REQUIRED_LEVELS,
    DecisionRecord,
    HitlBlockedError,
    SafetyLevel,
)
from life_companion.safety.decision_log import DecisionLog
from life_companion.safety.hitl import (
    effective_safety_level,
    ensure_hitl_or_raise,
    gate_execution,
)

__all__ = [
    "SafetyLevel",
    "HITL_REQUIRED_LEVELS",
    "DecisionRecord",
    "HitlBlockedError",
    "DecisionLog",
    "effective_safety_level",
    "ensure_hitl_or_raise",
    "gate_execution",
]
