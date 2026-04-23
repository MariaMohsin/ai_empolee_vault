# Skill: error-recovery

Handle failed tasks: log the error, quarantine the file, retry once after 5 minutes.

---

## Usage

### Handle a failed task (full recovery flow)
```bash
python .claude/skills/error-recovery/scripts/error_recovery.py \
  --file "AI_Employee_Vault/Needs_Approval/task.md" \
  --action send_email \
  --error "SMTP connection timeout"
```

### List all recorded errors
```bash
python .claude/skills/error-recovery/scripts/error_recovery.py --list-errors
```

### Retry all pending tasks immediately (manual override)
```bash
python .claude/skills/error-recovery/scripts/error_recovery.py --retry-all
```

### Show error statistics
```bash
python .claude/skills/error-recovery/scripts/error_recovery.py --stats
```

### Custom retry delay (for testing)
```bash
python .claude/skills/error-recovery/scripts/error_recovery.py \
  --file task.md --action send_email --error "timeout" --delay 10
```

---

## Input Parameters

| Flag | Required | Description |
|------|----------|-------------|
| `--file` | Yes* | Path to the failed task file |
| `--action` | Yes* | Action type: `send_email`, `linkedin_post`, `log_activity`, etc. |
| `--error` | Yes* | Error message from the failure |
| `--delay` | No | Retry delay in seconds (default: 300 = 5 min) |
| `--list-errors` | — | Show all error records |
| `--retry-all` | — | Re-run all PENDING_RETRY tasks |
| `--stats` | — | Summary counts |

*Required together for the recovery flow.

---

## Recovery Flow

```
Task fails in mcp_executor or any skill
        │
        ▼
[1] Log to Logs/error.log
        │
        ▼
[2] Move file → AI_Employee_Vault/Errors/<timestamp>_<filename>.md
    Append error metadata block to file
        │
        ▼
[3] Wait 5 minutes
        │
        ▼
[4] Retry once
    ├── Success → status: RETRY_SUCCESS
    │             file stays in Errors/ (with success annotation)
    └── Fail    → status: RETRY_FAILED
                  log second failure to error.log
                  file stays in Errors/ for manual review
```

---

## Output Files

| File | Content |
|------|---------|
| `Logs/error.log` | One line per error event with timestamp, action, file, message |
| `Logs/error_index.json` | Structured JSON index of all error records |
| `AI_Employee_Vault/Errors/*.md` | Quarantined task files with error annotations |

### error.log format
```
[2026-04-18 17:00:00] STATUS=FAILED ATTEMPT=1 ACTION=send_email FILE=task.md ERROR='SMTP timeout'
[2026-04-18 17:05:01] STATUS=RETRY_FAILED ATTEMPT=2 ACTION=send_email FILE=task.md ERROR='RETRY FAILED: ...'
```

### Error file annotation
Each quarantined file gets a block appended at the bottom:
```markdown
---
## Error Record

- **Timestamp:** 2026-04-18 17:00:00
- **Action:** send_email
- **Attempt:** 1
- **Error:** SMTP timeout
- **Folder:** AI_Employee_Vault/Errors/
```

---

## Status Values

| Status | Meaning |
|--------|---------|
| `PENDING_RETRY` | First failure logged, retry scheduled |
| `RETRY_SUCCESS` | Retry succeeded |
| `RETRY_FAILED` | Both attempts failed — manual review needed |

---

## Integration with mcp_executor

Call this skill from `scripts/mcp_executor.py` on any failure:

```python
import subprocess, sys

subprocess.run([
    sys.executable,
    ".claude/skills/error-recovery/scripts/error_recovery.py",
    "--file",   str(task_file_path),
    "--action", action_type,
    "--error",  error_message,
    "--delay",  "300",
])
```

---

## Notes

- `--retry-all` with `--delay 0` retries immediately (useful for testing)
- Files in `Errors/` are never auto-deleted — review manually
- `error_index.json` is the authoritative record of all failures
- Retry logic detects skill by action name — supported: `send_email`, `linkedin_post`, `log_activity`
- Unknown action types are re-queued to `Needs_Action/` with a `RETRY_` prefix
