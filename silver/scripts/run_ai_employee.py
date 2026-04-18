#!/usr/bin/env python3
"""
AI Employee Scheduler - Silver Tier Orchestrator
Runs vault watcher, task planner, and MCP executor in a loop

Usage:
    python run_ai_employee.py --daemon    # Run continuously
    python run_ai_employee.py --once      # Single execution
    python run_ai_employee.py --status    # Show status
    python run_ai_employee.py --unlock    # Force unlock
"""

import os
import sys
import time
import json
import signal
from pathlib import Path
from datetime import datetime
import logging

# Load .env from project root automatically
def _load_env():
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

_load_env()
from logging.handlers import RotatingFileHandler


class AIEmployeeScheduler:
    """
    Main scheduler orchestrator for AI Employee
    """

    def __init__(self, root_path=None):
        if root_path is None:
            self.root = Path(__file__).parent.parent
        else:
            self.root = Path(root_path)

        # Paths
        self.logs_dir = self.root / "logs"
        self.log_file = self.logs_dir / "ai_employee.log"
        self.lock_file = self.logs_dir / "ai_employee.lock"
        self.config_file = self.root / "config" / "scheduler_config.json"

        # State
        self.running = False
        self.cycle_count = 0
        self.error_count = 0

        # Configuration
        self.config = {
            "interval_seconds": 300,  # 5 minutes
            "max_errors": 10,
            "log_max_bytes": 5 * 1024 * 1024,  # 5MB
            "log_backup_count": 5
        }

        self._ensure_directories()
        self._load_config()
        self._setup_logging()

    def _ensure_directories(self):
        """Create required directories"""
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self):
        """Load configuration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config.get("scheduler", {}))
            except:
                pass

    def _setup_logging(self):
        """Setup logging with rotation"""
        self.logger = logging.getLogger("AIEmployee")
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers
        self.logger.handlers = []

        # File handler with rotation
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=self.config['log_max_bytes'],
            backupCount=self.config['log_backup_count']
        )
        file_handler.setFormatter(
            logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        )
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        )
        self.logger.addHandler(console_handler)

    def log(self, level, message):
        """Log message with level"""
        if level == "INFO":
            self.logger.info(message)
        elif level == "WARNING":
            self.logger.warning(message)
        elif level == "ERROR":
            self.logger.error(message)
        elif level == "CRITICAL":
            self.logger.critical(message)
        else:
            self.logger.debug(message)

    def acquire_lock(self):
        """Acquire lock file"""
        if self.lock_file.exists():
            # Check if stale
            try:
                with open(self.lock_file, "r") as f:
                    lock_data = json.load(f)

                pid = lock_data.get("pid")

                # Check if process exists
                try:
                    if pid and os.kill(pid, 0) == None:
                        # Process exists
                        raise Exception(f"Another instance running (PID: {pid})")
                except OSError:
                    # Process doesn't exist, remove stale lock
                    self.log("WARNING", "Removing stale lock file")
                    self.lock_file.unlink()
            except:
                # Can't read lock file, remove it
                self.lock_file.unlink()

        # Create lock file
        lock_data = {
            "pid": os.getpid(),
            "started_at": datetime.now().isoformat(),
            "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown"
        }

        with open(self.lock_file, "w") as f:
            json.dump(lock_data, f, indent=2)

        self.log("INFO", f"Lock acquired (PID: {os.getpid()})")

    def release_lock(self):
        """Release lock file"""
        if self.lock_file.exists():
            self.lock_file.unlink()
            self.log("INFO", "Lock released")

    def run_vault_watcher(self):
        """Run vault watcher"""
        try:
            # Import and run
            sys.path.insert(0, str(self.root / "scripts"))
            from task_planner import TaskPlanner

            watcher = TaskPlanner()
            result = watcher.process_inbox()

            return {
                "success": True,
                "files_processed": result.get("files_processed", 0)
            }

        except Exception as e:
            self.log("ERROR", f"Vault watcher failed: {e}")
            return {"success": False, "files_processed": 0}

    def run_task_planner(self):
        """Run task planner — already called inside vault watcher, kept for clarity."""
        return {"success": True, "plans_generated": 0}

    def run_gmail_watcher(self):
        """Fetch new emails and convert to inbox tasks."""
        try:
            import subprocess
            script = self.root / "scripts" / "watch_gmail.py"
            if not script.exists():
                return {"success": False, "emails": 0, "note": "watch_gmail.py not found"}

            result = subprocess.run(
                [sys.executable, str(script), "--mock", "--once"],
                capture_output=True, text=True, timeout=30
            )
            self.log("GMAIL", result.stdout.strip() or result.stderr.strip())
            return {"success": result.returncode == 0, "emails": 0}
        except Exception as e:
            self.log("ERROR", f"Gmail watcher failed: {e}")
            return {"success": False, "emails": 0}

    def run_mcp_executor(self):
        """Run MCP executor for approved actions"""
        try:
            sys.path.insert(0, str(self.root / "scripts"))
            from mcp_executor import MCPExecutor

            executor = MCPExecutor()
            result = executor.process_approved_actions()

            return {
                "success": result.get("success", False),
                "actions_executed": result.get("stats", {}).get("executed", 0)
            }

        except Exception as e:
            self.log("ERROR", f"MCP executor failed: {e}")
            return {"success": False, "actions_executed": 0}

    def get_queue_stats(self):
        """Get queue statistics"""
        stats = {
            "inbox": 0,
            "needs_action": 0,
            "needs_approval": 0,
            "done_today": 0
        }

        try:
            # Count inbox files
            inbox = self.root / "AI_Employee_Vault" / "Inbox"
            if inbox.exists():
                stats["inbox"] = len(list(inbox.glob("*.md")))

            # Count needs action
            needs_action = self.root / "AI_Employee_Vault" / "Needs_Action"
            if needs_action.exists():
                stats["needs_action"] = len(list(needs_action.glob("*.md")))

            # Count needs approval
            needs_approval = self.root / "AI_Employee_Vault" / "Needs_Approval"
            if needs_approval.exists():
                stats["needs_approval"] = len(list(needs_approval.glob("*.md")))

            # Count done today
            done = self.root / "AI_Employee_Vault" / "Done"
            if done.exists():
                today = datetime.now().date()
                for f in done.glob("*.md"):
                    modified = datetime.fromtimestamp(f.stat().st_mtime).date()
                    if modified == today:
                        stats["done_today"] += 1

        except Exception as e:
            self.log("ERROR", f"Failed to get queue stats: {e}")

        return stats

    def execute_work_cycle(self):
        """Execute one complete work cycle"""
        self.cycle_count += 1
        cycle_start = time.time()

        self.log("INFO", f"=== Cycle #{self.cycle_count} started ===")

        try:
            # Step 1: Gmail Watcher — fetch new emails → Inbox
            self.log("INFO", "Step 1: Checking Gmail...")
            gmail_result = self.run_gmail_watcher()
            self.log("INFO", f"  Gmail watcher: {'OK' if gmail_result['success'] else 'skipped'}")

            # Step 2: Vault Watcher + Task Planner — Inbox → Needs_Action
            self.log("INFO", "Step 2: Running vault watcher + task planner...")
            watcher_result = self.run_vault_watcher()
            self.log("INFO", f"  Vault watcher: {watcher_result['files_processed']} files processed")

            # Step 3: MCP Executor — execute approved actions in Needs_Approval
            self.log("INFO", "Step 3: Running MCP executor (approved actions)...")
            executor_result = self.run_mcp_executor()
            self.log("INFO", f"  MCP executor: {executor_result['actions_executed']} actions executed")

            # Calculate cycle time
            cycle_time = time.time() - cycle_start
            self.log("INFO", f"=== Cycle #{self.cycle_count} complete ({cycle_time:.1f}s) ===")
            self.error_count = 0

            return {
                "success": True,
                "files_processed": watcher_result['files_processed'],
                "actions_executed": executor_result['actions_executed'],
                "cycle_time": cycle_time
            }

        except Exception as e:
            self.log("ERROR", f"Cycle failed: {e}")
            self.error_count += 1

            return {
                "success": False,
                "error": str(e)
            }

    def run_once(self):
        """Run a single work cycle"""
        self.log("INFO", "AI Employee running once...")

        try:
            self.acquire_lock()

            result = self.execute_work_cycle()

            self.log("INFO", f"Single cycle complete")
            self.log("INFO", f"  Files processed: {result.get('files_processed', 0)}")
            self.log("INFO", f"  Actions executed: {result.get('actions_executed', 0)}")

            return result

        finally:
            self.release_lock()

    def run_daemon(self):
        """Run continuously in daemon mode"""
        self.log("INFO", "AI Employee Daemon starting...")
        self.log("INFO", f"Interval: {self.config['interval_seconds']} seconds ({self.config['interval_seconds']//60} minutes)")

        try:
            self.acquire_lock()
            self.running = True

            # Setup signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

            while self.running:
                # Execute cycle
                result = self.execute_work_cycle()

                # Check error count
                if self.error_count >= self.config['max_errors']:
                    self.log("CRITICAL", f"Too many errors ({self.error_count}), stopping daemon")
                    break

                # Sleep until next cycle
                if self.running:
                    self.log("INFO", f"Sleeping {self.config['interval_seconds']} seconds...")
                    time.sleep(self.config['interval_seconds'])

        except KeyboardInterrupt:
            self.log("INFO", "Daemon stopped by user (Ctrl+C)")
        except Exception as e:
            self.log("CRITICAL", f"Daemon error: {e}")
        finally:
            self.release_lock()
            self.log("INFO", "AI Employee Daemon stopped")

    def show_status(self):
        """Show current status"""
        print("\n" + "="*60)
        print("  AI EMPLOYEE STATUS")
        print("="*60 + "\n")

        # Check if running
        if self.lock_file.exists():
            try:
                with open(self.lock_file, "r") as f:
                    lock_data = json.load(f)

                pid = lock_data.get("pid")
                started = lock_data.get("started_at", "unknown")

                try:
                    os.kill(pid, 0)
                    print(f"Status: RUNNING (PID: {pid})")
                    print(f"Started: {started}")
                except OSError:
                    print("Status: STOPPED (stale lock file)")
            except:
                print("Status: UNKNOWN")
        else:
            print("Status: STOPPED")

        print()

        # Queue stats
        stats = self.get_queue_stats()

        print("Queue Status:")
        print(f"  Inbox:            {stats['inbox']} files")
        print(f"  Needs_Action:     {stats['needs_action']} tasks")
        print(f"  Needs_Approval:   {stats['needs_approval']} pending")
        print(f"  Done (today):     {stats['done_today']} completed")

        print()

        # Component check
        print("Components:")

        components = {
            "Task Planner": (self.root / "scripts" / "task_planner.py").exists(),
            "MCP Executor": (self.root / "scripts" / "mcp_executor.py").exists(),
            "Approval Manager": (self.root / "scripts" / "request_approval.py").exists()
        }

        for component, exists in components.items():
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {component}: {status}")

        print()

        # Recent log entries
        if self.log_file.exists():
            print("Recent Activity (last 5 lines):")
            try:
                with open(self.log_file, "r") as f:
                    lines = f.readlines()
                    for line in lines[-5:]:
                        print(f"  {line.strip()}")
            except:
                print("  (Could not read log)")

        print("\n" + "="*60 + "\n")

    def force_unlock(self):
        """Force remove lock file"""
        if self.lock_file.exists():
            self.lock_file.unlink()
            print("Lock file removed")
            self.log("WARNING", "Lock file forcefully removed")
        else:
            print("No lock file found")

    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        self.log("INFO", f"Received signal {signum}, stopping gracefully...")
        self.running = False


def main():
    """Main entry point"""
    scheduler = AIEmployeeScheduler()

    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == "--daemon":
            scheduler.run_daemon()

        elif mode == "--once":
            scheduler.run_once()

        elif mode == "--status":
            scheduler.show_status()

        elif mode == "--unlock":
            scheduler.force_unlock()

        else:
            print(f"Unknown mode: {mode}")
            print("Use: --daemon, --once, --status, or --unlock")

    else:
        print("""
AI Employee Scheduler - Silver Tier Orchestrator

Usage:
  python run_ai_employee.py --daemon    # Run continuously (every 5 minutes)
  python run_ai_employee.py --once      # Single execution
  python run_ai_employee.py --status    # Show current status
  python run_ai_employee.py --unlock    # Force remove lock file

Examples:
  # Start daemon
  python run_ai_employee.py --daemon

  # Run once (for cron)
  python run_ai_employee.py --once

  # Check status
  python run_ai_employee.py --status

Production:
  # Run as systemd service
  sudo systemctl start ai-employee

  # Run with nohup
  nohup python run_ai_employee.py --daemon &

  # Add to crontab (every 5 minutes)
  */5 * * * * cd /path/to/silver && python scripts/run_ai_employee.py --once
        """)


if __name__ == "__main__":
    main()
