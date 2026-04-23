"""
Task Executor - Executes approved tasks
"""

from pathlib import Path
from datetime import datetime


class TaskExecutor:
    """
    Executes tasks autonomously or after approval
    """

    def execute(self, task_file, approved=False):
        """
        Execute a task

        Args:
            task_file (Path): Path to task file
            approved (bool): Whether this is an approved action

        Returns:
            dict: Execution result with success status
        """
        try:
            # Read task
            with open(task_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Determine action type
            action_type = self._detect_action_type(content, task_file.name)

            # Execute based on type
            if action_type == "email":
                result = self._execute_email(content, approved)
            elif action_type == "linkedin_post":
                result = self._execute_linkedin(content, approved)
            elif action_type == "analysis":
                result = self._execute_analysis(content)
            else:
                result = self._execute_general(content)

            # Add completion note to file
            self._mark_complete(task_file, result)

            return {"success": True, "action": action_type, "result": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _detect_action_type(self, content, filename):
        """Detect what type of action this is"""
        content_lower = content.lower()
        filename_lower = filename.lower()

        if "email" in content_lower or "email" in filename_lower:
            return "email"
        elif "linkedin" in content_lower or "post" in filename_lower:
            return "linkedin_post"
        elif "analyze" in content_lower or "research" in content_lower:
            return "analysis"
        else:
            return "general"

    def _execute_email(self, content, approved):
        """Execute email sending (mock for now)"""
        if not approved:
            return "ERROR: Email sending requires approval"

        # Mock email sending
        return "✅ Email sent successfully (mock)"

    def _execute_linkedin(self, content, approved):
        """Execute LinkedIn posting (mock for now)"""
        if not approved:
            return "ERROR: LinkedIn posting requires approval"

        # Mock LinkedIn post
        return "✅ LinkedIn post published successfully (mock)"

    def _execute_analysis(self, content):
        """Execute analysis task"""
        # Simple analysis: count words, extract key info
        words = len(content.split())
        lines = len(content.split("\n"))

        analysis = f"""
**Analysis Complete**

- Word count: {words}
- Line count: {lines}
- Type: Analysis task
- Status: Processed
        """

        return analysis.strip()

    def _execute_general(self, content):
        """Execute general task"""
        return "✅ Task processed successfully"

    def _mark_complete(self, task_file, result):
        """Add completion marker to task file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        completion_note = f"""

---

## ✅ Completed by AI Employee

**Timestamp:** {timestamp}
**Result:**

{result}

---
"""

        with open(task_file, "a", encoding="utf-8") as f:
            f.write(completion_note)
