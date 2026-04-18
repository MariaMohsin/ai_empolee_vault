# Skill: Silver Scheduler

## Metadata
```yaml
name: silver-scheduler
type: orchestrator
tier: silver
status: active
version: 1.0.0
created: 2026-04-17
priority: critical
```

## Goal
Orchestrate autonomous AI Employee operations by running vault watchers, task planner, and approval processing in a continuous loop with proper logging, error handling, and instance management.

---

## Core Responsibilities

### 1. Orchestration Loop
- Run vault-watcher (monitor Inbox)
- Run task-planner (create plans)
- Process approved actions (via MCP Executor)
- Coordinate all Silver Tier components

### 2. Execution Modes
- **Daemon Mode (`--daemon`)**: Run continuously
- **Once Mode (`--once`)**: Single execution cycle
- **Status Mode (`--status`)**: Show system status

### 3. Logging & Monitoring
- Log all actions to `logs/ai_employee.log`
- Rotate logs at 5MB
- Track execution metrics
- Report errors and warnings

### 4. Instance Management
- Prevent duplicate instances
- Use lock files
- Clean up on exit
- Handle crashes gracefully

### 5. Health Checks
- Monitor component status
- Track success/failure rates
- Alert on repeated failures
- Self-healing capabilities

---

## Architecture

```
┌─────────────────────────────────────────────┐
│       SCHEDULER START (run_ai_employee.py)  │
│  Modes: --daemon | --once | --status        │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  CHECK LOCK FILE                             │
│  - Is another instance running?              │
│  - Create lock if not                        │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  INITIALIZE                                  │
│  - Load configuration                        │
│  - Setup logging                            │
│  - Verify components                         │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  MAIN EXECUTION LOOP                         │
│  (Repeat every 5 minutes in daemon mode)    │
└──────────────┬──────────────────────────────┘
               │
               ▼
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌──────────────┐  ┌──────────────┐
│ CYCLE START  │  │ LOG START    │
└──────┬───────┘  └──────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  STEP 1: VAULT WATCHER                       │
│  - Scan AI_Employee_Vault/Inbox              │
│  - Process new files                         │
│  - Log results                               │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  STEP 2: TASK PLANNER                        │
│  - Generate plans for new tasks              │
│  - Prioritize by urgency                     │
│  - Save to Needs_Action                      │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  STEP 3: MCP EXECUTOR                        │
│  - Check Needs_Approval                      │
│  - Execute approved actions                  │
│  - Log execution results                     │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  STEP 4: HEALTH CHECK                        │
│  - Verify all components working             │
│  - Track metrics                             │
│  - Report issues                             │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  CYCLE COMPLETE                              │
│  - Log summary                               │
│  - Update metrics                            │
│  - Rotate logs if needed                     │
└──────────────┬──────────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
    DAEMON         ONCE
     MODE          MODE
        │             │
        ▼             ▼
  WAIT 5 MIN       EXIT
        │
        └──────► REPEAT
```

---

## Execution Modes

### 1. Daemon Mode (`--daemon`)

**Purpose:** Run continuously as a background service

**Behavior:**
- Execute work cycle every 5 minutes
- Run indefinitely until stopped
- Self-recover from errors
- Suitable for production

**Usage:**
```bash
python scripts/run_ai_employee.py --daemon
```

**Output:**
```
[2026-04-17 10:00:00] [START] AI Employee Daemon started
[2026-04-17 10:00:00] [CONFIG] Interval: 300 seconds (5 minutes)
[2026-04-17 10:00:01] [CYCLE] Starting cycle #1
[2026-04-17 10:00:05] [CYCLE] Cycle #1 complete (4 seconds)
[2026-04-17 10:00:05] [SLEEP] Sleeping 300 seconds...
[2026-04-17 10:05:05] [CYCLE] Starting cycle #2
...
```

### 2. Once Mode (`--once`)

**Purpose:** Run a single work cycle and exit

**Behavior:**
- Execute one complete cycle
- Report results
- Exit immediately
- Suitable for testing/cron

**Usage:**
```bash
python scripts/run_ai_employee.py --once
```

