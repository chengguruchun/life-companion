# Life Companion（生活伙伴 Agent）v0.3

面向长期陪伴的目标驱动 Agent：**工作顺利 + 生活开心**。

> Reminders（纪念日 / 接送 / 睡眠 / 运动）由 **外部 cron/webhook** 唤醒，不是与 planner 并列的 Agent 模式。它们是 planner 必须尊重的硬约束。

完整产品决策见 [DESIGN.md](./DESIGN.md)。

## What's new in v0.2 / v0.3

| Version | Status | Highlights |
|---------|--------|------------|
| **v0.2 Life Loop** | ✅ implemented | Outcome metrics, gap analysis, soft feedback → memory, goal-tweak *suggestions* |
| **v0.3 Safety + Decision Log** | ✅ implemented | `SafetyLevel`, HITL gate for high/irreversible, append-only decision trace |
| **v0.4** | 🧭 planned | Real Calendar/Gmail/Weather/Traffic, memory confidence pipeline — see [ROADMAP.md](./ROADMAP.md) |

### Life Loop (dry-run)

```
Goal → Plan/Proposal → Critic → (simulate) Action → Outcome → Gap → Feedback → Memory
                                                                  ↘ goal-tweak suggestions
```

Metrics: `sleep_hours`, `work_progress`, `life_happiness`, optional `fatigue`.

### Decision Log / HITL

```python
from life_companion.safety import gate_execution, HitlBlockedError, DecisionLog

try:
    rec = gate_execution(proposal, human_approved=False)  # blocks if high/irreversible
except HitlBlockedError:
    rec = gate_execution(proposal, human_approved=True, human_feedback="ok")
```

