"""Stub cron/webhook entrypoints that wake the planner.

Reminders are hard constraints from *outside* the agent mode — not a coequal
agent personality. Wire these to system cron, LaunchAgent, or a webhook gateway.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ScheduleEvent:
    kind: str  # morning_plan | evening_review | hard_reminder
    at: str
    payload: dict[str, Any]


def morning_plan_hook(*, now: datetime | None = None) -> ScheduleEvent:
    """Cron suggestion: weekdays 07:30 Asia/Shanghai — wake planner for day plan."""
    ts = (now or datetime.now()).isoformat(timespec="minutes")
    return ScheduleEvent(
        kind="morning_plan",
        at=ts,
        payload={
            "_stub": True,
            "instruction": "Generate today_plan proposal respecting hard constraints.",
            "cron_example": "30 7 * * 1-5",
        },
    )


def evening_review_hook(*, now: datetime | None = None) -> ScheduleEvent:
    """Cron suggestion: daily 21:00 — short-term rollup / tomorrow draft."""
    ts = (now or datetime.now()).isoformat(timespec="minutes")
    return ScheduleEvent(
        kind="evening_review",
        at=ts,
        payload={
            "_stub": True,
            "instruction": "Review today tasks vs short-term; draft tomorrow.",
            "cron_example": "0 21 * * *",
        },
    )


def hard_reminder_hook(
    name: str, *, now: datetime | None = None, meta: dict[str, Any] | None = None
) -> ScheduleEvent:
    """Webhook/cron for anniversaries, pickup, sleep, exercise — hard constraints."""
    ts = (now or datetime.now()).isoformat(timespec="minutes")
    return ScheduleEvent(
        kind="hard_reminder",
        at=ts,
        payload={
            "_stub": True,
            "name": name,
            "meta": meta or {},
            "instruction": "Inject as hard constraint into planner context; do not soft-defer.",
        },
    )
