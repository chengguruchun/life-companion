"""Sample goal tree + proposals for CLI demo."""

from __future__ import annotations

from datetime import date, timedelta

from life_companion.models.goals import GoalLayer, GoalNode, GoalTree, TodayTask
from life_companion.models.proposal import (
    PreferenceWrite,
    Proposal,
    ProposalType,
    TodayPlanBlock,
    ToolAction,
)


def sample_goal_tree() -> GoalTree:
    vision = GoalNode(
        id="v1",
        layer=GoalLayer.VISION,
        title="工作顺利 + 生活开心",
        description="长期伙伴目标：职业推进与生活幸福感并行。",
    )
    lt = GoalNode(
        id="lt1",
        layer=GoalLayer.LONG_TERM,
        title="推进 Agent 基础设施影响力",
        parent_id="v1",
        deadline=date.today() + timedelta(days=180),
        success_criteria=["公开作品被引用", "稳定输出节奏"],
    )
    st = GoalNode(
        id="st1",
        layer=GoalLayer.SHORT_TERM,
        title="完成本周 Life Companion v0.1",
        parent_id="lt1",
        deadline=date.today() + timedelta(days=7),
        success_criteria=["dry-run demo 可用", "测试通过"],
    )
    today = [
        TodayTask(
            id="t1",
            title="实现 critic gate + pipeline",
            linked_goal_id="st1",
            estimated_minutes=90,
            priority=1,
        ),
        TodayTask(
            id="t2",
            title="晚间散步（生活开心）",
            linked_goal_id="v1",
            estimated_minutes=40,
            priority=2,
        ),
    ]
    return GoalTree(
        vision=[vision],
        long_term=[lt],
        short_term=[st],
        today=today,
    )


def sample_day_plan_proposal(*, bad: bool = False) -> Proposal:
    """If bad=True, intentionally overlap pickup window for critic to catch."""
    blocks = [
        TodayPlanBlock(
            start="09:00",
            end="11:00",
            title="Deep work: critic pipeline",
            linked_goal_id="st1",
        ),
        TodayPlanBlock(
            start="17:35" if bad else "18:15",
            end="18:30" if bad else "19:00",
            title="More coding" if bad else "Buffer / family time",
            linked_goal_id="st1" if bad else "v1",
        ),
        TodayPlanBlock(
            start="19:30",
            end="20:10",
            title="Evening walk",
            linked_goal_id="v1",
        ),
    ]
    return Proposal(
        type=ProposalType.PLAN_DAY,
        summary="Sample weekday plan balancing deep work and family constraints",
        today_plan=blocks,
        tool_actions=[
            ToolAction(tool="calendar_list_events", args={}, mutating=False),
            ToolAction(tool="weather_forecast", args={"city": "Hangzhou"}, mutating=False),
        ],
        rationale="上午深工作服务「工作顺利」；傍晚尊重接送硬约束并保留散步服务「生活开心」。",
    )


def sample_read_only_proposal() -> Proposal:
    return Proposal(
        type=ProposalType.OTHER,
        summary="Check weather and traffic only",
        tool_actions=[
            ToolAction(tool="weather_forecast", args={}, mutating=False),
            ToolAction(tool="traffic_eta", args={"origin": "home", "destination": "school"}, mutating=False),
        ],
        rationale="琐碎只读查询，不应触发 critic。",
    )


def sample_preference_proposal() -> Proposal:
    return Proposal(
        type=ProposalType.WRITE_PREFERENCE,
        summary="Infer evening walk preference",
        preference_writes=[
            PreferenceWrite(key="evening_walk", value=True, confidence=0.3, rationale=""),
        ],
        rationale="尝试沉淀稳定习惯；低置信度应被 critic 卡住。",
    )

def sample_hitl_email_proposal() -> Proposal:
    """High-safety email send — must be blocked without human_approved."""
    return Proposal(
        type=ProposalType.SEND_EMAIL,
        summary="Send OKR update email to boss",
        tool_actions=[
            ToolAction(
                tool="email_draft_send",
                args={"to": "boss@example.com", "subject": "OKR", "body": "..."},
                mutating=True,
                requires_hitl=True,
                safety_level=__import__(
                    "life_companion.models.safety", fromlist=["SafetyLevel"]
                ).SafetyLevel.HIGH,
            )
        ],
        safety_level=__import__(
            "life_companion.models.safety", fromlist=["SafetyLevel"]
        ).SafetyLevel.HIGH,
        rationale="工作顺利：同步进度；需 HITL。",
    )


def sample_late_night_plan_proposal() -> Proposal:
    """Day plan with late block — used to simulate sleep gap in life loop."""
    blocks = [
        TodayPlanBlock(start="09:00", end="11:00", title="Deep work", linked_goal_id="st1"),
        TodayPlanBlock(start="22:30", end="23:30", title="Late coding sprint", linked_goal_id="st1"),
    ]
    return Proposal(
        type=ProposalType.PLAN_DAY,
        summary="Aggressive late-night plan (sleep risk)",
        today_plan=blocks,
        rationale="压测 sleep gap → feedback loop。",
    )
