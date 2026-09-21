# Life Companion Agent — Design Spec (v0.1)

## Product North Star
Goal-driven long-term companion optimizing two outcomes:
1. 工作顺利 (work going smoothly)
2. 生活开心 (life happiness)

Reminders (anniversaries, school pickup, sleep, exercise) are **external cron/webhooks**, not a coequal agent mode. They are hard constraints the planner must respect.

## Goal Tree (domain model)
Four layers:
1. Vision — rarely changes ("why")
2. Long-term goals — few (2–3), deadlines + success criteria
3. Short-term goals — weekly/biweekly, must be completable
4. Today tasks — estimated duration + priority; only this layer enters calendar

Feedback loop:
- Today tasks roll up to short-term
- Short-term reviewed at deadline: continue / split / cut
- Long-term reviewed monthly
- Prefer changing today/short-term over vision

Conflict defaults:
- Hard life constraints (sleep, child pickup, important anniversaries) beat deferrable work
- Before real work deadlines, entertainment yields — but no all-nighters by default
- Success is not only completion rate; burnout / irritation counts as failure signal

## Agent architecture (LangChain Deep Agents)
- Harness: `deepagents` / `create_deep_agent`
- Main agent = **planner** (business tools)
- Critic = **equal-strength adversarial subagent** (read-only, no write/business tools)
- Model: customer-selectable (`model=`)
- Default system prompt: product baseline (Claude Code–style short principles)
- Self-evolution memory: infer prefs/habits from conversation; writable only after critic (+ optional user confirm for important prefs)
- Customer extensions: extra tools, skills, prompt overlays

### Critic protocol
- Input: structured proposal JSON + necessary context
- Output: `pass` | `conditional_pass` | `reject` + objections + suggested fixes
- On conditional_pass: planner revises **at most once**, then execute or ask user
- Critic must NOT call mutating tools
- Trigger gate (cost control):
  - Skip: weather/traffic read, calendar read, trivial Q&A
  - Invoke: goal-tree mutations, preference self-evolution writes, email send, full-day plan generation
  - User says「按这个执行」: may skip/downgrade critic; log override

