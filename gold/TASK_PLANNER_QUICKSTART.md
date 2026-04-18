# 🎯 Task Planner - Quick Start Guide

## What is Task Planner?

**Task Planner** is an Agent Skill that autonomously:
- Reads new files from `AI_Employee_Vault/Inbox`
- Analyzes content and creates step-by-step execution plans
- Saves plans to `AI_Employee_Vault/Needs_Action`
- Archives processed files to `Done/`
- Prevents duplicate processing (idempotent)

---

## ✅ What Just Worked

**Test Result:**
- ✅ Read test file from Inbox
- ✅ Analyzed as "analysis" task, medium priority
- ✅ Generated 4-step execution plan
- ✅ Saved plan to Needs_Action
- ✅ Moved original to Done
- ✅ Logged in processed_files.json (won't process again)

---

## 📁 File Structure

```
silver/
├── AI_Employee_Vault/
│   ├── Inbox/                    ← Drop tasks here
│   └── Needs_Action/             ← Plans appear here
├── Done/                         ← Processed originals
├── logs/
│   ├── action.log                ← Activity log
│   └── processed_files.json      ← Deduplication tracker
├── scripts/
│   └── task_planner.py           ← The skill script
└── claude/
    └── skills/
        └── task-planner/
            └── SKILL.md          ← Documentation
```

---

## 🎮 Usage

### 1. Process All Inbox Files
```bash
cd C:\Users\HP\Desktop\ai_employee\silver
python scripts/task_planner.py --run
```

### 2. Process Specific File
```bash
python scripts/task_planner.py --file "AI_Employee_Vault/Inbox/my_task.md"
```

### 3. Run Test
```bash
python scripts/task_planner.py --test
```

---

## 📝 Example Workflow

### Step 1: Create a task file

Create `AI_Employee_Vault/Inbox/my_project.md`:

```markdown
# Build Marketing Dashboard

Create a dashboard to track marketing metrics.

## Requirements
- Show website traffic
- Track social media engagement
- Display conversion rates

## Deadline
End of next week
```

### Step 2: Run task planner
```bash
python scripts/task_planner.py --run
```

### Step 3: Check results

**Generated plan in `Needs_Action/plan_YYYYMMDD_HHMMSS.md`:**
- Step-by-step execution plan
- Priority level
- Time estimates
- Success criteria

**Original file moved to `Done/my_project.md`**

**Logged in `logs/action.log`**

---

## 🔧 Integration

### Called by Vault Watcher
```python
from scripts.task_planner import TaskPlanner

planner = TaskPlanner()
result = planner.process_inbox()
```

### Called by Scheduler
```bash
# Run every 5 minutes
*/5 * * * * cd /path/to/silver && python scripts/task_planner.py --run
```

### Called by AI Employee
```python
# In ai_employee.py
from scripts.task_planner import TaskPlanner

planner = TaskPlanner()
planner.process_inbox()
```

---

## 🎯 Task Types Detected

| Type | Keywords | Example |
|------|----------|---------|
| **Research** | research, investigate | "Research competitors" |
| **Communication** | email, send, message | "Send project update email" |
| **Analysis** | analyze, study | "Analyze sales data" |
| **Creation** | create, build, make | "Create marketing plan" |
| **Social Media** | linkedin, post, publish | "Post about product launch" |

---

## 🚦 Priority Detection

| Priority | Keywords | Action |
|----------|----------|--------|
| **High** 🔴 | urgent, asap, critical | Process first |
| **Medium** 🟡 | (default) | Standard processing |
| **Low** 🟢 | when possible, someday | Process last |

---

## ⚠️ Approval Detection

Automatically detects if tasks need manager approval:

**Requires Approval:**
- Send email
- Post to LinkedIn
- Delete files
- Purchase/payment
- External API calls

**No Approval Needed:**
- Analysis tasks
- Research
- Creating drafts
- Internal documentation

---

## 🔄 Idempotency

**Same file won't be processed twice:**

1. File hash calculated (MD5)
2. Checked against `logs/processed_files.json`
3. Skipped if already processed
4. Logged after processing

**Test it:**
```bash
# First run - processes file
python scripts/task_planner.py --test

# Second run - skips (already processed)
python scripts/task_planner.py --run
```

Output: `[SKIP] File already processed`

---

## 📊 Generated Plan Format

Every plan includes:
- **Header:** Priority, type, time estimate, approval status
- **Summary:** Brief overview
- **Steps:** Numbered, with dependencies and time
- **Success Criteria:** Checkboxes for completion
- **Resources:** What's needed
- **Risks:** Potential issues and mitigation

---

## 🔍 Logs

### Action Log (`logs/action.log`)
```
[2026-04-17 10:03:46] [START] Task Planner started
[2026-04-17 10:03:46] [SCAN] Found 1 file(s) in inbox
[2026-04-17 10:03:46] [READ] Read 619 characters from test_task.md
[2026-04-17 10:03:46] [ANALYZE] Type: analysis, Priority: medium
[2026-04-17 10:03:46] [GENERATE] Created plan: plan_20260417.md
[2026-04-17 10:03:46] [ARCHIVE] Moved test_task.md to Done
[2026-04-17 10:03:46] [COMPLETE] Processing complete
```

### Processed Files Log (`logs/processed_files.json`)
```json
{
  "processed_files": [
    {
      "filename": "test_task.md",
      "hash": "7584e8c5...",
      "processed_at": "2026-04-17T10:03:46",
      "plan_created": "plan_20260417.md"
    }
  ]
}
```

---

## 🐛 Troubleshooting

### Issue: Files not processing
**Check:**
1. Files in correct folder? (`AI_Employee_Vault/Inbox/`)
2. Files have `.md` extension?
3. Already processed? (check `logs/processed_files.json`)

### Issue: Plan not appearing
**Check:**
1. Needs_Action folder exists?
2. Check logs/action.log for errors
3. Run with `--test` to verify system works

### Issue: Duplicates being processed
**Solution:**
- Delete or clear `logs/processed_files.json`
- System will reset deduplication

---

## ✅ Verify It's Working

**Quick Test:**
```bash
# 1. Run test
python scripts/task_planner.py --test

# 2. Check outputs
ls AI_Employee_Vault/Needs_Action/  # Should have plan_*.md
ls Done/                            # Should have test_task_*.md
cat logs/action.log                 # Should have processing logs

# 3. Try again (should skip)
python scripts/task_planner.py --test
# Output: [SKIP] File already processed
```

---

## 🚀 Next Steps

1. ✅ Task Planner working
2. **Integrate with Vault Watcher** - Auto-trigger when files arrive
3. **Integrate with AI Employee** - Part of work cycle
4. **Add Scheduler** - Run every 5 minutes
5. **Connect to Gmail Watcher** - Process emails as tasks

---

**Your Task Planner is ready! Drop files in Inbox and watch it work!** 🎉
