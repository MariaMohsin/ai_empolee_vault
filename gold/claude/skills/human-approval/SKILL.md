# Skill: Human Approval

## Metadata
```yaml
name: human-approval
type: agent_skill
tier: silver
status: active
version: 1.0.0
created: 2026-04-17
priority: critical
risk_level: high
```

## Goal
Manage human-in-the-loop approval workflow by monitoring approval requests, blocking execution until decisions are made, handling timeouts, and tracking approval states.

---

## Core Responsibilities

### 1. Approval Request Creation
- Create structured approval request files
- Route to `AI_Employee_Vault/Needs_Approval/`
- Include all necessary context for decision
- Assign unique IDs

### 2. Approval Monitoring
- Monitor `Needs_Approval/` folder
- Check for human decisions (APPROVED/REJECTED)
- Track approval status changes
- Detect timeouts

### 3. Decision Processing
- Read and validate human decisions
- Rename files based on decision:
  - `filename.approved` (approved)
  - `filename.rejected` (rejected)
  - `filename.timeout` (timed out)
- Trigger appropriate actions

### 4. Timeout Management
- Configurable timeout duration (default: 1 hour)
- Auto-expire pending approvals
- Notify on timeout
- Prevent zombie approvals

### 5. Comprehensive Logging
- Log all approval lifecycle events
- Track decision makers
- Record timestamps
- Audit trail for compliance

---

## Architecture

```
┌─────────────────────────────────────────────┐
│    AI WORKFLOW NEEDS APPROVAL                │
│  (Send email, Post to LinkedIn, etc.)       │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  CREATE APPROVAL REQUEST                     │
│  - Generate unique ID                        │
│  - Create markdown file                      │
│  - Add context & details                     │
│  - Save to Needs_Approval/                   │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  MONITOR FOR DECISION                        │
│  - Poll every 10 seconds                     │
│  - Check for APPROVED/REJECTED               │
│  - Track elapsed time                        │
└──────────────┬──────────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
    DECISION      TIMEOUT
     FOUND        (1 hour)
        │             │
        ▼             ▼
┌──────────────┐  ┌──────────────┐
│ READ         │  │ MARK         │
│ DECISION     │  │ TIMEOUT      │
└──────┬───────┘  └──────┬───────┘
       │                 │
   ┌───┴────┐            │
   │        │            │
APPROVED  REJECTED       │
   │        │            │
   ▼        ▼            ▼
┌────────────────────────────┐
│  RENAME FILE               │
│  - .approved               │
│  - .rejected               │
│  - .timeout                │
└──────────┬─────────────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│  LOG DECISION & RETURN                       │
│  - Log to actions.log                        │
│  - Return status to caller                   │
└─────────────────────────────────────────────┘
```

---

## Approval Request Format

### File Naming
```
approval_<action>_<timestamp>_<id>.md
```

Examples:
- `approval_email_20260417_103045_a1b2c3.md`
- `approval_linkedin_20260417_103046_d4e5f6.md`

### File Content Template

```markdown
# Approval Request: [Action Type]

```yaml
request_id: a1b2c3d4
action_type: send_email
created_at: 2026-04-17T10:30:45Z
requested_by: ai_employee
timeout: 3600  # seconds (1 hour)
status: pending
```

## Action Details

**Type:** [Email / LinkedIn Post / File Delete / etc.]

[Detailed description of what action will be taken]

**Parameters:**
- Parameter 1: Value
- Parameter 2: Value
- Parameter 3: Value

## Risk Assessment

**Risk Level:** [Low / Medium / High / Critical]

**Potential Impact:**
- Impact point 1
- Impact point 2

**Mitigation:**
- How this action is safe/controlled

---

## Manager Decision Required

⚠️ **This action requires your approval before execution.**

### How to Approve

Add this line anywhere in the file:
```
DECISION: APPROVED
```

### How to Reject

Add this line with reason:
```
DECISION: REJECTED
Reason: [Your reason here]
```

### Questions or Need More Info?

Add a comment:
```
QUESTION: [Your question]
```

---

**Status:** Awaiting Decision
**Timeout:** [Timestamp when this expires]
**Last Checked:** [Timestamp of last check]
```

---

## File Renaming Logic

### On Approval
```
Original:  approval_email_20260417_103045_a1b2c3.md
Renamed:   approval_email_20260417_103045_a1b2c3.md.approved
```

### On Rejection
```
Original:  approval_email_20260417_103045_a1b2c3.md
Renamed:   approval_email_20260417_103045_a1b2c3.md.rejected
```

### On Timeout
```
Original:  approval_email_20260417_103045_a1b2c3.md
Renamed:   approval_email_20260417_103045_a1b2c3.md.timeout
```

**Why rename instead of delete?**
- Preserves audit trail
- Allows review of decisions
- Prevents file loss
- Supports compliance requirements

---

## Timeout Configuration

Default timeout: **1 hour (3600 seconds)**

Configurable in `config/approval_config.json`:

