# Skill: MCP Executor

## Metadata
```yaml
name: mcp-executor
type: agent_skill
tier: silver
status: active
version: 1.0.0
created: 2026-04-17
priority: high
risk_level: high
```

## Goal
Execute external actions (emails, LinkedIn posts) with mandatory human-in-the-loop approval workflow, comprehensive logging, and robust error handling.

---

## Core Responsibilities

### 1. Request Acceptance
- Accept execution requests from AI workflows
- Triggered by:
  - Vault watchers (file, Gmail, LinkedIn)
  - Task planner
  - Scheduler
  - AI Employee orchestrator

### 2. Approval Enforcement
- **CRITICAL:** Check `/Needs_Approval` before ANY external action
- Block execution if approval not granted
- Support approval states: PENDING, APPROVED, REJECTED
- Never bypass approval for sensitive actions

### 3. External Action Execution
- **Gmail:** Send emails via gmail-send skill
- **LinkedIn:** Post content via linkedin-post skill
- **Extensible:** Support for future actions (Twitter, Slack, etc.)

### 4. Error Handling & Retry
- Graceful error handling
- Configurable retry logic (up to 3 attempts)
- Exponential backoff
- Fallback to manual intervention

### 5. Comprehensive Logging
- Log every action to `logs/actions.log`
- Include: timestamp, action type, status, details
- Track approval decisions
- Record errors and retries

---

## Architecture

```
┌─────────────────────────────────────────────┐
│         AI WORKFLOW REQUEST                  │
│  (Watcher/Scheduler/Task Planner)           │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  MCP EXECUTOR: Validate Request              │
│  - Check action type                         │
│  - Verify required parameters                │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  APPROVAL CHECK (Mandatory)                  │
│  - Is this action in Needs_Approval?         │
│  - Status: PENDING → Block                   │
│  - Status: APPROVED → Continue               │
│  - Status: REJECTED → Cancel                 │
└──────────────┬──────────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
┌──────────────┐  ┌──────────────┐
│ APPROVED     │  │ NOT APPROVED │
└──────┬───────┘  └──────┬───────┘
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ EXECUTE      │  │ LOG & EXIT   │
│ ACTION       │  │ (Waiting)    │
└──────┬───────┘  └──────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  ACTION ROUTER                               │
│  - gmail-send skill → Send Email             │
│  - linkedin-post skill → Post Content        │
│  - [future skills] → Other Actions           │
└──────────────┬──────────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
   SUCCESS         ERROR
        │             │
        ▼             ▼
┌──────────────┐  ┌──────────────┐
│ LOG SUCCESS  │  │ RETRY LOGIC  │
│ MOVE TO DONE │  │ (up to 3x)   │
└──────────────┘  └──────┬───────┘
                         │
                    ┌────┴────┐
                    │         │
               SUCCESS     FAILED
                    │         │
                    ▼         ▼
              LOG SUCCESS  LOG FAILURE
                           ESCALATE
```

---

## Approval Workflow

### Approval States

| State | Description | Action |
|-------|-------------|--------|
| **PENDING** | Awaiting manager decision | Block execution, log wait |
| **APPROVED** | Manager approved | Execute action |
| **REJECTED** | Manager rejected | Cancel, log rejection, archive |
| **NOT_REQUIRED** | Safe action, no approval needed | Execute immediately |

### Approval File Format

Files in `Needs_Approval/` must contain decision marker:

```markdown
# Approval Request: Email Send

**Action:** Send Email
**To:** client@example.com
**Subject:** Project Update

---

## Manager Decision

DECISION: APPROVED

(or)

DECISION: REJECTED
Reason: Wrong timing, wait for next week
```

### Checking Approval

```python
def check_approval(action_file):
    """
    Returns: "APPROVED", "REJECTED", or "PENDING"
    """
    content = read_file(action_file)

    if "DECISION: APPROVED" in content:
        return "APPROVED"
    elif "DECISION: REJECTED" in content:
        return "REJECTED"
    else:
        return "PENDING"
```

---

## External Action Skills

### 1. Gmail Send Skill

**Purpose:** Send emails via Gmail API

**Input:**
```json
{
  "action": "send_email",
  "to": "recipient@example.com",
  "subject": "Email Subject",
  "body": "Email content here",
  "cc": ["optional@example.com"],
  "attachments": ["path/to/file.pdf"]
}
```

**Output:**
```json
{
  "success": true,
  "message_id": "abc123xyz",
  "timestamp": "2026-04-17T10:00:00Z"
}
```

