# Skill: Vault Watcher

## Metadata
```yaml
name: vault-watcher
type: automation
tier: bronze
status: active
version: 1.0.0
created: 2026-04-17
```

## Goal
Continuously monitor the `AI_Employee_Vault/Inbox` folder for new `.md` files and automatically trigger Claude AI processing workflow when new files are detected.

## How It Works

### Monitoring Strategy
- **Type:** Polling-based (not event-driven)
- **Interval:** 10-30 seconds (configurable)
- **Target:** `AI_Employee_Vault/Inbox/` folder
- **File Type:** Markdown files (`.md` extension only)

### Workflow

```
┌─────────────────────────────────────────────────┐
│  1. SCAN INBOX (every 10-30s)                   │
│     └─> Check for new .md files                 │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  2. CHECK PROCESSED LOG                          │
│     └─> Load logs/processed_files.json          │
│     └─> Filter out already processed files      │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  3. NEW FILE FOUND?                              │
│     ├─> YES: Continue to step 4                 │
│     └─> NO: Wait and scan again                 │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  4. LOG DETECTION                                │
│     └─> Write to logs/actions.log               │
│     └─> Timestamp + filename + action           │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  5. TRIGGER AI WORKFLOW                          │
│     └─> Execute: run_ai_employee.py --once      │
│     └─> Pass detected file as context           │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  6. MARK AS PROCESSED                            │
│     └─> Add to logs/processed_files.json        │
│     └─> Store: filename, timestamp, hash        │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  7. REPEAT                                       │
│     └─> Wait 10-30 seconds                      │
│     └─> Go back to step 1                       │
└─────────────────────────────────────────────────┘
```

## Trigger Conditions

### Files WILL Be Processed
✅ New `.md` files in Inbox
✅ Files not in processed log
✅ Files with valid content (not empty)
✅ Files created/modified since last scan

### Files WILL NOT Be Processed
❌ Non-markdown files (`.txt`, `.pdf`, etc.)
❌ Files already in processed log
❌ Temporary files (`.tmp`, `~$`, etc.)
❌ Hidden files (starting with `.`)
❌ Empty files (0 bytes)

## Deduplication Strategy

### Method 1: Filename + Timestamp Tracking
Store processed files with:
- Filename
- Detection timestamp
- File size
- Last modified time

### Method 2: Content Hash (Optional)
- Calculate MD5/SHA256 of file content
- Prevents reprocessing identical files with different names

### Storage
```json
{
  "processed_files": [
    {
      "filename": "task_001.md",
      "detected_at": "2026-04-17T09:30:00Z",
      "size_bytes": 1024,
      "hash": "a1b2c3d4...",
      "processed_at": "2026-04-17T09:30:05Z",
      "status": "completed"
    }
  ]
}
```

## AI Processing Workflow

When a new file is detected, the watcher triggers:

```bash
python run_ai_employee.py --once --file="AI_Employee_Vault/Inbox/task_001.md"
```

This command should:
1. Read the detected file
2. Process it according to Company Handbook rules
3. Generate appropriate response/action
4. Move file to appropriate folder (Needs_Action/Done)
5. Log the outcome

## Logging

### Action Log Format
**File:** `logs/actions.log`

```
[2026-04-17 09:30:00] [SCAN] Scanning Inbox folder...
[2026-04-17 09:30:01] [DETECT] New file found: task_001.md
[2026-04-17 09:30:02] [TRIGGER] Starting AI workflow for: task_001.md
[2026-04-17 09:30:08] [SUCCESS] AI processing completed for: task_001.md
[2026-04-17 09:30:09] [MARK] File marked as processed: task_001.md
[2026-04-17 09:30:39] [SCAN] Scanning Inbox folder...
[2026-04-17 09:30:40] [IDLE] No new files detected
```

### Log Levels
- `[SCAN]` - Regular polling check
- `[DETECT]` - New file found
- `[TRIGGER]` - AI workflow started
- `[SUCCESS]` - Processing completed
- `[ERROR]` - Processing failed
- `[MARK]` - File added to processed log
- `[IDLE]` - No activity

## Configuration

### Environment Variables
```bash
INBOX_PATH="AI_Employee_Vault/Inbox"
SCAN_INTERVAL=30  # seconds
PROCESSED_LOG="logs/processed_files.json"
ACTION_LOG="logs/actions.log"
AI_COMMAND="python run_ai_employee.py --once"
```

### Tuning Performance

**Fast Mode (10 seconds):**
- Use when expecting frequent files
- Higher CPU usage
- Near real-time processing

**Balanced Mode (30 seconds):**
- Default recommended
- Good balance of responsiveness and resources
- Production-ready

