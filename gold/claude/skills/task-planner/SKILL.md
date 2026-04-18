# Skill: Task Planner

## Metadata
```yaml
name: task-planner
type: agent_skill
tier: silver
status: active
version: 1.0.0
created: 2026-04-17
```

## Goal
Autonomously read new markdown files from `AI_Employee_Vault/Inbox`, analyze content, generate step-by-step execution plans, and route them for processing.

## Responsibilities

### 1. Intake Analysis
- Monitor `AI_Employee_Vault/Inbox/` for new `.md` files
- Read and parse file content
- Extract key information (goals, requirements, constraints)

### 2. Plan Generation
- Break down tasks into actionable steps
- Identify dependencies between steps
- Estimate time and complexity
- Determine priority level
- Assess if approval is needed

### 3. Plan Output
- Create detailed `plan_<timestamp>.md` file
- Place in `AI_Employee_Vault/Needs_Action/`
- Include:
  - Task summary
  - Step-by-step execution plan
  - Priority and urgency
  - Required resources
  - Success criteria

### 4. File Management
- Move processed input file to `Done/`
- Track processed files (prevent duplicates)
- Log all actions

### 5. Integration Points
- **vault-file-manager**: Move files between folders
- **vault-watcher**: Triggered by new file detection
- **scheduler**: Can run on schedule
- **logging**: All actions logged to `logs/action.log`

---

## Workflow

```
┌─────────────────────────────────────┐
│  NEW FILE in Inbox                  │
│  (detected by watcher/scheduler)    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  1. READ FILE                        │
│     - Load content                   │
│     - Check if already processed     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  2. ANALYZE CONTENT                  │
│     - Extract goals                  │
│     - Identify task type             │
│     - Assess complexity              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  3. GENERATE PLAN                    │
│     - Break into steps               │
│     - Add dependencies               │
│     - Set priority                   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  4. SAVE PLAN                        │
│     plan_YYYYMMDD_HHMMSS.md          │
│     → Needs_Action/                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  5. ARCHIVE ORIGINAL                 │
│     via vault-file-manager           │
│     → Done/                          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  6. LOG ACTION                       │
│     logs/action.log                  │
└─────────────────────────────────────┘
```

---

## Plan Template

Generated plans follow this structure:

```markdown
# Execution Plan: [Task Name]

**Generated:** YYYY-MM-DD HH:MM:SS
**Source File:** original_file.md
**Priority:** [High/Medium/Low]
**Estimated Time:** [X minutes/hours]
**Requires Approval:** [Yes/No]

---

## Summary
[Brief 2-3 sentence overview of the task]

---

## Step-by-Step Execution

### Step 1: [Action Name]
- **Description:** What needs to be done
- **Dependencies:** None or [previous step]
- **Time:** ~X minutes
- **Output:** Expected result

### Step 2: [Action Name]
- **Description:** What needs to be done
- **Dependencies:** Step 1
- **Time:** ~X minutes
- **Output:** Expected result

[... more steps ...]

---

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

---

## Resources Needed
- Resource 1
- Resource 2

---

## Risks & Mitigation
- **Risk:** Description
  - **Mitigation:** How to handle

---

**Status:** Ready for Execution
**Next Action:** [Specific next step]
```

---

## Usage

### Called by Vault Watcher
```python
from scripts.task_planner import TaskPlanner

planner = TaskPlanner()
result = planner.process_inbox()
```

### Called by Scheduler
```bash
python scripts/task_planner.py --run
```

### Manual Trigger
```bash
python scripts/task_planner.py --file "Inbox/my_task.md"
```

---

## Idempotency

**Ensures files are processed only once:**
- Maintains `logs/processed_files.json`
- Calculates file hash (MD5)
- Checks hash before processing
- Skips if already in processed log

**Duplicate Detection:**
```json
{
  "processed_files": [
    {
      "filename": "task_001.md",
      "hash": "a1b2c3d4e5f6",
      "processed_at": "2026-04-17T10:00:00Z",
      "plan_created": "plan_20260417_100000.md"
    }
  ]
}
```

---

## Integration: vault-file-manager

Uses file manager to move files:

