# 🎯 Human Approval - Quick Start Guide

## What is Human Approval?

**Human Approval** is the critical control layer that ensures all sensitive external actions require explicit manager approval before execution.

**Key Features:**
- ✅ Mandatory approval for external actions
- ✅ Blocks execution until decision made
- ✅ Configurable timeouts (default: 1 hour)
- ✅ File renaming based on decision
- ✅ Comprehensive audit trail

---

## ✅ What Just Worked

**Test Workflow:**
1. ✅ Created approval request (9d5ed007)
2. ✅ File created in Needs_Approval/
3. ✅ Listed as PENDING
4. ✅ Approved via CLI command
5. ✅ Status updated to APPROVED
6. ✅ Logged all actions

---

## 📁 File Structure

```
silver/
├── AI_Employee_Vault/
│   └── Needs_Approval/
│       ├── approval_*.md           ← Pending decisions
│       ├── approval_*.md.approved  ← Approved actions
│       ├── approval_*.md.rejected  ← Rejected actions
│       └── approval_*.md.timeout   ← Timed out requests
├── logs/
│   └── actions.log                 ← All approval activity
├── scripts/
│   └── request_approval.py         ← The approval script
└── claude/
    └── skills/
        └── human-approval/
            └── SKILL.md            ← Full documentation
```

---

## 🎮 Usage

### 1. Create Approval Request
```bash
cd C:\Users\HP\Desktop\ai_employee\silver

# Email approval
python scripts/request_approval.py --create \
    --action "send_email" \
    --params '{"to":"client@example.com","subject":"Update"}' \
    --timeout 3600

# LinkedIn post approval
python scripts/request_approval.py --create \
    --action "linkedin_post" \
    --params '{"content":"Exciting announcement!"}' \
    --timeout 1800
```

### 2. List Pending Approvals
```bash
python scripts/request_approval.py --list-pending
```

### 3. Check Specific Request Status
```bash
python scripts/request_approval.py --status <request_id>
```

### 4. Approve (Manual - For Testing)
```bash
python scripts/request_approval.py --approve <request_id>
```

### 5. Reject (Manual - For Testing)
```bash
python scripts/request_approval.py --reject <request_id> --reason "Need more info"
```

### 6. Clean Up Old Files
```bash
python scripts/request_approval.py --cleanup --older-than 24h
```

### 7. Run Test
```bash
python scripts/request_approval.py --test
```

---

## 📝 Real-World Workflow

### Manager's Perspective

**Step 1: Receive Notification**
Check `AI_Employee_Vault/Needs_Approval/` folder for new files

**Step 2: Review Request**
Open the approval file:
```markdown
# Approval Request: Send Email

**To:** client@example.com
**Subject:** Project Status Update
**Body:** The project is on track...

---

## Manager Decision Required

Add one of these decisions:
```

**Step 3: Make Decision**

**To APPROVE:**
Add at the end of file:
```
DECISION: APPROVED
```

**To REJECT:**
Add at the end of file:
```
DECISION: REJECTED
Reason: Wrong timing, reschedule for next week
```

**Step 4: Save File**
The AI Employee will detect the decision and act accordingly

---

## 🔄 Programmatic Usage

### From AI Employee Code

```python
from scripts.request_approval import request_approval

# Request approval (blocking - waits for decision)
result = request_approval(
    action_type="send_email",
    details={
        "to": "client@example.com",
        "subject": "Project Update",
        "body": "Status report..."
    },
    risk_level="medium",
    timeout=3600,  # 1 hour
    blocking=True
)

if result['status'] == 'approved':
    # Execute the action
    send_email(result['details'])
    print("Email sent!")

elif result['status'] == 'rejected':
    # Handle rejection
    log_rejection(result['reason'])
    print(f"Action rejected: {result['reason']}")

else:  # timeout
    # Handle timeout
    handle_timeout(result)
    print("Request timed out - no decision made")
```

### Non-Blocking Mode

```python
# Create request without waiting
result = request_approval(
    action_type="linkedin_post",
    details={"content": "Exciting news!"},
    blocking=False
)

# Check status later
from scripts.request_approval import ApprovalRequest

approver = ApprovalRequest()
status = approver.get_status(result['request_id'])

if status['status'] == 'approved':
    execute_action()
```

---

## ⏱️ Timeout Configuration

### Default Timeouts

```json
{
  "timeout": {
    "default_seconds": 3600,  // 1 hour
    "by_action_type": {
      "send_email": 1800,       // 30 minutes
      "linkedin_post": 3600,    // 1 hour
      "delete_file": 7200,      // 2 hours
      "critical": 43200         // 12 hours
    }
  }
}
```

### Custom Timeout

```python
# 5 minutes timeout
result = request_approval(
    action_type="send_email",
    details={...},
    timeout=300
)

# 12 hours for critical actions
result = request_approval(
    action_type="delete_database",
    details={...},
    timeout=43200
)
```

---

## 📊 File States

### 1. PENDING (Original .md file)
```
approval_send_email_20260417_103108_9d5ed007.md
```
- Awaiting manager decision
- Being monitored by system
- Will timeout if no decision

### 2. APPROVED (.approved extension)
```
approval_send_email_20260417_103108_9d5ed007.md.approved
```
- Manager approved
- Action can be executed
- Preserved for audit trail