### Soft priors vs hard boundaries
- Soft: time-of-day likelihoods as prompt hints only (NOT hard tool whitelists by hour — that would stop being an agent)
- Hard: irreversible actions need human approval (email send, change others' meetings, delete goals); sleep/child pickup cannot be displaced by learning tasks

## Tools (MVP stubs OK; real integrations later)
Always/core:
- Goal tree CRUD (structured store, not only chat history)
- Memory read/write (prefs/habits)
- Critic review (subagent wrapper)
- Web search (optional)

Scene-capable (stubs with clear interfaces):
- Calendar (read/write events, free slots)
- Weather
- Traffic / ETA
- Email (read; send requires interrupt/HITL)
- Wiki / knowledge base
- Meeting (pre-brief / notes hook)
- Code agent (delegate as subagent only when coding task exists)
- Food / entertainment (evening soft)
- Kids education (weekend / family branch of goal tree)

Scheduling layer (outside LLM loop):
- Cron/webhook wakes planner for morning plan, evening review, hard reminders

## Implementation requirements
Create a Python project suitable to live under:
`/Users/chunchenglu/Downloads/AIProject/life-companion`

Stack:
- Python 3.11+
- `deepagents` + LangChain/LangGraph as needed
- `uv` or `pip` + `pyproject.toml`
- Clear package layout, README in Chinese + English OK
- `.env.example` for model API keys (no real secrets)
- Demo CLI: run a sample day plan proposal → critic → revise/execute path with **mocked** calendar/weather/traffic tools
- Unit/smoke tests for goal-tree store + critic schema roundtrip
- Document how to swap model and add a custom tool

### Suggested layout
```
life-companion/
  README.md
  DESIGN.md          # copy this spec
  pyproject.toml
  .env.example
  src/life_companion/
    __init__.py
    prompts/         # default system prompt + critic prompt
    models/          # goal tree pydantic models, proposal/review schemas
    store/           # goal tree + preference memory persistence (local JSON/SQLite OK)
    tools/           # stub tools (calendar, weather, traffic, email, ...)
    agents/          # create_planner_agent, create_critic_subagent, wiring
    scheduling/      # notes + stub cron entrypoints
    cli.py           # demo entry
  tests/
```

### Proposal / review schema (minimum fields)
Proposal:
- `proposal_id`, `type` (plan_day | mutate_goals | write_preference | send_email | other)
- `summary`
- `goal_changes` (optional)
- `today_plan` (optional list of blocks with start/end/title/linked_goal_id)
- `preference_writes` (optional)
- `tool_actions` (optional intended mutations)
- `rationale` (how it serves 工作顺利 / 生活开心)

Review:
- `proposal_id`
- `verdict`: pass | conditional_pass | reject
- `objections`: list[{code, message, severity}]
- `conditions`: list[str] (for conditional_pass)
- `suggested_fixes`: list[str]

### Default system prompt principles (encode these)
1. Goal-driven companion
2. Optimize 工作顺利 and 生活开心 together
3. Use tools as needed; do not follow a rigid hourly whitelist
4. Hard constraints (sleep, child pickup, anniversaries) win over deferrable work
5. Irreversible actions require confirmation
6. Infer prefs carefully; stable habits only; invite correction
7. When unsure, ask the user
8. Critic gates high-impact changes

## Success criteria
- `uv sync` / `pip install -e ".[dev]"` works
- `python -m life_companion.cli demo` (or equivalent) runs end-to-end with mocks without needing real API keys for tool stubs; if model call needed, document how to set key and allow a `--dry-run` path that only exercises schemas + critic stub
- Prefer a dry-run that doesn't require paid API for CI
- README explains architecture matching this design
- No fabricated integrations — stubs clearly labeled

## Non-goals for v0.1
- Real Google Calendar / Gmail OAuth
- Production multi-tenant SaaS
- Rigid scene tool whitelist tables

---

## v0.2 Life Loop (implemented)

Close the loop: **Goal → Plan → Action → Outcome → Feedback → Memory** (with goal-evolution *hooks* as suggestions only).

```
Proposal ──► Critic gate ──► (simulate) Execute
     │                              │
     │                              ▼
     │                         Outcome
     │                         (expected vs actual metrics)
     │                              │
     │                              ▼
     │                         GapReport + suggestions
     │                              │
     ▼                              ▼
Goal tree / prefs ◄── soft prefs / hypotheses / goal-tweak suggestions
                      (never auto-mutate Vision)
```

### Outcome model
- `Outcome`: `proposal_id`, `expected`/`actual` `Metrics`, timestamps, notes, optional `decision_id`
- Metrics: `sleep_hours`, `work_progress` (0–1), `life_happiness` (0–1), optional `fatigue` (0–1)

### Gap analysis
- `analyze_gaps(outcome) -> GapReport` with per-metric delta + severity + messages
- Suggestions: `schedule_hint` | `soft_preference` | `hypothesis` | `goal_tweak`

### Feedback loop (conservative)
- Soft prefs written under `soft:` keys with capped confidence (not hard-locked)
- Hypotheses appended to memory (`_hypotheses`) as Observation→Hypothesis (not Confirmed)
- Goal-tree tweaks returned as `GoalTweakSuggestion` only — **Vision is never auto-mutated**
- Persisted in `data/outcomes.jsonl` + `data/gap_reports.jsonl`

### Dry-run demo
`python -m life_companion.cli demo --dry-run` runs a Life Loop scenario (late-night plan → sleep/work gaps → soft prefs + tweaks) without API keys.

---

## v0.3 Runtime Safety & Decision Trace (implemented)

### SafetyLevel
`low | medium | high | irreversible` on `Proposal` and `ToolAction`.
Heuristics bump email send / delete / cancel-others toward high/irreversible.

### HITL gate
- `ensure_hitl_or_raise` / `gate_execution` block execute for high/irreversible unless `human_approved=True`
- `force=True` allows through but sets `human_override=True` on the decision record

### Decision Log (append-only JSONL)
Fields: Decision, Context, Goals involved, Constraints, Proposal summary,
Critic objections/verdict, Final decision, Outcome id (optional), Human feedback/override,
Safety level, Notes.

Paths: `data/decisions.jsonl` (via `DecisionLog` / `LocalStore.save_decision`).

### Tests
Gate block/approve/force + decision log write/read covered in `tests/test_hitl_and_decision_log.py`.

---

## v0.4 (planned only — see ROADMAP.md)

Calendar/Gmail/Weather/Traffic adapters, multi-objective trade-off, Memory confidence pipeline
(Observation→Hypothesis→Confirmed), Personal knowledge, Family/Code Agent. **Not built in this release.**
