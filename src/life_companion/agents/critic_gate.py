"""Trigger gate for critic invocation (cost control)."""

from __future__ import annotations

from life_companion.models.proposal import Proposal, ProposalType

# Types that always need critic (unless user override)
_ALWAYS_CRITIC = {
    ProposalType.PLAN_DAY,
    ProposalType.MUTATE_GOALS,
    ProposalType.WRITE_PREFERENCE,
    ProposalType.SEND_EMAIL,
}

# Tool names that are read-only / trivial — skip critic when proposal is OTHER
# and only touches these.
_READ_ONLY_TOOLS = {
    "calendar_list_events",
    "calendar_free_slots",
    "weather_forecast",
    "traffic_eta",
    "email_list",
    "wiki_lookup",
    "web_search",
}


def should_invoke_critic(proposal: Proposal) -> bool:
    """Return True if critic should run for this proposal.

    Skip: weather/traffic/calendar read, trivial Q&A.
    Invoke: goal-tree mutations, preference writes, email send, full-day plan.
    User says「按这个执行」(user_override_skip_critic): skip/downgrade; caller logs.
    """
    if proposal.user_override_skip_critic:
        return False

    if proposal.type in _ALWAYS_CRITIC:
        return True

    actions = proposal.tool_actions or []
    if not actions and proposal.type == ProposalType.OTHER:
        # Trivial Q&A / no mutations
        return False

    if actions and all(
        (not a.mutating) and a.tool in _READ_ONLY_TOOLS for a in actions
    ):
        return False

    # Any mutating tool or unknown action → invoke
    if any(a.mutating or a.requires_hitl for a in actions):
        return True

    if proposal.goal_changes or proposal.preference_writes or proposal.today_plan:
        return True

    return False
