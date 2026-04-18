# Auto-Run File Watcher

## Current Status (Bronze Tier)
- File watcher (`file_watcher.py`) must be started **manually**
- Command: `python file_watcher.py`
- **Currently running:** Task ID b04acd1
- **Known Limitation:** Works reliably for bash/terminal-created files, but may not detect atomically-written files (e.g., from Write tool) on Windows
- Acceptable for Bronze tier development/testing

## Problem
- If watcher stops or system restarts, files in `/Inbox` won't move to `/Needs_Action`
- AI Employee will report "Watcher not running" and wait
- Requires manual intervention to restart watcher

## Future Improvement (Silver/Gold Tier)

### Option 1: System Startup
Run `file_watcher.py` automatically on system startup

**Windows:**
- Add to Task Scheduler
- Or add to Startup folder

**Linux/Mac:**
- Use systemd service
- Or add to crontab with `@reboot`

### Option 2: Service Wrapper
Wrap file watcher in a proper service

**Benefits:**
- Auto-restart on failure
- System integration
- Better logging
- Process management

**Tools:**
- Windows: NSSM (Non-Sucking Service Manager)
- Linux: systemd unit file
- Cross-platform: Docker container

### Option 3: Background Daemon
Convert to a proper daemon/background process
- Detach from terminal
- Handle signals properly (SIGTERM, etc.)
- PID file management
- Log rotation

## Implementation Priority
- Bronze: Manual start ✓ (current)
- Silver: Startup script
- Gold: Full service with monitoring

## Notes
- For now, remember to start watcher manually before expecting automation
- Future versions should handle this automatically
- Consider adding health check endpoint for monitoring

---

**Created:** 2026-02-10
**Status:** Planned for future tiers
