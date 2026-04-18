# 🚀 MCP Executor - Quick Start Guide

## What is MCP Executor?

**MCP Executor** is the external action execution layer with mandatory human-in-the-loop approval workflow.

**Capabilities:**
- ✅ Executes external actions (Gmail, LinkedIn)
- ✅ Enforces approval workflow (no bypass)
- ✅ Handles errors with retry logic
- ✅ Comprehensive logging
- ✅ Safe by default (mock mode)

---

## ✅ What Just Worked

**Test Workflow:**
1. ✅ Created test approval request
2. ✅ Manager approved (added DECISION: APPROVED)
3. ✅ Executor detected approval
4. ✅ Executed Gmail send action (mock mode)
5. ✅ Moved to Done as `executed_test_email_*.md`
6. ✅ Logged all actions to logs/actions.log

---

## 📁 File Structure

```
silver/
├── Needs_Approval/              ← Approval requests go here
│   └── (empty after execution)
├── Done/
│   └── executed_*.md            ← Executed actions
├── logs/
│   └── actions.log              ← All MCP activity
├── scripts/
│   └── mcp_executor.py          ← The executor script
└── claude/
    └── skills/
        └── mcp-executor/
            └── SKILL.md         ← Full documentation
```

---

## 🎮 Usage

### 1. Process All Approved Actions
```bash
cd C:\Users\HP\Desktop\ai_employee\silver
python scripts/mcp_executor.py --process-approvals
```

### 2. Execute Specific Approved Action
```bash
python scripts/mcp_executor.py --execute "Needs_Approval/email_001.md"
```

### 3. Check System Health
```bash
python scripts/mcp_executor.py --health
```

### 4. Create Test Approval
```bash
python scripts/mcp_executor.py --create-test
```

---

## 📝 Approval Workflow

### Step 1: Action Requested
AI Employee or Watcher creates approval request in `Needs_Approval/`:

```markdown
# Approval Request: Send Email

**To:** client@example.com
**Subject:** Project Update
**Body:** The project is on track...

---

## Manager Decision Required

DECISION: [PENDING]
```

### Step 2: Manager Reviews
Open the file and add decision:

**To APPROVE:**
```
DECISION: APPROVED
```

**To REJECT:**
```
DECISION: REJECTED
Reason: Wrong timing, wait until next week
```

### Step 3: MCP Executor Processes
```bash
python scripts/mcp_executor.py --process-approvals
```

**If APPROVED:**
- Executes action (sends email, posts to LinkedIn)
- Moves to `Done/executed_*.md`
- Logs success

**If REJECTED:**
- Cancels action
- Moves to `Done/rejected_*.md`
- Logs rejection

**If PENDING:**
- Skips (waits for decision)
- Logs "awaiting approval"

---

## 🔒 Safety Features

### 1. Mandatory Approval Check
✅ **Every external action requires approval**
✅ **No backdoors or bypass mechanisms**
✅ **Double-check before execution**

### 2. Mock Mode (Default)
✅ **Safe testing without real actions**
✅ **No actual emails sent**
✅ **No LinkedIn posts published**
✅ **All actions simulated**

### 3. Error Handling
✅ **Automatic retry (up to 3 times)**
✅ **Exponential backoff (1s, 2s, 4s)**
✅ **Graceful failure**
✅ **Comprehensive error logging**

---

## ⚙️ Configuration

Edit `config/mcp_executor_config.json`:

```json
{
  "retry": {
    "max_attempts": 3,
    "initial_delay": 1
  },
  "skills": {
    "gmail-send": {
      "enabled": true,
      "mock_mode": true    ← Set to false for real emails
    },
    "linkedin-post": {
      "enabled": true,
      "mock_mode": true    ← Set to false for real posts
    }
  }
}
```

---

## 🔄 Integration

### Called by AI Employee
```python
from scripts.mcp_executor import MCPExecutor

executor = MCPExecutor()
executor.process_approved_actions()
```

### Called by Scheduler
```bash
# Every 5 minutes, check for approved actions
*/5 * * * * cd /path/to/silver && python scripts/mcp_executor.py --process-approvals
```

