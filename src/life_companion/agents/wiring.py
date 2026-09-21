"""Optional deepagents wiring. Degrades gracefully without deps/keys."""

from __future__ import annotations

import os
from typing import Any, Optional

from life_companion.prompts.system import CRITIC_SYSTEM_PROMPT, PLANNER_SYSTEM_PROMPT
from life_companion.tools.stubs import STUB_TOOLS


def deepagents_available() -> bool:
    try:
        import deepagents  # noqa: F401

        return True
    except ImportError:
        return False


def _tool_list():
    """Expose stub callables for agent tools."""
    return list(STUB_TOOLS.values())


def build_critic_subagent_spec(*, model: Optional[str] = None) -> dict[str, Any]:
    """Declarative SubAgent dict matching deepagents create_deep_agent subagents=.

    Critic is equal-strength (same model) but read-only: no mutating tools.
    """
    read_only = [
        STUB_TOOLS["calendar_list_events"],
        STUB_TOOLS["calendar_free_slots"],
        STUB_TOOLS["weather_forecast"],
        STUB_TOOLS["traffic_eta"],
        STUB_TOOLS["email_list"],
        STUB_TOOLS["wiki_lookup"],
        STUB_TOOLS["web_search"],
    ]
    spec: dict[str, Any] = {
        "name": "life-companion-critic",
        "description": (
            "Equal-strength adversarial critic. Reviews proposals; "
            "returns pass|conditional_pass|reject. Read-only tools only."
        ),
        "system_prompt": CRITIC_SYSTEM_PROMPT,
        "tools": read_only,
    }
    if model:
        spec["model"] = model
    return spec


def create_planner_agent(
    *,
    model: Optional[str] = None,
    with_critic_subagent: bool = True,
) -> Any:
    """Create planner via deepagents.create_deep_agent when installed.

    Raises ImportError if deepagents is not available.
    Model string is customer-selectable (e.g. openai:gpt-4o-mini).
    """
    from deepagents import create_deep_agent

    model = model or os.environ.get("LIFE_COMPANION_MODEL", "openai:gpt-4o-mini")
    subagents = [build_critic_subagent_spec(model=model)] if with_critic_subagent else None

    # Email send requires HITL interrupt when deepagents supports interrupt_on
    interrupt_on = {"email_draft_send": True, "calendar_upsert_event": True}

    try:
        agent = create_deep_agent(
            model=model,
            tools=_tool_list(),
            system_prompt=PLANNER_SYSTEM_PROMPT,
            subagents=subagents,
            interrupt_on=interrupt_on,
            name="life-companion-planner",
        )
    except TypeError:
        # Older deepagents may not accept interrupt_on / name
        agent = create_deep_agent(
            model=model,
            tools=_tool_list(),
            system_prompt=PLANNER_SYSTEM_PROMPT,
            subagents=subagents,
        )
    return agent


def try_create_live_stack(model: Optional[str] = None) -> tuple[bool, Any, str]:
    """Return (ok, agent_or_none, message)."""
    if not deepagents_available():
        return False, None, "deepagents not installed; use pip install 'life-companion[agents]'"
    # Presence of any common key is a soft check; providers vary
    keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "GOOGLE_API_KEY",
    ]
    if not any(os.environ.get(k) for k in keys):
        return (
            False,
            None,
            "No model API key in env; dry-run does not need keys. "
            "Set OPENAI_API_KEY / ANTHROPIC_API_KEY / etc. for live path.",
        )
    try:
        agent = create_planner_agent(model=model, with_critic_subagent=True)
        return True, agent, "live planner+critic wired via create_deep_agent"
    except Exception as exc:  # noqa: BLE001
        return False, None, f"create_deep_agent failed: {exc}"
