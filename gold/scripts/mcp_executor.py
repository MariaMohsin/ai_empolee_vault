#!/usr/bin/env python3
"""
MCP Executor - External Action Execution with Approval Workflow
Executes external actions (Gmail, LinkedIn) with mandatory human approval

Usage:
    python mcp_executor.py --process-approvals    # Check and execute approved actions
    python mcp_executor.py --execute <file>       # Execute specific approved action
    python mcp_executor.py --health               # Check system health
"""

import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
import sys


class MCPExecutor:
    """
    MCP Executor: External action execution with approval workflow
    """

    def __init__(self, root_path=None, mock_mode=False):
        if root_path is None:
            self.root = Path(__file__).parent.parent
        else:
            self.root = Path(root_path)

        self.mock_mode = mock_mode

        # Vault paths
        self.vault = self.root / "AI_Employee_Vault"
        self.needs_approval = self.vault / "Needs_Approval"
        self.done = self.vault / "Done"
        self.logs_dir = self.root / "logs"
        self.action_log = self.logs_dir / "actions.log"
        self.config_file = self.root / "config" / "mcp_executor_config.json"

        # Skill script paths
        self.skills_root = self.root / ".claude" / "skills"

        # Stats
        self.stats = {
            "executed": 0,
            "failed": 0,
            "retries": 0,
            "blocked": 0
        }

        self._ensure_directories()
        self._load_config()

    def _ensure_directories(self):
        """Create required directories"""
        for directory in [self.needs_approval, self.done, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_config(self):
        """Load configuration"""
        self.config = {
            "retry": {
                "max_attempts": 3,
                "initial_delay": 1
            },
            "skills": {
                "gmail-send": {"enabled": True, "mock_mode": self.mock_mode},
                "linkedin-post": {"enabled": True, "mock_mode": self.mock_mode}
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

    def check_approval_status(self, approval_file):
        """
        Check if action has been approved

        Args:
            approval_file (Path): Path to approval file

        Returns:
            str: "APPROVED", "REJECTED", or "PENDING"
        """
        try:
            with open(approval_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for decision markers
            if "DECISION: APPROVED" in content:
                return "APPROVED"
            elif "DECISION: REJECTED" in content:
                return "REJECTED"
            else:
                return "PENDING"

        except Exception as e:
            self.log("ERROR", f"Failed to check approval: {e}")
            return "PENDING"

    def extract_action_params(self, approval_file):
        """Extract action parameters from approval file, stripping markdown formatting."""
        import re

        def clean(val):
            """Strip markdown bold/italic markers and extra whitespace."""
            return re.sub(r'\*+', '', val).strip()

        try:
            with open(approval_file, "r", encoding="utf-8") as f:
                raw_lines = f.readlines()

            params = {
                "action_type": None,
                "to": None,
                "subject": None,
                "body": None,
                "content": None
            }

            # Try YAML frontmatter block first (action_type, to, subject, body)
            in_yaml = False
            for line in raw_lines:
                stripped = line.strip()
                if stripped == "```yaml":
                    in_yaml = True
                    continue
                if in_yaml and stripped == "```":
                    in_yaml = False
                    continue
                if in_yaml and ":" in stripped:
                    key, _, val = stripped.partition(":")
                    key, val = key.strip(), val.strip()
                    if key == "action_type":
                        params["action_type"] = val
                    elif key == "to":
                        params["to"] = clean(val)
                    elif key == "subject":
                        params["subject"] = clean(val)

            # Parse markdown field lines: **To:** value  or  To: value
            for i, line in enumerate(raw_lines):
                low = line.lower().strip()

                if re.search(r'\*{0,2}to\*{0,2}\s*:', low):
                    val = clean(line.split(":", 1)[1]) if ":" in line else ""
                    if val and "@" in val:  # only set if looks like an email
                        params["to"] = val
                        params["action_type"] = params["action_type"] or "send_email"

                elif re.search(r'\*{0,2}subject\*{0,2}\s*:', low):
                    val = clean(line.split(":", 1)[1]) if ":" in line else ""
                    if val:
                        params["subject"] = val

                elif re.search(r'\*{0,2}body\*{0,2}\s*:', low):
                    body_lines = []
                    for j in range(i + 1, min(i + 15, len(raw_lines))):
                        ln = raw_lines[j].strip()
                        if ln and not ln.startswith("**") and not ln.startswith("---") and not ln.startswith("DECISION"):
                            body_lines.append(ln)
                        elif not ln:
                            break
                    if body_lines:
                        params["body"] = " ".join(body_lines)

                elif re.search(r'\*{0,2}content\*{0,2}\s*:', low) or "post content:" in low:
                    # Collect full multi-paragraph post — stop only at section separators
                    content_lines = []
                    for j in range(i + 1, min(i + 80, len(raw_lines))):
                        ln = raw_lines[j].rstrip()
                        if ln.strip().startswith("---") or ln.strip().startswith("DECISION") \
                                or ln.strip().startswith("## Manager") \
                                or ln.strip().startswith("To APPROVE") \
                                or ln.strip().startswith("To REJECT"):
                            break
                        content_lines.append(ln)
                    # Strip leading/trailing blank lines
                    content_text = "\n".join(content_lines).strip()
                    if content_text:
                        params["content"] = content_text
                        params["action_type"] = params["action_type"] or "linkedin_post"

                elif "linkedin" in low:
                    params["action_type"] = params["action_type"] or "linkedin_post"

            # Fallback: detect from filename
            filename = approval_file.name.lower()
            if not params["action_type"]:
                if "email" in filename:
                    params["action_type"] = "send_email"
                elif "linkedin" in filename or "post" in filename:
                    params["action_type"] = "linkedin_post"

            return params

        except Exception as e:
            self.log("ERROR", f"Failed to extract params: {e}")
            return {}

    def execute_gmail_send(self, params):
        """
        Execute Gmail send via production skill script.
        Requires EMAIL_ADDRESS and EMAIL_PASSWORD environment variables.
        """
        to = (params.get("to") or "").strip()
        subject = (params.get("subject") or "").strip()
        body = (params.get("body") or "").strip()

        if not to or not subject:
            return {"success": False, "error": "Missing required fields: to, subject"}

        self.log("EXECUTE", f"gmail-send: sending to {to}")

        skill_script = self.skills_root / "gmail-send" / "scripts" / "send_email.py"
        if not skill_script.exists():
            return {"success": False, "error": f"Skill script not found: {skill_script}"}

        cmd = [sys.executable, str(skill_script),
               "--to", to, "--subject", subject, "--body", body or "(no body)"]

        cc = params.get("cc", "").strip()
        if cc:
            cmd += ["--cc", cc]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            output = result.stdout.strip() or result.stderr.strip()
            self.log("SKILL_OUTPUT", output)

            if result.returncode == 0:
                return {"success": True, "message": output}
            else:
                return {"success": False, "error": output}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "gmail-send timed out after 30s"}
        except Exception as e:
            self.log("ERROR", f"gmail-send failed: {e}")
            return {"success": False, "error": str(e)}

    def execute_linkedin_post(self, params):
        """
        Execute LinkedIn post via production Playwright skill script.
        Requires LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables.
        """
        content = (params.get("content") or "").strip()
        if not content:
            return {"success": False, "error": "Missing required field: content"}

        self.log("EXECUTE", f"linkedin-post: posting content ({len(content)} chars)")

        skill_script = self.skills_root / "linkedin-post" / "scripts" / "post_linkedin.py"
        if not skill_script.exists():
            return {"success": False, "error": f"Skill script not found: {skill_script}"}

        cmd = [sys.executable, str(skill_script), "--content", content, "--headless", "True"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = result.stdout.strip() or result.stderr.strip()
            self.log("SKILL_OUTPUT", output)

            if result.returncode == 0:
                return {"success": True, "message": output}
            else:
                return {"success": False, "error": output}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "linkedin-post timed out after 60s"}
        except Exception as e:
            self.log("ERROR", f"linkedin-post failed: {e}")
            return {"success": False, "error": str(e)}

    def move_task(self, filename, from_folder, to_folder):
        """Move a task file using the vault-file-manager skill."""
        skill_script = self.skills_root / "vault-file-manager" / "scripts" / "move_task.py"
        if not skill_script.exists():
            self.log("WARNING", f"vault-file-manager skill not found — skipping move of {filename}")
            return False

        cmd = [sys.executable, str(skill_script),
               "--file", filename, "--from", from_folder, "--to", to_folder]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.log("MOVE", result.stdout.strip() or result.stderr.strip())
            return result.returncode == 0
        except Exception as e:
            self.log("ERROR", f"move_task failed: {e}")
            return False

    def execute_action(self, action_type, params):
        """
        Route and execute action

        Args:
            action_type (str): Type of action
            params (dict): Action parameters

        Returns:
            dict: Execution result
        """
        if action_type == "send_email":
            return self.execute_gmail_send(params)
        elif action_type == "linkedin_post":
            return self.execute_linkedin_post(params)
        else:
            self.log("ERROR", f"Unknown action type: {action_type}")
            return {"success": False, "error": "Unknown action type"}

    def execute_with_retry(self, action_type, params):
        """
        Execute action with retry logic

        Returns:
            dict: Execution result
        """
        max_attempts = self.config["retry"]["max_attempts"]
        initial_delay = self.config["retry"]["initial_delay"]

        for attempt in range(max_attempts):
            self.log("ATTEMPT", f"Execution attempt {attempt + 1}/{max_attempts}")

            try:
                result = self.execute_action(action_type, params)

                if result.get("success"):
                    if attempt > 0:
                        self.stats["retries"] += attempt
                    return result
                else:
                    # Check if error is retryable
                    error = result.get("error", "")
                    if "permanent" in error.lower() or "invalid" in error.lower():
                        self.log("ERROR", "Permanent error - not retrying")
                        return result

                    # Wait before retry
                    if attempt < max_attempts - 1:
                        wait_time = initial_delay * (2 ** attempt)
                        self.log("RETRY", f"Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)

            except Exception as e:
                self.log("ERROR", f"Execution error: {e}")
                if attempt < max_attempts - 1:
                    wait_time = initial_delay * (2 ** attempt)
                    time.sleep(wait_time)

        self.log("FAILED", f"All {max_attempts} attempts exhausted")
        return {"success": False, "error": "Max retries exceeded"}

    def execute_approved_action(self, approval_file):
        """
        Execute a single approved action

        Args:
            approval_file (Path): Path to approval file

        Returns:
            dict: Execution result
        """
        filename = approval_file.name
        self.log("MCP_EXECUTOR", f"Processing: {filename}")

        # Step 1: Check approval status
        status = self.check_approval_status(approval_file)
        self.log("APPROVAL_CHECK", f"Status: {status}")

        if status == "PENDING":
            self.log("BLOCKED", "Execution blocked - awaiting approval")
            self.stats["blocked"] += 1
            return {"success": False, "blocked": True, "reason": "Awaiting approval"}

        elif status == "REJECTED":
            self.log("REJECTED", "Action rejected by manager")
            dest = self.done / f"rejected_{filename}"
            try:
                approval_file.rename(dest)
            except Exception:
                pass
            return {"success": False, "rejected": True, "reason": "Rejected by manager"}

        elif status == "APPROVED":
            self.log("APPROVED", "Action approved by manager")

            # Step 2: Extract parameters
            params = self.extract_action_params(approval_file)
            action_type = params.get("action_type")

            if not action_type:
                self.log("ERROR", "Could not determine action type")
                return {"success": False, "error": "Unknown action type"}

            self.log("PARAMS", f"Action type: {action_type}")

            # Step 3: Execute with retry
            result = self.execute_with_retry(action_type, params)

            # Step 4: Move to Done via vault-file-manager skill
            if result.get("success"):
                self.log("SUCCESS", f"Action completed: {filename}")
                self.stats["executed"] += 1
                moved = self.move_task(filename, "Needs_Approval", "Done")
                if not moved:
                    # Fallback: rename directly
                    try:
                        approval_file.rename(self.done / f"executed_{filename}")
                    except Exception:
                        pass
                return result
            else:
                self.log("FAILED", f"Action failed: {result.get('error')}")
                self.stats["failed"] += 1
                return result

        else:
            self.log("ERROR", f"Unknown approval status: {status}")
            return {"success": False, "error": "Unknown status"}

    def process_approved_actions(self):
        """
        Scan Needs_Approval folder and execute approved actions

        Returns:
            dict: Processing summary
        """
        self.log("START", "MCP Executor: Processing approved actions")

        if not self.needs_approval.exists():
            self.log("ERROR", f"Needs_Approval folder not found")
            return {"success": False, "error": "Folder not found"}

        # Get all files in Needs_Approval
        files = list(self.needs_approval.glob("*.md"))

        if not files:
            self.log("IDLE", "No pending approvals")
            return {"success": True, "message": "No pending approvals"}

        self.log("SCAN", f"Found {len(files)} file(s) in Needs_Approval")

        results = []
        for approval_file in files:
            result = self.execute_approved_action(approval_file)
            results.append({
                "file": approval_file.name,
                "result": result
            })

        # Log summary
        self.log("SUMMARY",
            f"Executed: {self.stats['executed']}, "
            f"Failed: {self.stats['failed']}, "
            f"Blocked: {self.stats['blocked']}, "
            f"Retries: {self.stats['retries']}")

        return {
            "success": True,
            "stats": self.stats,
            "results": results
        }

    def health_check(self):
        """Check system health"""
        print("\n" + "="*60)
        print("  MCP EXECUTOR HEALTH CHECK")
        print("="*60 + "\n")

        # Check folders
        print("Folders:")
        print(f"  Needs_Approval: {'[OK]' if self.needs_approval.exists() else '[MISSING]'}")
        print(f"  Done: {'[OK]' if self.done.exists() else '[MISSING]'}")
        print(f"  Logs: {'[OK]' if self.logs_dir.exists() else '[MISSING]'}")

        # Check pending approvals
        if self.needs_approval.exists():
            pending = list(self.needs_approval.glob("*.md"))
            print(f"\nPending Approvals: {len(pending)}")
            if pending:
                for f in pending[:5]:
                    status = self.check_approval_status(f)
                    print(f"  - {f.name}: {status}")
                if len(pending) > 5:
                    print(f"  ... and {len(pending) - 5} more")

        # Check skills
        print("\nSkills:")
        for skill, config in self.config.get("skills", {}).items():
            enabled = config.get("enabled", False)
            mock = config.get("mock_mode", False)
            status = "[OK]" if enabled else "[DISABLED]"
            mode = "(mock mode)" if mock else "(real mode)"
            print(f"  {skill}: {status} {mode}")

        print("\n" + "="*60 + "\n")

    def create_test_approval(self):
        """Create a test approval request"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_email_{timestamp}.md"
        filepath = self.needs_approval / filename

        content = f"""# Approval Request: Test Email

**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Action Type:** Send Email
**Status:** Pending Manager Review

---

## Action Details

**To:** test@example.com
**Subject:** Test Email from MCP Executor
**Body:** This is a test email to verify the MCP Executor approval workflow is working correctly.

---

## Manager Decision Required

Please review the above action and add your decision below:

**To APPROVE, add this line:**
```
DECISION: APPROVED
```

**To REJECT, add this line:**
```
DECISION: REJECTED
Reason: [your reason here]
```

---

**Awaiting Decision...**
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        self.log("TEST", f"Created test approval: {filename}")
        print(f"\nTest approval created: {filepath}")
        print(f"\nNext steps:")
        print(f"1. Edit the file and add: DECISION: APPROVED")
        print(f"2. Run: python mcp_executor.py --execute \"{filepath}\"")

        return filepath


def main():
    """CLI interface"""
    executor = MCPExecutor(mock_mode=False)  # Real mode — skills handle their own errors

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--process-approvals":
            print("Processing approved actions...")
            result = executor.process_approved_actions()
            print(f"\nResult: {result}")

        elif command == "--execute":
            if len(sys.argv) < 3:
                print("Usage: python mcp_executor.py --execute <filepath>")
                return

            filepath = Path(sys.argv[2])
            if not filepath.exists():
                print(f"File not found: {filepath}")
                return

            print(f"Executing: {filepath}")
            result = executor.execute_approved_action(filepath)
            print(f"\nResult: {result}")

        elif command == "--health":
            executor.health_check()

        elif command == "--create-test":
            executor.create_test_approval()

        else:
            print(f"Unknown command: {command}")
            print("Use: --process-approvals, --execute <file>, --health, or --create-test")

    else:
        print("""
MCP Executor - External Action Execution (Silver Tier)

Usage:
  python mcp_executor.py --process-approvals    # Check and execute approved actions
  python mcp_executor.py --execute <file>       # Execute specific approved action
  python mcp_executor.py --health               # Check system health
  python mcp_executor.py --create-test          # Create test approval

Examples:
  python mcp_executor.py --process-approvals
  python mcp_executor.py --execute "Needs_Approval/email_001.md"
  python mcp_executor.py --health
        """)


if __name__ == "__main__":
    main()