**Output:**
```
[2026-04-17 10:00:00] [START] AI Employee running once
[2026-04-17 10:00:01] [VAULT_WATCHER] Processed 2 files
[2026-04-17 10:00:02] [TASK_PLANNER] Generated 1 plan
[2026-04-17 10:00:03] [MCP_EXECUTOR] Executed 1 action
[2026-04-17 10:00:04] [COMPLETE] Cycle complete
[2026-04-17 10:00:04] [EXIT] AI Employee stopped
```

### 3. Status Mode (`--status`)

**Purpose:** Show current system status

**Behavior:**
- Check all components
- Report inbox/task counts
- Show last run time
- Exit immediately

**Usage:**
```bash
python scripts/run_ai_employee.py --status
```

**Output:**
```
==================================================
  AI EMPLOYEE STATUS
==================================================

System Status: RUNNING
Last Cycle: 2026-04-17 10:00:00 (5 minutes ago)

Components:
  Vault Watcher:    [OK]
  Task Planner:     [OK]
  MCP Executor:     [OK]
  Approval Manager: [OK]

Queue Status:
  Inbox:            3 files
  Needs_Action:     2 tasks
  Needs_Approval:   1 pending
  Done (today):     15 completed

Performance (Last 24h):
  Cycles:           288
  Tasks Processed:  42
  Actions Executed: 12
  Errors:           0

Lock File: [ACTIVE] (PID: 12345)

==================================================
```

---

## Configuration

### Default Settings

```json
{
  "scheduler": {
    "interval_seconds": 300,
    "max_errors": 10,
    "error_cooldown": 60
  },
  "logging": {
    "file": "logs/ai_employee.log",
    "level": "INFO",
    "max_size_mb": 5,
    "backup_count": 5,
    "format": "[%(asctime)s] [%(levelname)s] %(message)s"
  },
  "lock_file": {
    "path": "logs/ai_employee.lock",
    "timeout": 300,
    "force_unlock": false
  },
  "health_check": {
    "enabled": true,
    "alert_on_failure": true,
    "max_consecutive_failures": 3
  }
}
```

### Custom Configuration

Edit `config/scheduler_config.json`:

```json
{
  "scheduler": {
    "interval_seconds": 180  # 3 minutes instead of 5
  },
  "logging": {
    "max_size_mb": 10  # Larger logs
  }
}
```

---

## Work Cycle Breakdown

### Full Cycle Steps

```python
def execute_work_cycle():
    """Execute one complete work cycle"""

    cycle_start = time.time()

    # Step 1: Vault Watcher (Process Inbox)
    watcher_result = run_vault_watcher()
    log(f"Vault Watcher: {watcher_result['files_processed']} files processed")

    # Step 2: Task Planner (Generate Plans)
    planner_result = run_task_planner()
    log(f"Task Planner: {planner_result['plans_generated']} plans created")

    # Step 3: MCP Executor (Execute Approved Actions)
    executor_result = run_mcp_executor()
    log(f"MCP Executor: {executor_result['actions_executed']} actions executed")

    # Step 4: Health Check
    health_result = run_health_check()
    log(f"Health Check: {health_result['status']}")

    cycle_time = time.time() - cycle_start

    # Summary
    summary = {
        "files_processed": watcher_result['files_processed'],
        "plans_generated": planner_result['plans_generated'],
        "actions_executed": executor_result['actions_executed'],
        "cycle_time_seconds": cycle_time
    }

    log(f"Cycle complete in {cycle_time:.1f}s: {summary}")

    return summary
```

---

## Logging

### Log Format

```
[TIMESTAMP] [LEVEL] MESSAGE

Examples:
[2026-04-17 10:00:00] [INFO] AI Employee Daemon started
[2026-04-17 10:00:01] [INFO] Cycle #1 started
[2026-04-17 10:00:05] [INFO] Vault Watcher: 2 files processed
[2026-04-17 10:00:06] [INFO] Task Planner: 1 plan generated
[2026-04-17 10:00:07] [INFO] MCP Executor: 0 actions executed
[2026-04-17 10:00:08] [INFO] Cycle #1 complete (7.2s)
[2026-04-17 10:00:08] [ERROR] Component failure: task_planner
```

