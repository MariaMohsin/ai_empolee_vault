"""
Reasoning Engine - The "brain" of the AI Employee
Analyzes tasks, generates plans, makes decisions
"""

from pathlib import Path
from datetime import datetime


class ReasoningEngine:
    """
    Reasoning and planning system for AI Employee
    """

    def classify_task(self, task_file):
        """
        Classify a task file

        Args:
            task_file (Path): Path to task file

        Returns:
            dict: Classification with needs_approval flag
        """
        # Read file content
        try:
            with open(task_file, "r", encoding="utf-8") as f:
                content = f.read().lower()
        except:
            content = ""

        filename = task_file.name.lower()

        # Determine if needs approval
        sensitive_keywords = [
            "send email", "post to linkedin", "delete", "publish",
            "payment", "purchase", "external", "api call"
        ]

        needs_approval = any(keyword in content or keyword in filename
                            for keyword in sensitive_keywords)

        # Determine priority
        urgent_keywords = ["urgent", "asap", "critical", "immediately"]
        priority = "high" if any(kw in content for kw in urgent_keywords) else "medium"

        return {
            "filename": task_file.name,
            "needs_approval": needs_approval,
            "priority": priority,
            "category": self._detect_category(content, filename)
        }

    def _detect_category(self, content, filename):
        """Detect task category"""
        if "email" in content or "email" in filename:
            return "email"
        elif "linkedin" in content or "post" in filename:
            return "social_media"
        elif "research" in content:
            return "research"
        else:
            return "general"

    def generate_plan(self, task_files):
        """
        Generate an execution plan for multiple tasks

        Args:
            task_files (list): List of task file paths

        Returns:
            str: Plan in markdown format
        """
        plan = f"""# Execution Plan

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Tasks to Process:** {len(task_files)}

---

## Task Summary

"""

        # Analyze each task
        high_priority = []
        medium_priority = []
        low_priority = []

        for task_file in task_files:
            classification = self.classify_task(task_file)

            task_info = f"- **{task_file.name}** ({classification['category']})"

            if classification['priority'] == 'high':
                high_priority.append(task_info)
            elif classification['priority'] == 'medium':
                medium_priority.append(task_info)
            else:
                low_priority.append(task_info)

        # Add to plan
        if high_priority:
            plan += "### 🔴 High Priority\n"
            plan += "\n".join(high_priority) + "\n\n"

        if medium_priority:
            plan += "### 🟡 Medium Priority\n"
            plan += "\n".join(medium_priority) + "\n\n"

        if low_priority:
            plan += "### 🟢 Low Priority\n"
            plan += "\n".join(low_priority) + "\n\n"

        # Add execution strategy
        plan += """---

## Execution Strategy

### Phase 1: High Priority Tasks
Execute urgent items first to meet deadlines.

### Phase 2: Medium Priority Tasks
Process standard workflow items.

### Phase 3: Low Priority Tasks
Handle remaining items as time permits.

---

## Risk Assessment

- **Autonomous Execution:** Safe tasks will be executed automatically
- **Manager Approval:** Sensitive actions queued in /Needs_Approval
- **Error Handling:** Failed tasks will be logged and retried

---

## Next Actions

1. Execute high-priority autonomous tasks
2. Submit sensitive tasks for approval
3. Monitor execution and log results
4. Generate completion report

---

**Status:** Ready for Execution
"""

        return plan
