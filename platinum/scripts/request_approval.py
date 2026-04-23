#!/usr/bin/env python3
"""
Human Approval Agent Skill - Request and Monitor Approvals
Blocks execution until human approves/rejects or timeout occurs

Usage:
    python request_approval.py --create --action "send_email" --params '{...}'
    python request_approval.py --list-pending
    python request_approval.py --status <request_id>
    python request_approval.py --test
"""

import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import sys


class ApprovalRequest:
    """
    Manages approval request lifecycle
    """

    def __init__(self, root_path=None):
        if root_path is None:
            self.root = Path(__file__).parent.parent
        else:
            self.root = Path(root_path)

        # Paths
        self.needs_approval = self.root / "AI_Employee_Vault" / "Needs_Approval"
        self.logs_dir = self.root / "logs"
        self.action_log = self.logs_dir / "actions.log"
        self.config_file = self.root / "config" / "approval_config.json"

        self._ensure_directories()
        self._load_config()

    def _ensure_directories(self):
        """Create required directories"""
        for directory in [self.needs_approval, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_config(self):
        """Load configuration"""
        self.config = {
            "timeout": {
                "default_seconds": 3600,  # 1 hour
                "by_action_type": {
                    "send_email": 1800,       # 30 minutes
                    "linkedin_post": 3600,    # 1 hour
                    "delete_file": 7200       # 2 hours
                }
            },
            "monitoring": {
                "poll_interval": 10  # Check every 10 seconds
            }
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
            except:
                pass

    def log(self, level, message):
        """Write to action log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}\n"

        with open(self.action_log, "a", encoding="utf-8") as f:
            f.write(entry)

        print(entry.strip())

    def generate_request_id(self):
        """Generate unique request ID"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]

    def get_timeout_for_action(self, action_type):
        """Get timeout duration for action type"""
        timeouts = self.config["timeout"]["by_action_type"]
        return timeouts.get(action_type, self.config["timeout"]["default_seconds"])

    def create_approval_file(self, action_type, details, risk_level="medium", timeout=None):
        """
        Create approval request file

        Args:
            action_type (str): Type of action (send_email, linkedin_post, etc.)
            details (dict): Action details/parameters
            risk_level (str): Risk level (low, medium, high, critical)
            timeout (int): Timeout in seconds (None = use default)

        Returns:
            dict: Request info with request_id and filepath
        """
        request_id = self.generate_request_id()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if timeout is None:
            timeout = self.get_timeout_for_action(action_type)

        timeout_dt = datetime.now() + timedelta(seconds=timeout)

        # Generate filename
        filename = f"approval_{action_type}_{timestamp}_{request_id}.md"
        filepath = self.needs_approval / filename

        # Format details
        details_str = ""
        if isinstance(details, dict):
            for key, value in details.items():
                details_str += f"**{key.title()}:** {value}\n"
        else:
            details_str = str(details)

        # Create content
        content = f"""# Approval Request: {action_type.replace('_', ' ').title()}

```yaml
request_id: {request_id}
action_type: {action_type}
created_at: {datetime.now().isoformat()}
requested_by: ai_employee
timeout: {timeout}
status: pending
```

## Action Details

**Type:** {action_type.replace('_', ' ').title()}

{details_str}

## Risk Assessment

**Risk Level:** {risk_level.upper()}

**Potential Impact:**
- This action will be executed externally
- Requires manager oversight

**Mitigation:**
- Human approval required before execution
- Full audit trail maintained

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
**Timeout:** {timeout_dt.strftime("%Y-%m-%d %H:%M:%S")} ({timeout} seconds)
**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        # Write file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        self.log("APPROVAL_REQUEST", f"Created request {request_id} ({action_type})")
        self.log("APPROVAL_REQUEST", f"File: {filename}")
        self.log("APPROVAL_REQUEST", f"Timeout: {timeout} seconds")

        return {
            "request_id": request_id,
            "filepath": filepath,
            "filename": filename,
            "timeout": timeout,
            "created_at": datetime.now().isoformat()
        }

    def check_decision(self, filepath):
        """
        Check if decision has been made

        Args:
            filepath (Path): Path to approval file

        Returns:
            dict: Decision status and details
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for decision
            if "DECISION: APPROVED" in content:
                return {"status": "approved", "decision": "APPROVED"}

            elif "DECISION: REJECTED" in content:
                # Extract reason
                reason = "No reason provided"
                for line in content.split("\n"):
                    if line.strip().startswith("Reason:"):
                        reason = line.split(":", 1)[1].strip()
                        break

                return {"status": "rejected", "decision": "REJECTED", "reason": reason}

            else:
                return {"status": "pending", "decision": None}

        except Exception as e:
            self.log("ERROR", f"Failed to check decision: {e}")
            return {"status": "error", "decision": None}

    def wait_for_approval(self, filepath, timeout, request_id):
        """
        Wait for approval decision with timeout

        Args:
            filepath (Path): Path to approval file
            timeout (int): Timeout in seconds
            request_id (str): Request ID

        Returns:
            dict: Final decision status
        """
        poll_interval = self.config["monitoring"]["poll_interval"]
        start_time = time.time()
        polls = 0

        self.log("APPROVAL_WAIT", f"Waiting for decision on {request_id}")
        self.log("APPROVAL_WAIT", f"Timeout: {timeout} seconds ({timeout//60} minutes)")

        while time.time() - start_time < timeout:
            polls += 1

            # Check decision
            result = self.check_decision(filepath)

            if result["status"] == "approved":
                elapsed = int(time.time() - start_time)
                self.log("APPROVAL_DECISION", f"Request {request_id}: APPROVED")
                self.log("APPROVAL_DECISION", f"Decision time: {elapsed} seconds ({elapsed//60}m {elapsed%60}s)")

                # Rename file
                new_path = filepath.parent / f"{filepath.name}.approved"
                filepath.rename(new_path)
                self.log("APPROVAL_RENAME", f"Renamed to: {new_path.name}")

                return {
                    "status": "approved",
                    "elapsed_seconds": elapsed,
                    "polls": polls
                }

            elif result["status"] == "rejected":
                elapsed = int(time.time() - start_time)
                self.log("APPROVAL_DECISION", f"Request {request_id}: REJECTED")
                self.log("APPROVAL_REASON", f"Reason: {result.get('reason')}")

                # Rename file
                new_path = filepath.parent / f"{filepath.name}.rejected"
                filepath.rename(new_path)
                self.log("APPROVAL_RENAME", f"Renamed to: {new_path.name}")

                return {
                    "status": "rejected",
                    "reason": result.get("reason"),
                    "elapsed_seconds": elapsed,
                    "polls": polls
                }

            # Still pending, wait
            time.sleep(poll_interval)

        # Timeout reached
        elapsed = int(time.time() - start_time)
        self.log("APPROVAL_TIMEOUT", f"Request {request_id}: TIMEOUT")
        self.log("APPROVAL_TIMEOUT", f"Elapsed: {elapsed} seconds ({elapsed//60} minutes)")

        # Rename file
        new_path = filepath.parent / f"{filepath.name}.timeout"
        filepath.rename(new_path)
        self.log("APPROVAL_RENAME", f"Renamed to: {new_path.name}")

        return {
            "status": "timeout",
            "elapsed_seconds": elapsed,
            "polls": polls
        }

    def list_pending(self):
        """List all pending approval requests"""
        if not self.needs_approval.exists():
            return []

        pending = []
        for filepath in self.needs_approval.glob("approval_*.md"):
            # Skip already decided files
            if filepath.suffix in ['.approved', '.rejected', '.timeout']:
                continue

            # Get file info
            created = datetime.fromtimestamp(filepath.stat().st_mtime)
            age_seconds = (datetime.now() - created).total_seconds()

            # Extract request_id from filename
            parts = filepath.stem.split("_")
            request_id = parts[-1] if len(parts) > 3 else "unknown"

            pending.append({
                "file": filepath.name,
                "request_id": request_id,
                "created": created.strftime("%Y-%m-%d %H:%M:%S"),
                "age_seconds": int(age_seconds),
                "age_minutes": int(age_seconds // 60)
            })

        return sorted(pending, key=lambda x: x['age_seconds'], reverse=True)

    def get_status(self, request_id):
        """Get status of specific approval request"""
        # Find file with this request_id
        pattern = f"approval_*_{request_id}.md*"

        for filepath in self.needs_approval.glob(pattern):
            # Check extension to determine status
            if filepath.suffix == ".approved":
                return {"status": "approved", "file": filepath.name}
            elif filepath.suffix == ".rejected":
                return {"status": "rejected", "file": filepath.name}
            elif filepath.suffix == ".timeout":
                return {"status": "timeout", "file": filepath.name}
            elif filepath.suffix == ".md":
                result = self.check_decision(filepath)
                return {"status": result["status"], "file": filepath.name}

        return {"status": "not_found", "file": None}

    def cleanup_old(self, older_than_hours=24):
        """Clean up old approval files"""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)

        cleaned = 0
        for filepath in self.needs_approval.glob("approval_*"):
            modified = datetime.fromtimestamp(filepath.stat().st_mtime)

            if modified < cutoff:
                filepath.unlink()
                cleaned += 1
                self.log("CLEANUP", f"Removed old file: {filepath.name}")

        return cleaned


def request_approval(action_type, details, risk_level="medium", timeout=None, blocking=True):
    """
    High-level function to request approval

    Args:
        action_type (str): Type of action
        details (dict): Action details
        risk_level (str): Risk level
        timeout (int): Timeout in seconds
        blocking (bool): Wait for decision if True

    Returns:
        dict: Approval result
    """
    approver = ApprovalRequest()

    # Create approval request
    request = approver.create_approval_file(action_type, details, risk_level, timeout)

    if not blocking:
        # Return immediately
        return {
            "status": "pending",
            "request_id": request["request_id"],
            "filepath": request["filepath"]
        }

    # Wait for decision
    result = approver.wait_for_approval(
        request["filepath"],
        request["timeout"],
        request["request_id"]
    )

    result["request_id"] = request["request_id"]
    result["action_type"] = action_type
    result["details"] = details

    return result


def main():
    """CLI interface"""
    approver = ApprovalRequest()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--create":
            # Parse arguments
            action_type = None
            params = {}
            timeout = None

            for i in range(2, len(sys.argv)):
                if sys.argv[i] == "--action" and i + 1 < len(sys.argv):
                    action_type = sys.argv[i + 1]
                elif sys.argv[i] == "--params" and i + 1 < len(sys.argv):
                    params = json.loads(sys.argv[i + 1])
                elif sys.argv[i] == "--timeout" and i + 1 < len(sys.argv):
                    timeout = int(sys.argv[i + 1])

            if not action_type:
                print("Error: --action required")
                return

            request = approver.create_approval_file(action_type, params, timeout=timeout)
            print(f"\nApproval request created:")
            print(f"  Request ID: {request['request_id']}")
            print(f"  File: {request['filename']}")
            print(f"  Timeout: {request['timeout']} seconds")

        elif command == "--list-pending":
            pending = approver.list_pending()

            if not pending:
                print("No pending approvals")
            else:
                print(f"\n{len(pending)} Pending Approval(s):\n")
                for item in pending:
                    print(f"  [{item['request_id']}] {item['file']}")
                    print(f"      Created: {item['created']} ({item['age_minutes']} minutes ago)")
                print()

        elif command == "--status":
            if len(sys.argv) < 3:
                print("Usage: python request_approval.py --status <request_id>")
                return

            request_id = sys.argv[2]
            status = approver.get_status(request_id)

            print(f"\nRequest ID: {request_id}")
            print(f"Status: {status['status'].upper()}")
            if status['file']:
                print(f"File: {status['file']}")

        elif command == "--approve":
            if len(sys.argv) < 3:
                print("Usage: python request_approval.py --approve <request_id>")
                return

            request_id = sys.argv[2]
            pattern = f"approval_*_{request_id}.md"

            found = False
            for filepath in approver.needs_approval.glob(pattern):
                with open(filepath, "a", encoding="utf-8") as f:
                    f.write("\n\nDECISION: APPROVED\n")

                print(f"Approved: {filepath.name}")
                found = True
                break

            if not found:
                print(f"Request not found: {request_id}")

        elif command == "--reject":
            if len(sys.argv) < 3:
                print("Usage: python request_approval.py --reject <request_id> --reason 'reason'")
                return

            request_id = sys.argv[2]
            reason = "No reason provided"

            for i in range(3, len(sys.argv)):
                if sys.argv[i] == "--reason" and i + 1 < len(sys.argv):
                    reason = sys.argv[i + 1]

            pattern = f"approval_*_{request_id}.md"

            found = False
            for filepath in approver.needs_approval.glob(pattern):
                with open(filepath, "a", encoding="utf-8") as f:
                    f.write(f"\n\nDECISION: REJECTED\nReason: {reason}\n")

                print(f"Rejected: {filepath.name}")
                print(f"Reason: {reason}")
                found = True
                break

            if not found:
                print(f"Request not found: {request_id}")

        elif command == "--cleanup":
            hours = 24

            for i in range(2, len(sys.argv)):
                if sys.argv[i] == "--older-than" and i + 1 < len(sys.argv):
                    hours_str = sys.argv[i + 1].rstrip('h')
                    hours = int(hours_str)

            cleaned = approver.cleanup_old(hours)
            print(f"Cleaned up {cleaned} old file(s)")

        elif command == "--test":
            print("Creating test approval request...")

            result = request_approval(
                action_type="send_email",
                details={
                    "to": "test@example.com",
                    "subject": "Test Email",
                    "body": "This is a test email for approval workflow"
                },
                risk_level="low",
                timeout=60,  # 1 minute for testing
                blocking=False
            )

            print(f"\nTest request created:")
            print(f"  Request ID: {result['request_id']}")
            print(f"\nNext steps:")
            print(f"1. Edit the file and add: DECISION: APPROVED")
            print(f"2. Or wait 60 seconds for timeout")
            print(f"3. Check status: python request_approval.py --status {result['request_id']}")

        else:
            print(f"Unknown command: {command}")
            print("Use: --create, --list-pending, --status, --approve, --reject, --cleanup, or --test")

    else:
        print("""
Human Approval Agent Skill (Silver Tier)

Usage:
  python request_approval.py --create --action "send_email" --params '{...}' [--timeout 3600]
  python request_approval.py --list-pending
  python request_approval.py --status <request_id>
  python request_approval.py --approve <request_id>
  python request_approval.py --reject <request_id> --reason "reason"
  python request_approval.py --cleanup [--older-than 24h]
  python request_approval.py --test

Examples:
  # Create approval request
  python request_approval.py --create --action "send_email" --params '{"to":"test@example.com"}'

  # List pending
  python request_approval.py --list-pending

  # Check status
  python request_approval.py --status a1b2c3

  # Manual approve (for testing)
  python request_approval.py --approve a1b2c3

  # Test
  python request_approval.py --test
        """)


if __name__ == "__main__":
    main()
