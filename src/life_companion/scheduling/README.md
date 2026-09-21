# Scheduling（外部唤醒，不在 LLM 循环内）

Reminders（纪念日、接送、睡眠、运动）由 **cron / webhook** 触发，不是 Agent 的并列模式。

## 建议 cron（Asia/Shanghai）

| 事件 | 示例 cron | 入口 |
|------|-----------|------|
| 晨间计划 | `30 7 * * 1-5` | `morning_plan_hook()` |
| 晚间回顾 | `0 21 * * *` | `evening_review_hook()` |
| 硬提醒 | 按事件 | `hard_reminder_hook(name)` |

macOS 可用 `launchd`；Linux 用 `crontab`；也可用任意 webhook 网关 POST 到你的服务，再调用上述 hook 并喂给 `run_proposal_pipeline`。

v0.1 仅提供 stub 与文档，不绑定具体云调度器。