```python
from scripts.vault_file_manager import VaultFileManager

fm = VaultFileManager()

# Move original to Done
fm.move_file(
    source="Inbox/task.md",
    destination="Done/task.md"
)

# Move plan to Needs_Action
fm.move_file(
    source="temp_plan.md",
    destination="Needs_Action/plan_20260417.md"
)
```

---

## Logging Format

All actions logged to `logs/action.log`:

```
[2026-04-17 10:00:00] [TASK_PLANNER] Started processing
[2026-04-17 10:00:01] [SCAN] Found 1 new file in Inbox
[2026-04-17 10:00:02] [READ] Reading task_001.md
[2026-04-17 10:00:03] [ANALYZE] Task type: research, Priority: medium
[2026-04-17 10:00:05] [GENERATE] Created plan with 5 steps
[2026-04-17 10:00:06] [SAVE] Saved plan_20260417_100006.md
[2026-04-17 10:00:07] [ARCHIVE] Moved task_001.md to Done
[2026-04-17 10:00:08] [COMPLETE] Processing complete
```

---

## Error Handling

### If file is unreadable:
- Log error
- Skip file
- Continue with next file

### If plan generation fails:
- Log error details
- Create fallback simple plan
- Mark for manual review

### If file move fails:
- Log error
- Keep original in Inbox
- Retry on next run

---

## Performance

**Typical Processing Time:**
- File read: <1 second
- Content analysis: 1-2 seconds
- Plan generation: 2-3 seconds
- File operations: <1 second
- **Total: ~5 seconds per file**

**Scalability:**
- Can process 10+ files per minute
- Batch processing supported
- Lightweight (minimal memory)

---

## Configuration

Edit `config/task_planner_config.json`:

```json
{
  "inbox_path": "AI_Employee_Vault/Inbox",
  "needs_action_path": "AI_Employee_Vault/Needs_Action",
  "done_path": "Done",
  "log_path": "logs/action.log",
  "processed_log": "logs/processed_files.json",
  "max_files_per_run": 10,
  "default_priority": "medium",
  "require_approval_keywords": [
    "send email",
    "post to linkedin",
    "delete",
    "purchase"
  ]
}
```

---

## Testing

### Test Command
```bash
python scripts/task_planner.py --test
```

Creates test file and processes it.

### Verify Output
1. Check `Needs_Action/` for generated plan
2. Check `Done/` for original file
3. Check `logs/action.log` for entries
4. Check `logs/processed_files.json` for record

---

## Examples

### Example Input (Inbox/research_task.md)
```markdown
# Research Task

Research our top 3 competitors and create a comparison report.

Include:
- Pricing
- Features
- Market position

Deadline: End of week
```

### Example Output (Needs_Action/plan_20260417_100000.md)
```markdown
# Execution Plan: Competitor Research

**Generated:** 2026-04-17 10:00:00
**Priority:** Medium
**Estimated Time:** 2-3 hours

## Step-by-Step Execution

### Step 1: Identify Competitors
- Research top 3 competitors
- Time: 20 minutes

### Step 2: Gather Pricing Data
- Collect pricing information
- Time: 30 minutes

### Step 3: Compare Features
- Create feature matrix
- Time: 45 minutes

### Step 4: Analyze Market Position
- Research market share
- Time: 30 minutes

### Step 5: Create Report
- Compile findings into report
- Time: 45 minutes

## Success Criteria
- [ ] 3 competitors identified
- [ ] Pricing comparison complete
- [ ] Feature matrix created
- [ ] Market analysis included
- [ ] Report delivered by deadline
```

---

## Dependencies

**Required:**
- Python 3.11+
- `vault_file_manager.py` (file operations)
- `logs/` directory (auto-created)

**Optional:**
- `vault_watcher.py` (auto-trigger)
- `scheduler.py` (scheduled runs)

---

## Maintenance

### Update Plan Template
Edit `scripts/task_planner.py` → `generate_plan()` function

### Adjust Priority Logic
Edit `scripts/task_planner.py` → `analyze_priority()` function

### Modify Approval Rules
Edit `config/task_planner_config.json` → `require_approval_keywords`

---

## Future Enhancements

### Silver → Gold Tier
- AI-powered plan optimization
- Learn from past plans
- Suggest efficiency improvements
- Parallel task identification
- Resource allocation

---

**Status:** ✅ Production Ready
**Last Updated:** 2026-04-17
**Maintained By:** AI Employee (Silver Tier)