### Log Rotation

**Triggers:**
- File size reaches 5MB
- Automatic rotation
- Keeps 5 backup files

**Rotation Behavior:**
```
ai_employee.log          (current)
ai_employee.log.1        (previous)
ai_employee.log.2
ai_employee.log.3
ai_employee.log.4
ai_employee.log.5        (oldest, will be deleted on next rotation)
```

### Log Levels

| Level | Usage |
|-------|-------|
| **DEBUG** | Detailed diagnostic info |
| **INFO** | Normal operational messages |
| **WARNING** | Warning messages, system still functional |
| **ERROR** | Error occurred, operation may have failed |
| **CRITICAL** | Critical error, system may be unstable |

---

## Lock File Management

### Purpose
Prevent duplicate instances running simultaneously

### Lock File Location
```
logs/ai_employee.lock
```

### Lock File Content
```json
{
  "pid": 12345,
  "started_at": "2026-04-17T10:00:00Z",
  "hostname": "DESKTOP-ABC123",
  "mode": "daemon"
}
```

### Lock Acquisition Flow

```python
def acquire_lock():
    """Acquire lock file"""

    if lock_file.exists():
        # Check if process is still running
        lock_data = read_lock_file()

        if is_process_running(lock_data['pid']):
            raise LockError(f"Another instance running (PID: {lock_data['pid']})")
        else:
            # Stale lock file, remove it
            log("WARNING: Removing stale lock file")
            lock_file.unlink()

    # Create lock file
    write_lock_file({
        "pid": os.getpid(),
        "started_at": datetime.now().isoformat(),
        "mode": current_mode
    })

    log(f"Lock acquired (PID: {os.getpid()})")
```

### Lock Release

```python
def release_lock():
    """Release lock file"""

    if lock_file.exists():
        lock_file.unlink()
        log("Lock released")
```

### Force Unlock (Manual)

```bash
# If instance crashed and lock file stuck
python scripts/run_ai_employee.py --unlock
```

---

## Error Handling

### Error Categories

| Category | Action | Example |
|----------|--------|---------|
| **Transient** | Retry, continue | Network timeout |
| **Component** | Skip component, continue | Task planner fails |
| **Critical** | Stop daemon, alert | Lock file conflict |

### Error Recovery

```python
def execute_with_error_handling():
    """Execute cycle with error handling"""

    error_count = 0
    max_errors = config['max_errors']

    try:
        execute_work_cycle()
        error_count = 0  # Reset on success

    except ComponentError as e:
        log(f"ERROR: Component failure: {e}")
        error_count += 1

        if error_count >= max_errors:
            log("CRITICAL: Too many errors, stopping daemon")
            stop_daemon()
        else:
            log(f"Continuing... ({error_count}/{max_errors} errors)")

    except CriticalError as e:
        log(f"CRITICAL: {e}")
        stop_daemon()
```

---

## Health Checks

### Component Checks

```python
def health_check():
    """Check all components"""

    checks = {
        "vault_watcher": check_vault_watcher(),
        "task_planner": check_task_planner(),
        "mcp_executor": check_mcp_executor(),
        "approval_manager": check_approval_manager()
    }

    all_ok = all(checks.values())

    if not all_ok:
        log("WARNING: Some components unhealthy")
        for component, status in checks.items():
            if not status:
                log(f"  {component}: FAILED")

    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks
    }
```

### Metrics Tracking

```json
{
  "cycles_total": 1440,
  "cycles_successful": 1438,
  "cycles_failed": 2,
  "files_processed_total": 342,
  "plans_generated_total": 156,
  "actions_executed_total": 89,
  "avg_cycle_time_seconds": 4.2,
  "uptime_hours": 120,
  "last_error": "2026-04-15T14:30:00Z"
}
```

---

## Usage Examples

### Production Daemon

```bash
# Start daemon
python scripts/run_ai_employee.py --daemon

# Runs forever, checking every 5 minutes
# Stop with Ctrl+C or kill command
```

