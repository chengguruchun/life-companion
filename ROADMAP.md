# Life Companion Roadmap

| Version | Status | Summary |
|---------|--------|---------|
| v0.1 | ✅ shipped | Goal tree, proposal→critic pipeline, dry-run stubs, local JSON store |
| v0.2 | ✅ shipped | Life Loop: Outcome / Gap / Feedback / soft Memory |
| v0.3 | ✅ shipped | SafetyLevel, HITL gate, Decision Log |
| **v0.4** | 🧭 **planned (not built)** | Integrations + multi-objective + memory confidence |

---

## v0.4 — Planned only (do not implement in this branch)

Explicitly **out of scope for the current tree**. Design notes only:

### 1. External adapters (stubs → real)
- **Calendar** (Google Calendar / Apple) — free slots, write events (HITL for invites that affect others)
- **Gmail** — read triage; send always HITL / irreversible
- **Weather** — commute & outdoor plan priors
- **Traffic** — ETA for pickup / commute hard constraints

> Do **not** invent OAuth flows in docs as if shipped. When built: env-based credentials, no secrets in repo.

### 2. Multi-objective trade-off
- Explicit Pareto / weighted trade-off between 工作顺利 and 生活开心
- Surface conflicts to the user when sleep vs deadline collide
- Critic reviews trade-off rationale, not only hard constraints

### 3. Memory confidence pipeline
```
Observation → Hypothesis → Confirmed
```
- Soft prefs / hypotheses from v0.2 stay provisional until repeated evidence or user confirm
- Confirmed prefs may raise confidence; never silently hard-lock from a single outcome
- Evidence pointers stored alongside memory entries

### 4. Personal knowledge
- Lightweight personal wiki / notes retrieval for planning context
- Clear boundary vs chat history (structured store)

### 5. Family / Code Agent delegation
- Family branch of the goal tree (kids education, weekends)
- Code agent as **subagent only** when a coding task exists (no always-on)

### Non-goals still
- Multi-tenant SaaS
- Rigid hourly tool whitelist tables
- Auto-mutating Vision from a single bad night's sleep