**Slow Mode (60+ seconds):**
- Use for low-traffic scenarios
- Minimal resource usage
- Batch-oriented processing

## Error Handling

### Scenarios

**File Read Error:**
```python
try:
    content = read_file(filepath)
except PermissionError:
    log_error("Cannot read file - permission denied")
    skip_file()
```

**AI Processing Timeout:**
```python
timeout = 300  # 5 minutes max
result = run_with_timeout(ai_workflow, timeout)
if result.timeout:
    log_error("AI processing timeout")
    retry_later()
```

**Disk Full:**
```python
if disk_space_low():
    log_error("Disk space low - pausing watcher")
    send_alert()
    sleep(300)  # Wait 5 minutes
```

## Production Deployment

### Running as Service

**Windows (Task Scheduler):**
```powershell
# Create scheduled task that runs on startup
schtasks /create /tn "VaultWatcher" /tr "python C:\path\to\scripts\watch_inbox.py" /sc onstart /ru SYSTEM
```

**Linux (systemd):**
```bash
# Create /etc/systemd/system/vault-watcher.service
[Unit]
Description=Vault Watcher Service
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/ai_employee
ExecStart=/usr/bin/python3 scripts/watch_inbox.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**macOS (launchd):**
```xml
<!-- ~/Library/LaunchAgents/com.vaultwatcher.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.vaultwatcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/scripts/watch_inbox.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

### Process Management

**Start:**
```bash
python scripts/watch_inbox.py &
echo $! > logs/watcher.pid
```

**Stop:**
```bash
kill $(cat logs/watcher.pid)
rm logs/watcher.pid
```

**Status:**
```bash
if ps -p $(cat logs/watcher.pid) > /dev/null; then
    echo "Watcher is running"
else
    echo "Watcher is stopped"
fi
```

### Health Monitoring

```python
# Health check endpoint (optional)
def health_check():
    return {
        "status": "running",
        "last_scan": "2026-04-17T09:30:00Z",
        "files_processed_today": 42,
        "uptime_seconds": 86400,
        "errors_today": 0
    }
```

## Performance Metrics

### Resource Usage (Expected)
- **Memory:** ~10-20 MB
- **CPU:** <1% (idle), ~5% (processing)
- **Disk I/O:** Minimal (read-only scans)
- **Network:** None (local only)

### Scalability
- **Files per hour:** 100+ (with 30s interval)
- **Max file size:** No limit (content hash optional)
- **Concurrent files:** Processes sequentially
- **Uptime target:** 99.9% (with auto-restart)

## Testing

### Unit Tests
```bash
pytest tests/test_vault_watcher.py -v
```

### Integration Test
```bash
# Start watcher
python scripts/watch_inbox.py &

# Create test file
echo "# Test" > AI_Employee_Vault/Inbox/test.md

# Wait 30 seconds
sleep 30

# Verify processing
cat logs/actions.log | grep "test.md"
```

### Stress Test
```bash
# Create 100 test files
for i in {1..100}; do
    echo "# Test $i" > AI_Employee_Vault/Inbox/test_$i.md
done

# Monitor processing
tail -f logs/actions.log
```

## Dependencies

```txt
# No external dependencies required!
# Uses Python standard library only:
- os
- time
- json
- hashlib
- pathlib
- datetime
- subprocess
```

## Upgrade Path

### Silver Tier Enhancements
- Multiple inbox monitoring (Gmail, LinkedIn, etc.)
- Real-time webhook support
- Parallel processing
- Priority queues
- Advanced filtering rules

### Gold Tier Features
- Machine learning for file classification
- Predictive processing
- Distributed monitoring
- Cloud sync support
- Analytics dashboard

## Troubleshooting

### Issue: Watcher not detecting files
**Solution:**
1. Check Inbox path is correct
2. Verify file has `.md` extension
3. Check logs/actions.log for errors
4. Ensure watcher is running (`ps aux | grep watch_inbox`)

### Issue: Same file processed multiple times
**Solution:**
1. Check logs/processed_files.json exists
2. Verify file permissions (read/write)
3. Ensure hash calculation is working
4. Review deduplication logic

### Issue: High CPU usage
**Solution:**
1. Increase scan interval (30s → 60s)
2. Check for infinite loops in code
3. Limit AI processing timeout
4. Monitor system resources

## Related Skills
- **task_processor.skill.md** - Processes the detected tasks
- **task_planner.skill.md** - Plans task execution
- **file_watcher.py** - Event-driven alternative (Bronze Tier)

---

**Implementation:** `scripts/watch_inbox.py`
**Status:** ✅ Production Ready
**Tier:** Bronze → Silver
**Last Updated:** 2026-04-17