### Called by Watcher
```python
# When approval file is modified
from scripts.mcp_executor import MCPExecutor

executor = MCPExecutor()
result = executor.execute_approved_action(approval_file)
```

---

## 📊 Supported Actions

| Action | Skill | Status | Mock Mode |
|--------|-------|--------|-----------|
| **Send Email** | gmail-send | ✅ Working | ✅ Default |
| **LinkedIn Post** | linkedin-post | ✅ Working | ✅ Default |
| Slack Message | slack-send | 🔄 Future | - |
| Twitter Post | twitter-post | 🔄 Future | - |
| Webhook Call | webhook-trigger | 🔄 Future | - |

---

## 🧪 Testing

### Full Test Workflow

```bash
# 1. Create test approval
python scripts/mcp_executor.py --create-test

# Output: Created test_email_TIMESTAMP.md

# 2. Check status (should be PENDING)
python scripts/mcp_executor.py --health

# 3. Approve the action
# Edit Needs_Approval/test_email_*.md
# Add line: DECISION: APPROVED

# 4. Execute approved action
python scripts/mcp_executor.py --process-approvals

# 5. Verify results
ls Done/                    # Should have executed_test_email_*.md
cat logs/actions.log        # Should show execution logs
```

---

## 📈 Logs

### Action Log Format (`logs/actions.log`)

```
[2026-04-17 10:17:26] [MCP_EXECUTOR] Processing: test_email_20260417.md
[2026-04-17 10:17:26] [APPROVAL_CHECK] Status: APPROVED
[2026-04-17 10:17:26] [APPROVED] Action approved by manager
[2026-04-17 10:17:26] [PARAMS] Action type: send_email
[2026-04-17 10:17:26] [ATTEMPT] Execution attempt 1/3
[2026-04-17 10:17:26] [EXECUTE] Calling gmail-send skill
[2026-04-17 10:17:26] [MOCK] Mock sending email to test@example.com
[2026-04-17 10:17:26] [SUCCESS] Action completed
```

---

## 🐛 Troubleshooting

### Issue: Actions not executing
**Check:**
1. Is approval granted? (File must contain `DECISION: APPROVED`)
2. Run health check: `python scripts/mcp_executor.py --health`
3. Check logs: `cat logs/actions.log`

### Issue: Approval not detected
**Solution:**
- Ensure exact text: `DECISION: APPROVED` (uppercase, with colon)
- No typos or extra spaces
- File saved properly (UTF-8 encoding)

### Issue: Want to use real Gmail/LinkedIn
**Solution:**
1. Edit `config/mcp_executor_config.json`
2. Set `"mock_mode": false`
3. Configure API credentials
4. Test carefully!

---

## ✅ Verify It's Working

```bash
# Quick verification
python scripts/mcp_executor.py --health

# Expected output:
# Folders: [OK]
# Skills: gmail-send [OK] (mock mode)
#         linkedin-post [OK] (mock mode)
# Pending Approvals: X files
```

---

## 🎯 Silver Tier Progress

| Component | Status | Notes |
|-----------|--------|-------|
| Reasoning Loop | ✅ | Generates plans |
| Task Planner | ✅ | Creates execution plans |
| **MCP Executor** | ✅ **DONE** | **Executes with approval** |
| Approval Workflow | ✅ | Working |
| Gmail Watcher | 🔄 Next | Monitor emails |
| LinkedIn Auto-Post | 🔄 Next | Content generation |
| Scheduler | 🔄 Next | Automated runs |

---

## 🚀 Next Steps

**MCP Executor is ready!** Now you can:

1. **Integrate with Watchers** - Auto-create approval requests
2. **Add Gmail Watcher** - Monitor incoming emails
3. **Add LinkedIn Auto-Poster** - Generate and post content
4. **Set up Scheduler** - Run every 5 minutes

---

**Your MCP Executor is production-ready with approval workflow!** 🎉

**Safety First:** Mock mode is enabled by default. Test thoroughly before enabling real actions.