**Implementation:**
- Uses Gmail API
- OAuth2 authentication
- Supports HTML/plain text
- Attachment support
- Mock mode for testing

### 2. LinkedIn Post Skill

**Purpose:** Post content to LinkedIn

**Input:**
```json
{
  "action": "linkedin_post",
  "content": "Post content here...",
  "visibility": "public",
  "tags": ["#AI", "#Automation"]
}
```

**Output:**
```json
{
  "success": true,
  "post_id": "urn:li:post:123456",
  "url": "https://linkedin.com/posts/...",
  "timestamp": "2026-04-17T10:00:00Z"
}
```

**Implementation:**
- Uses LinkedIn API or Playwright
- Supports text posts
- Image attachments (future)
- Scheduling (future)
- Mock mode for testing

---

## Error Handling & Retry

### Retry Strategy

```python
def execute_with_retry(action, max_retries=3):
    """
    Execute action with exponential backoff retry
    """
    for attempt in range(max_retries):
        try:
            result = execute_action(action)
            return result
        except TransientError as e:
            # Retry on temporary failures
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            sleep(wait_time)
            log(f"Retry {attempt+1}/{max_retries}")
        except PermanentError as e:
            # Don't retry on permanent failures
            log(f"Permanent error: {e}")
            return {"success": False, "error": str(e)}

    # All retries exhausted
    return {"success": False, "error": "Max retries exceeded"}
```

### Error Categories

| Category | Examples | Retry? |
|----------|----------|--------|
| **Transient** | Network timeout, rate limit | Yes (3x) |
| **Permanent** | Invalid email, auth failed | No |
| **Approval** | Not yet approved | No (wait) |
| **Config** | Missing API key | No (fix config) |

### Error Response

```json
{
  "success": false,
  "error": "Network timeout",
  "error_type": "transient",
  "retries": 2,
  "next_action": "retry",
  "timestamp": "2026-04-17T10:00:00Z"
}
```

---

## Logging Format

All actions logged to `logs/actions.log`:

```
[2026-04-17 10:00:00] [MCP_EXECUTOR] Request received: send_email
[2026-04-17 10:00:01] [APPROVAL_CHECK] Checking Needs_Approval/email_123.md
[2026-04-17 10:00:02] [APPROVAL_STATUS] APPROVED by manager
[2026-04-17 10:00:03] [EXECUTE] Calling gmail-send skill
[2026-04-17 10:00:05] [SUCCESS] Email sent: message_id=abc123
[2026-04-17 10:00:06] [ARCHIVE] Moved email_123.md to Done
[2026-04-17 10:00:07] [COMPLETE] Action completed successfully
```

**Error Log Example:**
```
[2026-04-17 10:00:00] [MCP_EXECUTOR] Request received: send_email
[2026-04-17 10:00:01] [APPROVAL_CHECK] Status: PENDING
[2026-04-17 10:00:02] [BLOCKED] Execution blocked - awaiting approval
[2026-04-17 10:00:03] [WAITING] Will retry when approved
```

---

## Usage

### Called by AI Workflow

```python
from scripts.mcp_executor import MCPExecutor

executor = MCPExecutor()

# Execute approved action
result = executor.execute({
    "action_type": "send_email",
    "approval_file": "Needs_Approval/email_001.md",
    "params": {
        "to": "client@example.com",
        "subject": "Project Update",
        "body": "The project is on track..."
    }
})

if result["success"]:
    print(f"Action completed: {result['message']}")
else:
    print(f"Action failed: {result['error']}")
```

### Called by Scheduler

```bash
# Check for approved actions and execute
python scripts/mcp_executor.py --process-approvals
```

### Manual Execution

```bash
# Execute specific approved action
python scripts/mcp_executor.py --execute "Needs_Approval/email_001.md"
```

---

## Configuration

`config/mcp_executor_config.json`:

```json
{
  "approval_required_actions": [
    "send_email",
    "linkedin_post",
    "delete_file",
    "api_call"
  ],
  "retry": {
    "max_attempts": 3,
    "backoff_strategy": "exponential",
    "initial_delay": 1
  },
  "skills": {
    "gmail-send": {
      "enabled": true,
      "mock_mode": false,
      "timeout": 30
    },
    "linkedin-post": {
      "enabled": true,
      "mock_mode": false,
      "timeout": 60
    }
  },
  "logging": {
    "level": "INFO",
    "file": "logs/actions.log",
    "max_size_mb": 10,
    "backup_count": 5
  }
}
```

---

