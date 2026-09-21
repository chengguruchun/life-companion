# Life Companion（生活伙伴 Agent）v0.1

面向长期陪伴的目标驱动 Agent：**工作顺利 + 生活开心**。

> Reminders（纪念日 / 接送 / 睡眠 / 运动）由 **外部 cron/webhook** 唤醒，不是与 planner 并列的 Agent 模式。它们是 planner 必须尊重的硬约束。

完整产品决策见 [DESIGN.md](./DESIGN.md)。

## 架构（对齐 DESIGN.md）

```
┌─────────────────────────────────────────────────────────┐
│  Scheduling（cron / webhook）                            │
│  morning_plan / evening_review / hard_reminder          │
└───────────────────────────┬─────────────────────────────┘
                            │ wake
                            ▼
┌─────────────────────────────────────────────────────────┐
│  Planner（main deep agent）                              │
│  tools: calendar/weather/traffic/email(HITL)/wiki/search│
│  soft time-of-day priors in prompt — NO hourly whitelist │
└───────────────────────────┬─────────────────────────────┘
                            │ Proposal JSON
                            ▼
┌─────────────────────────────────────────────────────────┐
│  Critic gate → equal-strength read-only critic subagent │
│  pass | conditional_pass | reject                       │
│  at most one revise round                               │
└─────────────────────────────────────────────────────────┘

Goal tree: Vision → Long-term → Short-term → Today tasks
Store: local JSON under data/ (gitignored)
```

### Critic 触发门控

| 跳过 | 触发 |
|------|------|
| 天气 / 路况 / 日历只读 / 琐碎问答 | 目标树变更、偏好自演化写入、发邮件、全日计划 |
| 用户说「按这个执行」（记 override 日志） | |

### 软先验 vs 硬边界

- **软**：一天中不同时段的工具/活动可能性，仅作为 prompt 提示
- **硬**：不可逆动作需人确认；睡眠 / 接孩子不可被学习任务挤占

## 安装

```bash
cd /Users/chunchenglu/Downloads/AIProject/life-companion

# 推荐
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# 或
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 可选：真实 deepagents 接线
pip install -e ".[dev,agents]"
cp .env.example .env   # 填入模型 API Key
```

## 运行 Demo（无需 API Key）

```bash
python -m life_companion.cli demo --dry-run
# 或
life-companion demo --dry-run
```

`--dry-run` 使用**确定性规则 critic stub**，CI / 本地都不需要付费 API。

尝试 live（需要 `life-companion[agents]` + API Key）：

```bash
python -m life_companion.cli demo --live
```

查看调度 stub：

```bash
python -m life_companion.cli schedule-list
```

## 测试

```bash
pytest -q
```

覆盖：store/schema 往返、critic gate、dry-run pipeline。

## 换模型 / 加工具

1. **模型**：设置环境变量 `LIFE_COMPANION_MODEL=provider:model`（如 `openai:gpt-4o-mini`、`anthropic:claude-sonnet-4-6`），并配置对应 API Key（见 `.env.example`）。
2. **自定义工具**：在 `life_companion/tools/` 增加可调用函数，并注册进 `STUB_TOOLS`；live 路径下 `create_planner_agent` 会一并传入 `create_deep_agent(tools=...)`。
3. **Critic**：默认作为 declarative subagent 规格传入 `subagents=`（只读工具集）。也可只使用 `run_proposal_pipeline` 的 dry-run / 自定义 `live_critic` callable。

## deepagents 接线说明

- **包含**：`agents/wiring.py` 在可选 extra `agents` 安装且存在 API Key 时，调用真实 `deepagents.create_deep_agent`，并把 critic 作为 `subagents` 规格挂上；`email_draft_send` / `calendar_upsert_event` 尝试 `interrupt_on` HITL。
- **默认路径**：无 deepagents / 无 Key 时，CLI `--dry-run` 与 `run_proposal_pipeline(dry_run=True)` 完全自洽，不导入 heavy 依赖。

若本地 monorepo `../deepagents` 可 editable 安装，可：

```bash
uv pip install -e "../deepagents/libs/deepagents"   # 以你仓库实际布局为准
uv pip install -e ".[dev]"
```

## 目录

```
life-companion/
  DESIGN.md
  README.md
  pyproject.toml
  .env.example
  src/life_companion/
    prompts/      # planner + critic system prompts
    models/       # goal tree + proposal/review
    store/        # JSON local store
    tools/        # clearly labeled stubs
    agents/       # gate + pipeline + optional deepagents wiring
    scheduling/   # cron/webhook stubs + notes
    cli.py
  tests/
  data/           # runtime (gitignored)
```

## 非目标（v0.1）

- 真实 Google Calendar / Gmail OAuth
- 多租户 SaaS
- 刚性「场景 × 小时」工具白名单表