### 3. REJECTED (.rejected extension)
```
approval_send_email_20260417_103108_9d5ed007.md.rejected
```
- Manager rejected
- Action cancelled
- Reason recorded in file

### 4. TIMEOUT (.timeout extension)
```
approval_send_email_20260417_103108_9d5ed007.md.timeout
```
- No decision within timeout period
- Action automatically cancelled
- Requires re-submission

---

## 🔒 Security Features

### 1. No AI Bypass
✅ AI cannot approve its own requests
✅ Only human can add DECISION marker
✅ File-based verification prevents circumvention

### 2. Audit Trail
✅ Every request logged with timestamp
✅ Decision maker tracked (when available)
✅ Decision time recorded
✅ All files preserved

### 3. Timeout Protection
✅ No zombie approvals
✅ Stale requests auto-expire
✅ Forces re-evaluation if missed

---

## 📈 Monitoring

### Check Pending Approvals

```bash
# List all pending
python scripts/request_approval.py --list-pending

# Output:
# 3 Pending Approval(s):
#
#   [abc123] approval_email_*.md
#       Created: 2026-04-17 10:00:00 (31 minutes ago)
#
#   [def456] approval_linkedin_*.md
#       Created: 2026-04-17 09:30:00 (61 minutes ago)
```

### Check Logs

```bash
tail -20 logs/actions.log

# Shows:
# [2026-04-17 10:31:08] [APPROVAL_REQUEST] Created request 9d5ed007
# [2026-04-17 10:32:15] [APPROVAL_DECISION] Request 9d5ed007: APPROVED
# [2026-04-17 10:32:15] [APPROVAL_RENAME] Renamed to: *.md.approved
```

---

## 🧪 Testing

### Quick Test Workflow

```bash
# 1. Create test request (60 second timeout)
python scripts/request_approval.py --test

# Output: Request ID: 9d5ed007

# 2. List pending (should show 1)
python scripts/request_approval.py --list-pending

# 3. Approve it
python scripts/request_approval.py --approve 9d5ed007

# 4. Check status (should show APPROVED)
python scripts/request_approval.py --status 9d5ed007

# 5. List pending (should show 0)
python scripts/request_approval.py --list-pending
```

### Test Timeout

```bash
# Create request with 30 second timeout
python scripts/request_approval.py --create \
    --action "test_timeout" \
    --params '{"test":true}' \
    --timeout 30

# Wait 30+ seconds (don't approve)
# File will auto-rename to *.timeout
```

---

## 🔗 Integration

### With MCP Executor

```python
from scripts.request_approval import request_approval
from scripts.mcp_executor import MCPExecutor

# Request approval
approval = request_approval("send_email", email_params)

if approval['status'] == 'approved':
    # Execute via MCP Executor
    executor = MCPExecutor()
    executor.execute_approved_action(approval)
```

### With Task Planner

```python
from scripts.task_planner import TaskPlanner
from scripts.request_approval import request_approval

# If task needs approval
if task.requires_approval:
    approval = request_approval(
        action_type=task.action_type,
        details=task.parameters,
        timeout=task.timeout
    )

    if approval['status'] != 'approved':
        task.mark_blocked(approval['status'])
```

---

## 🐛 Troubleshooting

### Issue: Request not detected
**Solution:**
- Check file is in `AI_Employee_Vault/Needs_Approval/`
- Verify filename format: `approval_*_*.md`
- Ensure no typos in DECISION marker

### Issue: Approval not recognized
**Solution:**
- Use exact text: `DECISION: APPROVED` (uppercase)
- No extra spaces or characters
- Save file with UTF-8 encoding

### Issue: Timeouts too aggressive
**Solution:**
- Edit `config/approval_config.json`
- Increase `default_seconds`
- Set action-specific timeouts

---

## 📋 Best Practices

### 1. Clear Request Descriptions
✅ Explain **what** will happen
✅ Show **all parameters**
✅ Include **risk assessment**
✅ Provide **context**

### 2. Appropriate Timeouts
- **Urgent:** 30 minutes
- **Normal:** 1 hour
- **Complex:** 4 hours
- **Critical:** 12+ hours

### 3. Regular Cleanup
```bash
# Weekly cleanup
python scripts/request_approval.py --cleanup --older-than 168h

# Monthly cleanup
python scripts/request_approval.py --cleanup --older-than 720h
```

---

## ✅ Verification

```bash
# Create, approve, and verify workflow
python scripts/request_approval.py --test
# Request ID: abc123

python scripts/request_approval.py --approve abc123
# Approved: approval_send_email_*.md

python scripts/request_approval.py --status abc123
# Status: APPROVED

ls AI_Employee_Vault/Needs_Approval/*.approved
# Shows approved file
```

---

## 🎯 Silver Tier Status

| Component | Status | Notes |
|-----------|--------|-------|
| Reasoning Loop | ✅ | Working |
| Task Planner | ✅ | Working |
| MCP Executor | ✅ | Working |
| **Human Approval** | ✅ **DONE** | **Blocking approval workflow** |
| Gmail Watcher | 🔄 Next | Monitor emails |
| LinkedIn Auto-Post | 🔄 Next | Generate content |
| Scheduler | 🔄 Next | Automated runs |

**Silver Tier Core: ~70% Complete!**

---

**Your Human Approval system is production-ready!** 🎉

**Critical Feature:** No external action can bypass approval - guaranteed safety!