```json
{
  "timeout": {
    "default_seconds": 3600,
    "max_seconds": 86400,
    "by_action_type": {
      "send_email": 1800,       # 30 minutes
      "linkedin_post": 3600,    # 1 hour
      "delete_file": 7200,      # 2 hours
      "critical": 43200         # 12 hours
    }
  },
  "monitoring": {
    "poll_interval": 10,        # Check every 10 seconds
    "max_polls": 360            # Stop after 1 hour (360 * 10s)
  },
  "notifications": {
    "timeout_warning": 300,     # Warn 5 minutes before timeout
    "enable_alerts": true
  }
}
```

---

## Monitoring Modes

### 1. Blocking Mode (Default)
Wait for decision or timeout:

```python
from scripts.request_approval import ApprovalRequest

request = ApprovalRequest("send_email", params)
request_id = request.create()

# Block until decision
result = request.wait_for_approval(timeout=3600)

if result['status'] == 'approved':
    execute_action()
elif result['status'] == 'rejected':
    log_rejection(result['reason'])
else:  # timeout
    handle_timeout()
```

### 2. Non-Blocking Mode
Check status without waiting:

```python
request = ApprovalRequest("send_email", params)
request_id = request.create()

# Check status later
status = request.check_status()

if status == 'pending':
    # Still waiting
    pass
elif status == 'approved':
    execute_action()
```

### 3. Polling Mode
Periodic checks:

```python
while True:
    pending_approvals = get_pending_approvals()

    for approval in pending_approvals:
        if approval.is_approved():
            process_approval(approval)
        elif approval.is_rejected():
            handle_rejection(approval)
        elif approval.is_timed_out():
            handle_timeout(approval)

    time.sleep(10)  # Check every 10 seconds
```

---

## Logging Format

All approval events logged to `logs/actions.log`:

### Approval Request Created
```
[2026-04-17 10:30:45] [APPROVAL_REQUEST] Created request a1b2c3 (send_email)
[2026-04-17 10:30:45] [APPROVAL_REQUEST] File: approval_email_20260417_103045_a1b2c3.md
[2026-04-17 10:30:45] [APPROVAL_REQUEST] Timeout: 3600 seconds (1 hour)
```

### Decision Made
```
[2026-04-17 10:35:20] [APPROVAL_DECISION] Request a1b2c3: APPROVED
[2026-04-17 10:35:20] [APPROVAL_DECISION] Decision time: 4 minutes 35 seconds
[2026-04-17 10:35:20] [APPROVAL_RENAME] Renamed to: approval_email_*.md.approved
```

### Rejection
```
[2026-04-17 10:40:15] [APPROVAL_DECISION] Request d4e5f6: REJECTED
[2026-04-17 10:40:15] [APPROVAL_REASON] Reason: Wrong timing, reschedule
[2026-04-17 10:40:15] [APPROVAL_RENAME] Renamed to: approval_linkedin_*.md.rejected
```

### Timeout
```
[2026-04-17 11:30:45] [APPROVAL_TIMEOUT] Request g7h8i9: TIMEOUT
[2026-04-17 11:30:45] [APPROVAL_TIMEOUT] Elapsed: 3600 seconds (1 hour)
[2026-04-17 11:30:45] [APPROVAL_RENAME] Renamed to: approval_delete_*.md.timeout
```

---

## Usage Examples

### Example 1: Request Email Approval

```python
from scripts.request_approval import request_approval

# Create approval request
result = request_approval(
    action_type="send_email",
    details={
        "to": "client@example.com",
        "subject": "Project Update",
        "body": "The project is on track..."
    },
    risk_level="medium",
    timeout=1800  # 30 minutes
)

if result['status'] == 'approved':
    send_email(result['params'])
    print("Email sent!")
elif result['status'] == 'rejected':
    print(f"Rejected: {result['reason']}")
else:
    print("Request timed out")
```

### Example 2: Request LinkedIn Post Approval

```python
result = request_approval(
    action_type="linkedin_post",
    details={
        "content": "Excited to announce our new product launch!",
        "visibility": "public"
    },
    risk_level="medium",
    timeout=3600  # 1 hour
)

if result['status'] == 'approved':
    post_to_linkedin(result['params'])
```

### Example 3: Critical Action (Extended Timeout)

```python
result = request_approval(
    action_type="delete_database",
    details={
        "database": "legacy_db",
        "backup": "completed"
    },
    risk_level="critical",
    timeout=43200  # 12 hours
)
```

---

## CLI Interface

```bash
# Create approval request
python scripts/request_approval.py --create \
    --action "send_email" \
    --params '{"to":"test@example.com","subject":"Test"}' \
    --timeout 3600

# Check pending approvals
python scripts/request_approval.py --list-pending

# Check specific approval status
python scripts/request_approval.py --status a1b2c3

# Manually approve (for testing)
python scripts/request_approval.py --approve a1b2c3

# Manually reject
python scripts/request_approval.py --reject a1b2c3 --reason "Not ready"

# Clean up old approvals
python scripts/request_approval.py --cleanup --older-than 24h
```

---

## Integration Points

