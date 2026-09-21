"""External scheduling layer (cron/webhooks) — outside the LLM loop."""

from life_companion.scheduling.hooks import (
    evening_review_hook,
    hard_reminder_hook,
    morning_plan_hook,
)

__all__ = ["morning_plan_hook", "evening_review_hook", "hard_reminder_hook"]