## Safety Features

### 1. Approval Enforcement
✅ **Mandatory approval check** before external actions
✅ **Double-check mechanism** (verify twice)
✅ **Audit trail** of all approval decisions

### 2. Action Validation
✅ **Parameter validation** before execution
✅ **Dry-run mode** for testing
✅ **Rate limiting** to prevent abuse

### 3. Error Recovery
✅ **Automatic retry** for transient errors
✅ **Graceful degradation** on failure
✅ **Manual fallback** when automation fails

### 4. Logging & Monitoring
✅ **Comprehensive logging** of all actions
✅ **Success/failure metrics**
✅ **Alert on repeated failures**

---

## Testing

### Test Workflow

```bash
# 1. Create test approval file
python scripts/mcp_executor.py --create-test-approval

# 2. Check approval status (should be PENDING)
python scripts/mcp_executor.py --check-approval "Needs_Approval/test_email.md"

# 3. Approve the test action
# Edit file and add: DECISION: APPROVED

# 4. Execute approved action
python scripts/mcp_executor.py --execute "Needs_Approval/test_email.md"

# 5. Verify in logs
cat logs/actions.log
```

### Mock Mode

For testing without real external calls:

```python
executor = MCPExecutor(mock_mode=True)
result = executor.execute(action)
# Returns success without actually sending email/post
```

---

## Integration Points

### With Task Planner
```python
# Task planner creates approval requests
from scripts.mcp_executor import MCPExecutor

executor = MCPExecutor()
executor.create_approval_request(
    action_type="send_email",
    params={...},
    destination="Needs_Approval/"
)
```

### With Vault Watcher
```python
# Watcher detects approved items
from scripts.mcp_executor import MCPExecutor

executor = MCPExecutor()
executor.process_approved_actions()
```

### With Scheduler
```python
# Scheduled execution of approved actions
# Every 5 minutes, check for approved items
executor = MCPExecutor()
executor.scan_and_execute()
```

---

## Metrics & Monitoring

### Track These Metrics

```json
{
  "daily_stats": {
    "actions_requested": 24,
    "awaiting_approval": 3,
    "approved": 18,
    "rejected": 2,
    "executed_successfully": 15,
    "failed": 1,
    "retries": 4
  },
  "by_action_type": {
    "send_email": 12,
    "linkedin_post": 6
  }
}
```

### Health Checks

```bash
# Check MCP Executor health
python scripts/mcp_executor.py --health

# Output:
# ✅ Gmail skill: OK
# ✅ LinkedIn skill: OK
# ⚠️  3 actions awaiting approval
# ✅ 15 actions executed today
# ❌ 1 failed action (needs attention)
```

---

## Security Considerations

### 1. Credential Management
- Store API keys in environment variables
- Use OAuth2 for Gmail/LinkedIn
- Never log sensitive data
- Rotate credentials regularly

### 2. Approval Bypass Prevention
- **No backdoors** - approval is mandatory
- **Audit trail** - log all approval checks
- **Manager visibility** - clear approval UI

### 3. Rate Limiting
- Max 10 emails per hour
- Max 5 LinkedIn posts per day
- Configurable limits
- Alert on threshold breach

---

## Future Enhancements

### Gold Tier
- **AI-powered approval** - Auto-approve low-risk actions
- **Batch execution** - Process multiple actions
- **Priority queues** - Urgent actions first
- **Advanced retry** - Smart retry logic
- **More integrations** - Slack, Twitter, webhooks

---

## Troubleshooting

### Issue: Actions not executing
**Check:**
1. Is approval granted? (Check file for DECISION: APPROVED)
2. Are credentials configured?
3. Check logs/actions.log for errors

### Issue: Approval not detected
**Solution:**
- Ensure exact text: `DECISION: APPROVED`
- Check file encoding (UTF-8)
- Verify file in Needs_Approval/ folder

### Issue: Retries exhausted
**Solution:**
- Check error logs for root cause
- Fix underlying issue (network, auth, etc.)
- Reset retry count and try again

---

## Dependencies

**Required:**
- Python 3.11+
- `gmail-send` skill (for Gmail)
- `linkedin-post` skill (for LinkedIn)
- `logs/` directory

**Optional:**
- Google API credentials (for real Gmail)
- LinkedIn API access (for real posts)
- Playwright (for browser automation)

---

**Status:** ✅ Production Ready (with approval workflow)
**Risk Level:** HIGH (external actions)
**Requires:** Manager oversight and approval
**Last Updated:** 2026-04-17