### With MCP Executor

```python
from scripts.request_approval import request_approval
from scripts.mcp_executor import MCPExecutor

# Request approval
approval = request_approval("send_email", email_params)

if approval['status'] == 'approved':
    # Execute via MCP Executor
    executor = MCPExecutor()
    executor.execute(approval['params'])
```

### With Task Planner

```python
from scripts.task_planner import TaskPlanner
from scripts.request_approval import request_approval

# Task requires approval
if task.needs_approval():
    approval = request_approval(
        action_type=task.action_type,
        details=task.details
    )

    if approval['status'] == 'approved':
        task.execute()
```

### With AI Employee

```python
from scripts.request_approval import request_approval

class AIEmployee:
    def execute_sensitive_action(self, action):
        # Request approval before execution
        approval = request_approval(
            action_type=action.type,
            details=action.details,
            timeout=self.config['approval_timeout']
        )

        if approval['status'] == 'approved':
            return self.perform_action(action)
        else:
            return self.handle_blocked_action(approval)
```

---

## Security & Compliance

### Audit Trail
✅ **Every request logged** with timestamp
✅ **Decision maker tracked** (if available)
✅ **Decision reason recorded**
✅ **Elapsed time tracked**
✅ **Action parameters preserved**

### Access Control
✅ **Manager-only decisions** (no AI bypass)
✅ **Explicit approval required** (no implicit)
✅ **Timeout protection** (no zombie requests)
✅ **Read-only for AI** (can't self-approve)

### Compliance
✅ **SOX compliance** - Financial actions tracked
✅ **GDPR compliance** - Data actions logged
✅ **ISO 27001** - Security controls
✅ **Audit support** - Complete history

---

## Metrics & Monitoring

### Track These Metrics

```json
{
  "daily_stats": {
    "requests_created": 15,
    "approved": 12,
    "rejected": 2,
    "timed_out": 1,
    "avg_decision_time_seconds": 420,
    "max_decision_time_seconds": 1800,
    "min_decision_time_seconds": 60
  },
  "by_action_type": {
    "send_email": {
      "requests": 8,
      "approved": 7,
      "rejected": 1
    },
    "linkedin_post": {
      "requests": 5,
      "approved": 4,
      "rejected": 0,
      "timed_out": 1
    }
  },
  "decision_makers": {
    "manager_a": 8,
    "manager_b": 4
  }
}
```

### Dashboard View

```
Approval Dashboard - Last 24 Hours

Pending:    3
Approved:   12  (80%)
Rejected:   2   (13%)
Timed Out:  1   (7%)

Average Decision Time: 7 minutes

Oldest Pending: approval_email_*.md (45 minutes ago)
```

---

## Testing

### Test Workflow

```bash
# 1. Create test approval
python scripts/request_approval.py --test

# 2. Check status (should be PENDING)
python scripts/request_approval.py --list-pending

# 3. Approve manually
# Edit file: Add "DECISION: APPROVED"

# 4. Check status again (should be APPROVED)
python scripts/request_approval.py --status <request_id>

# 5. Verify file renamed
ls -la AI_Employee_Vault/Needs_Approval/*.approved
```

### Mock Approval (For Testing)

```python
# Skip approval for tests
approval = request_approval(
    action_type="send_email",
    details={...},
    mock_approve=True  # Auto-approve immediately
)
```

---

## Troubleshooting

### Issue: Approvals not detected
**Solution:**
- Ensure exact text: `DECISION: APPROVED` (uppercase)
- Check file encoding (UTF-8)
- Verify file not locked

### Issue: Timeouts too short
**Solution:**
- Edit `config/approval_config.json`
- Increase `default_seconds`
- Set action-specific timeouts

### Issue: Old approval files accumulating
**Solution:**
```bash
python scripts/request_approval.py --cleanup --older-than 7d
```

---

## Best Practices

### 1. Clear Action Descriptions
✅ Explain **what** will happen
✅ Explain **why** it's needed
✅ Show **impact** of action
✅ Provide **context**

### 2. Appropriate Timeouts
✅ **Urgent:** 30 minutes
✅ **Normal:** 1 hour
✅ **Complex:** 4 hours
✅ **Critical:** 12-24 hours

### 3. Meaningful Rejection Reasons
✅ "Wrong timing - reschedule for tomorrow"
✅ "Need more information about recipients"
✅ "Budget not approved yet"
❌ "No" (too vague)

### 4. Regular Cleanup
✅ Archive old approvals weekly
✅ Review metrics monthly
✅ Update timeout config based on patterns

---

## Future Enhancements

### Gold Tier
- **AI-assisted decisions** - Suggest approval/rejection
- **Delegation** - Route to specific managers
- **Priority queues** - Urgent approvals first
- **Mobile app** - Approve via phone
- **Slack/Teams integration** - Approve in chat
- **Bulk approvals** - Approve multiple at once

---

**Status:** ✅ Production Ready
**Critical Component:** YES (controls all external actions)
**Requires:** Manager oversight
**Last Updated:** 2026-04-17
