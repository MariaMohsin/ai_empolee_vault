#!/usr/bin/env python3
"""
Human Approval - Production Implementation
Request and wait for human approval with timeout handling
"""

import argparse
import os
import sys
import time
from pathlib import Path
from datetime import datetime


def create_approval_request(action, details, risk_level, timeout):
    """
    Create approval request file

    Args:
        action: Action description
        details: Action details
        risk_level: Risk level (low/medium/high)
        timeout: Timeout in seconds

    Returns:
        Path: Path to created approval file
    """
    # Get vault base path
    script_dir = Path(__file__).parent
    vault_base = script_dir.parent.parent.parent.parent / "AI_Employee_Vault"
    approval_dir = vault_base / "Needs_Approval"
    approval_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"approval_{timestamp}.md"
    filepath = approval_dir / filename

    # Create approval content
    timeout_str = f"{timeout // 60} minutes" if timeout >= 60 else f"{timeout} seconds"
    content = f"""# Approval Request: {action}

**Risk Level:** {risk_level.upper()}
**Requested:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Timeout:** {timeout_str}

## Action Details

{details}

---

## Manager Decision Required

Add one of the following to this file:

**To Approve:**
```
DECISION: APPROVED
```

**To Reject:**
```
DECISION: REJECTED
Reason: [Your reason here]
```

**Status:** Awaiting Decision
"""

    # Write file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


def check_approval_decision(filepath):
    """
    Check if approval file contains decision

    Returns:
        dict: {"status": str, "reason": str or None}
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if "DECISION: APPROVED" in content:
            return {"status": "approved", "reason": None}

        if "DECISION: REJECTED" in content:
            # Extract reason
            lines = content.split("\n")
            reason = "No reason provided"
            for i, line in enumerate(lines):
                if "DECISION: REJECTED" in line:
                    if i + 1 < len(lines) and lines[i + 1].startswith("Reason:"):
                        reason = lines[i + 1].replace("Reason:", "").strip()
                    break
            return {"status": "rejected", "reason": reason}

        return {"status": "pending", "reason": None}

    except Exception:
        return {"status": "pending", "reason": None}


def wait_for_approval(filepath, timeout):
    """
    Wait for approval decision with timeout

    Args:
        filepath: Path to approval file
        timeout: Timeout in seconds

    Returns:
        dict: {"success": bool, "message": str, "status": str}
    """
    start_time = time.time()
    poll_interval = 10  # Check every 10 seconds

    while True:
        elapsed = time.time() - start_time

        # Check for timeout
        if elapsed >= timeout:
            # Rename file to indicate timeout
            timeout_path = filepath.parent / f"{filepath.name}.timeout"
            filepath.rename(timeout_path)

            return {
                "success": False,
                "message": f"Approval timeout after {timeout} seconds",
                "status": "timeout"
            }

        # Check for decision
        result = check_approval_decision(filepath)

        if result["status"] == "approved":
            # Rename file to indicate approval
            approved_path = filepath.parent / f"{filepath.name}.approved"
            filepath.rename(approved_path)

            return {
                "success": True,
                "message": "Action approved by manager",
                "status": "approved"
            }

        if result["status"] == "rejected":
            # Rename file to indicate rejection
            rejected_path = filepath.parent / f"{filepath.name}.rejected"
            filepath.rename(rejected_path)

            return {
                "success": False,
                "message": f"Action rejected: {result['reason']}",
                "status": "rejected"
            }

        # Still pending, wait and check again
        time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="Request human approval for action")
    parser.add_argument("--action", required=True, help="Action description")
    parser.add_argument("--details", required=True, help="Action details")
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Timeout in seconds (default: 3600 = 1 hour)"
    )
    parser.add_argument(
        "--risk",
        choices=["low", "medium", "high"],
        default="medium",
        help="Risk level (default: medium)"
    )

    args = parser.parse_args()

    # Create approval request
    filepath = create_approval_request(
        action=args.action,
        details=args.details,
        risk_level=args.risk,
        timeout=args.timeout
    )

    print(f"Approval request created: {filepath.name}")
    print(f"Waiting for decision (timeout: {args.timeout}s)...")

    # Wait for approval
    result = wait_for_approval(filepath, args.timeout)

    # Print result
    print(result["message"])

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