### Cron Job (Once Mode)

```bash
# Add to crontab: run every 5 minutes
*/5 * * * * cd /path/to/silver && python scripts/run_ai_employee.py --once >> logs/cron.log 2>&1
```

### Windows Task Scheduler

**Action:**
```
Program: python.exe
Arguments: C:\path\to\silver\scripts\run_ai_employee.py --once
Start in: C:\path\to\silver
```

**Trigger:**
- Repeat task every 5 minutes
- For a duration of: Indefinitely

### Status Check Script

```bash
#!/bin/bash
# check_ai_employee.sh

STATUS=$(python scripts/run_ai_employee.py --status)

if echo "$STATUS" | grep -q "ERROR"; then
    # Send alert
    echo "AI Employee has errors!" | mail -s "Alert" admin@example.com
fi
```

---

## Integration

### With System Services

**Linux (systemd):**

```ini
# /etc/systemd/system/ai-employee.service
[Unit]
Description=AI Employee Daemon
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/silver
ExecStart=/usr/bin/python3 scripts/run_ai_employee.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Commands:**
```bash
sudo systemctl enable ai-employee
sudo systemctl start ai-employee
sudo systemctl status ai-employee
sudo journalctl -u ai-employee -f  # View logs
```

---

## Monitoring & Alerts

### Log Monitoring

```bash
# Watch logs in real-time
tail -f logs/ai_employee.log

# Search for errors
grep ERROR logs/ai_employee.log

# Count cycles today
grep "Cycle complete" logs/ai_employee.log | wc -l
```

### Alert on Errors

```python
def send_alert(message):
    """Send alert on critical issues"""

    # Email alert
    send_email(
        to="admin@example.com",
        subject="AI Employee Alert",
        body=message
    )

    # Slack alert
    send_slack_message(
        channel="#alerts",
        message=f"⚠️ AI Employee: {message}"
    )
```

---

## Best Practices

### 1. Start with Once Mode
✅ Test with `--once` first
✅ Verify all components work
✅ Check logs for errors
✅ Then switch to daemon

### 2. Monitor Logs Regularly
✅ Review logs daily
✅ Set up log rotation
✅ Alert on errors
✅ Track performance metrics

### 3. Graceful Shutdown
✅ Use Ctrl+C for daemon
✅ Wait for current cycle to complete
✅ Lock file auto-releases
✅ No data loss

### 4. Resource Management
✅ Set appropriate intervals
✅ Monitor CPU/memory usage
✅ Rotate logs regularly
✅ Clean up old files

---

## Troubleshooting

### Issue: Lock file stuck
**Solution:**
```bash
python scripts/run_ai_employee.py --unlock
# or manually delete logs/ai_employee.lock
```

### Issue: Daemon not starting
**Check:**
1. Is another instance running?
2. Check lock file
3. Review logs for errors
4. Verify Python version

### Issue: Components failing
**Solution:**
```bash
# Check status
python scripts/run_ai_employee.py --status

# Review component health
# Fix individual components
# Restart daemon
```

### Issue: High memory usage
**Solution:**
- Reduce interval
- Rotate logs more frequently
- Clear old files from Done/
- Monitor Python memory leaks

---

## Performance Metrics

### Target Performance

| Metric | Target | Acceptable |
|--------|--------|------------|
| Cycle Time | < 5s | < 10s |
| Memory Usage | < 100MB | < 200MB |
| CPU Usage | < 5% | < 10% |
| Success Rate | > 99% | > 95% |
| Uptime | > 99% | > 95% |

---

## Future Enhancements

### Gold Tier
- **Adaptive scheduling** - Adjust interval based on load
- **Parallel execution** - Run components concurrently
- **Distributed mode** - Multiple workers
- **Advanced monitoring** - Prometheus/Grafana
- **Auto-healing** - Self-repair on failures
- **Load balancing** - Distribute work across instances

---

**Status:** ✅ Production Ready
**Critical Component:** YES (orchestrates everything)
**Dependencies:** All Silver Tier skills
**Last Updated:** 2026-04-17
