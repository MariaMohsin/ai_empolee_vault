# Skill: human-approval

Request human approval for sensitive actions with timeout handling.

## Usage

```bash
python .claude/skills/human-approval/scripts/request_approval.py \
  --action "Send email to client" \
  --details "Subject: Project Update\nTo: client@example.com" \
  --timeout 3600
```

## Input Parameters

- `--action`: Action description (required)
- `--details`: Action details/context (required)
- `--timeout`: Timeout in seconds (default: 3600 = 1 hour)
- `--risk`: Risk level (low/medium/high, default: medium)

## Output

Success: "Action approved by manager"
Rejected: "Action rejected: [reason]"
Timeout: "Approval timeout after 3600 seconds"

## Approval Process

1. Script creates file in `AI_Employee_Vault/Needs_Approval/`
2. Manager reviews file and adds decision:
   - Add line: `DECISION: APPROVED` to approve
   - Add line: `DECISION: REJECTED\nReason: [reason]` to reject
3. Script polls for decision every 10 seconds
4. Returns result or times out

## Example Approval File

```markdown
# Approval Request: Send email to client

**Risk Level:** MEDIUM
**Requested:** 2026-04-17 15:30:00
**Timeout:** 1 hour

## Action Details
Send email to client@example.com about project update

---
**Manager Decision Required:**
Add DECISION: APPROVED or DECISION: REJECTED below
```

## Notes

- Blocking: Script waits until approved/rejected/timeout
- File renamed after decision (.approved / .rejected / .timeout)
- Production-ready with clean audit trail
