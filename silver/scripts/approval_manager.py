"""
Approval Manager - Handles human approval workflow
"""

from pathlib import Path


class ApprovalManager:
    """
    Manages approval requests and decisions
    """

    def check_status(self, approval_file):
        """
        Check if an item has been approved or rejected

        Args:
            approval_file (Path): Path to approval file

        Returns:
            str: "APPROVED", "REJECTED", or "PENDING"
        """
        try:
            with open(approval_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for decision markers
            if "DECISION: APPROVED" in content or "APPROVED" in content.upper():
                return "APPROVED"
            elif "DECISION: REJECTED" in content or "REJECTED" in content.upper():
                return "REJECTED"
            else:
                return "PENDING"

        except Exception:
            return "PENDING"

    def create_approval_request(self, action_type, details, dest_folder):
        """
        Create an approval request file

        Args:
            action_type (str): Type of action (email, linkedin_post, etc.)
            details (str): Details of the action
            dest_folder (Path): Destination folder (Needs_Approval)

        Returns:
            Path: Path to created approval file
        """
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"approval_{action_type}_{timestamp}.md"
        filepath = dest_folder / filename

        content = f"""# Approval Request: {action_type}

**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Action Type:** {action_type}
**Status:** Pending Manager Review

---

## Action Details

{details}

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

        return filepath
