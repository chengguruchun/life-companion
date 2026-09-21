# Life Companion

**Life Companion** is a long-running personal agent that closes the loop:

**Goal → Planning → Execution → Feedback → Memory → Safety → Human**

It optimizes two outcomes together: **工作顺利** (work going smoothly) + **生活开心** (life happiness).

> Reminders (anniversaries / pickup / sleep / exercise) are woken by **external cron/webhook**, not a co-equal agent mode. They are hard constraints the planner must respect.

Design details: [DESIGN.md](./DESIGN.md) · Roadmap: [ROADMAP.md](./ROADMAP.md)

## Architecture (v0.3.x)

```
Goal → Plan/Proposal → Critic → HITL/Safety → ExecutionRecord → Observation
                                                         ↓
                                              Outcome → Gap → Feedback → Memory
                                                         ↘ goal-tweak suggestions (Human is Goal Authority)
```

| Node | Role |
|------|------|
| Goal | Vision / long / short / today — **Human is Goal Authority**; agent only suggests tweaks |
| Planning | Proposal + adversarial Critic |
| Execution | `ExecutionRecord` = what was attempted (≠ Outcome) |
| Feedback | Gap analysis → soft memory + suggestions |
| Memory | **Provisional** `soft:*` / `_hypotheses` until [v0.4 confidence](docs/v0.4-memory-confidence.md) |
| Safety | HITL uses **effective** safety = max(proposal, tool_actions) |
| Human | Approves high/irreversible; owns goals |

### Trace

One `trace_id` threads DecisionRecord → ExecutionRecord → Outcome → Feedback in a single dry-run scenario.

### Versions

| Version | Status | Highlights |
|---------|--------|------------|
| **v0.1** | ✅ | Goal tree, proposal→critic, dry-run stubs, JSON store |
| **v0.2 Life Loop** | ✅ | Outcome / Gap / Feedback → **provisional** soft memory |
| **v0.3 Safety** | ✅ | SafetyLevel, HITL, Decision Log |
| **v0.3.1 Hardening** | ✅ | Provisional markers, `trace_id`, ExecutionRecord design/stub, effective-risk clarity |
| **v0.4** | 🧭 planned (not built) | Adapters + [Memory Confidence](docs/v0.4-memory-confidence.md) |

> **Memory is provisional.** Current `soft:*` prefs and `_hypotheses` are a v0.2 legacy representation tagged `provisional` / `legacy_v02`. Do not treat them as confirmed. Migration design: [`docs/v0.4-memory-confidence.md`](docs/v0.4-memory-confidence.md).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m life_companion.cli demo --dry-run
```

### HITL / effective risk

```python
from life_companion.safety import gate_execution, HitlBlockedError, effective_safety_level

# HITL uses effective_safety_level = max(proposal.safety_level, tool_actions[*])
# — not the proposal's self-declared level alone.
try:
    rec = gate_execution(proposal, human_approved=False)
except HitlBlockedError:
    rec = gate_execution(proposal, human_approved=True, human_feedback="ok")
```

### Life Loop dry-run

Metrics: `sleep_hours`, `work_progress`, `life_happiness`, optional `fatigue`.

Demo prints `trace_id` and an `ExecutionRecord` stub when wired.

## Docs

- [DESIGN.md](./DESIGN.md) — product + architecture
- [ROADMAP.md](./ROADMAP.md) — version plan
- [docs/v0.3.1-runtime-trace.md](docs/v0.3.1-runtime-trace.md) — ExecutionRecord / Observation boundary
- [docs/v0.4-memory-confidence.md](docs/v0.4-memory-confidence.md) — **planned, not built**
