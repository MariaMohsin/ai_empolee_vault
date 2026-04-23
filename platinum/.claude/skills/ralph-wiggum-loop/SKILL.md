# Skill: ralph-wiggum-loop

Autonomous multi-step task execution loop.
Picks up tasks from `Needs_Action/`, plans them, executes step by step,
checks each result, handles failures, and moves completed tasks to `Done/`.

> "I'm helping!" — Ralph Wiggum

---

## Usage

### Process all tasks in Needs_Action/
```bash
python .claude/skills/ralph-wiggum-loop/scripts/ralph_loop.py
```

### Process a specific task file
```bash
python .claude/skills/ralph-wiggum-loop/scripts/ralph_loop.py \
  --file "AI_Employee_Vault/Needs_Action/my_task.md"
```

### Process the next single task (used by scheduler)
```bash
python .claude/skills/ralph-wiggum-loop/scripts/ralph_loop.py --once
```

### Show current loop state
```bash
python .claude/skills/ralph-wiggum-loop/scripts/ralph_loop.py --status
```

---

## Loop Behaviour

```
Needs_Action/task.md
        │
  ┌─────▼──────────────────────────────────────┐
  │          RALPH WIGGUM LOOP                  │
  │                                             │
  │  [Step 1] Read & analyse task               │
  │           ↓                                 │
  │  [Step 2] Risky? → Request human approval   │
  │           Safe?  → Continue automatically   │
  │           ↓                                 │
  │  [Step 3] Execute action skill              │
  │           Fail?  → error-recovery skill     │
  │           ↓                                 │
  │  [Step 4] Verify result                     │
  │           ↓                                 │
  │  [Step 5] Move task to Done/                │
  └─────────────────────────────────────────────┘
        │
      Done/ or Errors/
```

---

## Safety Limits

| Safety Feature | Behaviour |
|---|---|
| **Max 5 iterations** | Loop stops if steps exceed 5 — status: `MAX_ITERATIONS` |
| **Risky keyword detection** | Triggers human-approval skill before execution |
| **Error recovery** | Failed Step 3 → calls `error-recovery` skill automatically |
| **Never deletes files** | Failed tasks moved to `Errors/`, completed to `Done/` |

### Risky keywords (trigger approval)
`send email`, `post to linkedin`, `publish`, `delete`, `payment`,
`purchase`, `transfer`, `tweet`, `facebook`, `instagram`

---

## Action Detection

The loop auto-detects what skill to call based on task content:

| Keyword in task | Skill called |
|---|---|
| "send email" / "gmail" | `gmail-send` |
| "linkedin" / "post" | `linkedin-post` |
| "income" / "expense" / "accounting" | `accounting-manager` |
| "ceo" / "briefing" / "report" | `ceo-briefing` |
| anything else | `general` (re-queues to Needs_Action) |

---

## Output Files

| File | Content |
|---|---|
| `AI_Employee_Vault/Plans/Plan_<task>_<id>.md` | Step-by-step execution plan with checkboxes |
| `AI_Employee_Vault/Done/<task>.md` | Completed task |
| `Logs/ralph_loop.log` | Timestamped loop activity log |
| `Logs/ralph_loop_state.json` | Persistent state (iteration count, step, status) |

### Plan.md format
```markdown
# Execution Plan
**Task:** my_task.md
**Loop ID:** abc12345-...
**Action Type:** send_email
**Risky:** YES - approval required
**Max Iterations:** 5

## Steps
- [x] Step 1: Read and analyse task
- [x] Step 2: Request human approval
- [x] Step 3: Execute action — send_email
- [ ] Step 4: Verify result
- [ ] Step 5: Move task to Done/

## Iteration Log
| # | Timestamp | Step | Result |
|---|-----------|------|--------|
| 1 | 2026-04-18 17:00 | Step 1 | Task read and analysed OK |
```

---

## Status Values

| Status | Meaning |
|---|---|
| `IN_PROGRESS` | Loop running |
| `DONE` | All 5 steps completed — task in Done/ |
| `PENDING_APPROVAL` | Waiting for human approval in Needs_Approval/ |
| `RETRY` | Step 3 failed — error-recovery triggered |
| `FAILED` | Approval denied or unrecoverable error |
| `MAX_ITERATIONS` | Reached 5-iteration safety limit |

---

## Scheduler Integration

The loop is called automatically by `scripts/run_ai_employee.py` at each cycle.
No manual action required — just drop a `.md` file in `AI_Employee_Vault/Needs_Action/`.

To run manually on a schedule:
```bash
python scripts/run_ai_employee.py --daemon
```
