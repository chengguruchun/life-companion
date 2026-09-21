"""Critic trigger gate tests."""

from life_companion.agents.critic_gate import should_invoke_critic
from life_companion.demo_data import (
    sample_day_plan_proposal,
    sample_preference_proposal,
    sample_read_only_proposal,
)
from life_companion.models.proposal import Proposal, ProposalType, ToolAction


def test_skip_read_only() -> None:
    assert should_invoke_critic(sample_read_only_proposal()) is False


def test_invoke_plan_day() -> None:
    assert should_invoke_critic(sample_day_plan_proposal()) is True


def test_invoke_preference() -> None:
    assert should_invoke_critic(sample_preference_proposal()) is True


def test_user_override_skips() -> None:
    p = sample_day_plan_proposal()
    p.user_override_skip_critic = True
    assert should_invoke_critic(p) is False


def test_send_email_invokes() -> None:
    p = Proposal(
        type=ProposalType.SEND_EMAIL,
        summary="send",
        tool_actions=[
            ToolAction(tool="email_draft_send", args={}, mutating=True, requires_hitl=True)
        ],
        rationale="工作顺利",
    )
    assert should_invoke_critic(p) is True
