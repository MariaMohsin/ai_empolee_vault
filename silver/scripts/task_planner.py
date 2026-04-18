#!/usr/bin/env python3
"""
Task Planner - Agent Skill (Silver Tier)
Reads inbox files, generates step-by-step execution plans

Usage:
    python task_planner.py --run              # Process all inbox files
    python task_planner.py --file "path"      # Process specific file
    python task_planner.py --test             # Run test
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
import sys


class TaskPlanner:
    """
    Agent Skill: Task Planner
    Analyzes tasks and generates execution plans
    """

    def __init__(self, root_path=None):
        if root_path is None:
            self.root = Path(__file__).parent.parent
        else:
            self.root = Path(root_path)

        # Paths
        self.inbox = self.root / "AI_Employee_Vault" / "Inbox"
        self.needs_action = self.root / "AI_Employee_Vault" / "Needs_Action"
        self.done = self.root / "Done"
        self.logs_dir = self.root / "logs"
        self.action_log = self.logs_dir / "action.log"
        self.processed_log = self.logs_dir / "processed_files.json"

        self._ensure_directories()

    def _ensure_directories(self):
        """Create required directories"""
        for directory in [self.inbox, self.needs_action, self.done, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def log(self, level, message):
        """Write to action log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}\n"

        with open(self.action_log, "a", encoding="utf-8") as f:
            f.write(entry)

        print(entry.strip())

    def calculate_file_hash(self, filepath):
        """Calculate MD5 hash of file content"""
        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            self.log("ERROR", f"Failed to hash {filepath.name}: {e}")
            return None

    def is_already_processed(self, filename, file_hash):
        """Check if file was already processed"""
        if not self.processed_log.exists():
            return False

        try:
            with open(self.processed_log, "r") as f:
                data = json.load(f)

            for entry in data.get("processed_files", []):
                if entry["filename"] == filename or entry.get("hash") == file_hash:
                    return True

            return False

        except Exception:
            return False

    def mark_as_processed(self, filename, file_hash, plan_filename):
        """Mark file as processed in log"""
        data = {"processed_files": []}

        if self.processed_log.exists():
            try:
                with open(self.processed_log, "r") as f:
                    data = json.load(f)
            except:
                pass

        entry = {
            "filename": filename,
            "hash": file_hash,
            "processed_at": datetime.now().isoformat(),
            "plan_created": plan_filename
        }

        data["processed_files"].append(entry)

        with open(self.processed_log, "w") as f:
            json.dump(data, f, indent=2)

    def read_file_content(self, filepath):
        """Read and return file content"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.log("ERROR", f"Failed to read {filepath.name}: {e}")
            return None

    def analyze_task(self, content, filename):
        """
        Analyze task content and extract key information

        Returns:
            dict: Analysis results
        """
        content_lower = content.lower()

        # Detect task type
        task_type = "general"
        if "research" in content_lower:
            task_type = "research"
        elif "email" in content_lower:
            task_type = "communication"
        elif "analyze" in content_lower or "analysis" in content_lower:
            task_type = "analysis"
        elif "create" in content_lower or "build" in content_lower:
            task_type = "creation"
        elif "post" in content_lower or "linkedin" in content_lower:
            task_type = "social_media"

        # Detect priority
        priority = "medium"
        if any(kw in content_lower for kw in ["urgent", "asap", "critical", "immediately"]):
            priority = "high"
        elif any(kw in content_lower for kw in ["when possible", "low priority", "someday"]):
            priority = "low"

        # Estimate complexity
        word_count = len(content.split())
        if word_count < 50:
            complexity = "simple"
            estimated_time = "15-30 minutes"
        elif word_count < 200:
            complexity = "moderate"
            estimated_time = "30-60 minutes"
        else:
            complexity = "complex"
            estimated_time = "1-3 hours"

        # Check if needs approval
        approval_keywords = [
            "send email", "post to", "publish", "delete", "purchase",
            "payment", "external", "api call"
        ]
        needs_approval = any(kw in content_lower for kw in approval_keywords)

        # Extract title
        lines = content.split("\n")
        title = "Untitled Task"
        for line in lines:
            if line.strip().startswith("#"):
                title = line.strip().lstrip("#").strip()
                break

        return {
            "title": title,
            "type": task_type,
            "priority": priority,
            "complexity": complexity,
            "estimated_time": estimated_time,
            "needs_approval": needs_approval,
            "word_count": word_count
        }

    def generate_steps(self, analysis, content):
        """
        Generate step-by-step execution plan based on task type

        Returns:
            list: List of steps (dicts)
        """
        task_type = analysis["type"]
        steps = []

        if task_type == "research":
            steps = [
                {
                    "name": "Define Research Scope",
                    "description": "Clarify what needs to be researched and why",
                    "time": "10 minutes",
                    "dependencies": None
                },
                {
                    "name": "Gather Information",
                    "description": "Collect relevant data from reliable sources",
                    "time": "30-45 minutes",
                    "dependencies": "Step 1"
                },
                {
                    "name": "Analyze Findings",
                    "description": "Review and synthesize collected information",
                    "time": "20 minutes",
                    "dependencies": "Step 2"
                },
                {
                    "name": "Create Summary",
                    "description": "Compile findings into clear, actionable summary",
                    "time": "15 minutes",
                    "dependencies": "Step 3"
                }
            ]

        elif task_type == "communication":
            steps = [
                {
                    "name": "Draft Message",
                    "description": "Write initial draft of communication",
                    "time": "10 minutes",
                    "dependencies": None
                },
                {
                    "name": "Review & Edit",
                    "description": "Check tone, clarity, and accuracy",
                    "time": "5 minutes",
                    "dependencies": "Step 1"
                },
                {
                    "name": "Get Approval",
                    "description": "Submit for manager review if required",
                    "time": "Variable",
                    "dependencies": "Step 2"
                },
                {
                    "name": "Send/Publish",
                    "description": "Execute the communication",
                    "time": "2 minutes",
                    "dependencies": "Step 3"
                }
            ]

        elif task_type == "analysis":
            steps = [
                {
                    "name": "Understand Requirements",
                    "description": "Clarify what analysis is needed",
                    "time": "5 minutes",
                    "dependencies": None
                },
                {
                    "name": "Collect Data",
                    "description": "Gather necessary information or files",
                    "time": "15 minutes",
                    "dependencies": "Step 1"
                },
                {
                    "name": "Perform Analysis",
                    "description": "Execute analytical work",
                    "time": "30 minutes",
                    "dependencies": "Step 2"
                },
                {
                    "name": "Document Results",
                    "description": "Create clear documentation of findings",
                    "time": "15 minutes",
                    "dependencies": "Step 3"
                }
            ]

        else:  # General task
            steps = [
                {
                    "name": "Review Task Requirements",
                    "description": "Understand what needs to be done",
                    "time": "5 minutes",
                    "dependencies": None
                },
                {
                    "name": "Plan Approach",
                    "description": "Determine best way to complete task",
                    "time": "10 minutes",
                    "dependencies": "Step 1"
                },
                {
                    "name": "Execute Task",
                    "description": "Complete the main work",
                    "time": "Variable",
                    "dependencies": "Step 2"
                },
                {
                    "name": "Verify & Complete",
                    "description": "Check work and mark as done",
                    "time": "5 minutes",
                    "dependencies": "Step 3"
                }
            ]

        return steps

    def generate_plan(self, filepath, content, analysis):
        """
        Generate complete execution plan in markdown format

        Returns:
            str: Plan content in markdown
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        steps = self.generate_steps(analysis, content)

        # Priority emoji
        priority_emoji = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢"
        }[analysis["priority"]]

        plan = f"""# Execution Plan: {analysis['title']}

**Generated:** {timestamp}
**Source File:** {filepath.name}
**Priority:** {priority_emoji} {analysis['priority'].title()}
**Task Type:** {analysis['type'].replace('_', ' ').title()}
**Complexity:** {analysis['complexity'].title()}
**Estimated Time:** {analysis['estimated_time']}
**Requires Approval:** {'Yes ⚠️' if analysis['needs_approval'] else 'No ✅'}

---

## Summary

{self._generate_summary(content, analysis)}

---

## Step-by-Step Execution

"""

        # Add steps
        for i, step in enumerate(steps, 1):
            plan += f"""### Step {i}: {step['name']}
- **Description:** {step['description']}
- **Dependencies:** {step['dependencies'] or 'None'}
- **Estimated Time:** {step['time']}

"""

        # Add success criteria
        plan += """---

## Success Criteria

- [ ] All steps completed as planned
- [ ] Output meets requirements
- [ ] Quality standards met
- [ ] Task documented properly

---

## Resources Needed

- Access to required tools/systems
- Relevant documentation or reference materials
"""

        if analysis['needs_approval']:
            plan += "- Manager approval for execution\n"

        plan += """
---

## Risks & Mitigation

"""

        # Add risk assessment based on task type
        if analysis['type'] == 'communication':
            plan += """- **Risk:** Message could be misinterpreted
  - **Mitigation:** Have draft reviewed before sending

- **Risk:** Wrong recipient
  - **Mitigation:** Double-check recipient list
"""

        elif analysis['complexity'] == 'complex':
            plan += """- **Risk:** Task more complex than estimated
  - **Mitigation:** Break into smaller subtasks if needed

- **Risk:** Missing information
  - **Mitigation:** Escalate to manager for clarification
"""

        else:
            plan += """- **Risk:** Minimal (straightforward task)
  - **Mitigation:** Standard quality checks apply
"""

        plan += f"""
---

**Status:** Ready for Execution
**Next Action:** {'Submit for approval' if analysis['needs_approval'] else 'Begin Step 1'}
**Created by:** AI Employee Task Planner (Silver Tier)
"""

        return plan

    def _generate_summary(self, content, analysis):
        """Generate 2-3 sentence summary of task"""
        # Extract first few meaningful lines
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]

        if lines:
            first_lines = " ".join(lines[:3])
            if len(first_lines) > 300:
                first_lines = first_lines[:297] + "..."
            return first_lines
        else:
            return f"This is a {analysis['type']} task with {analysis['priority']} priority."

    def process_file(self, filepath):
        """
        Process a single file: analyze and generate plan

        Returns:
            dict: Result with success status
        """
        filename = filepath.name
        self.log("TASK_PLANNER", f"Processing file: {filename}")

        # Calculate hash
        file_hash = self.calculate_file_hash(filepath)
        if not file_hash:
            return {"success": False, "error": "Failed to hash file"}

        # Check if already processed (idempotency)
        if self.is_already_processed(filename, file_hash):
            self.log("SKIP", f"File already processed: {filename}")
            return {"success": False, "skipped": True, "reason": "Already processed"}

        # Read content
        content = self.read_file_content(filepath)
        if not content:
            return {"success": False, "error": "Failed to read file"}

        self.log("READ", f"Read {len(content)} characters from {filename}")

        # Analyze task
        analysis = self.analyze_task(content, filename)
        self.log("ANALYZE",
            f"Type: {analysis['type']}, Priority: {analysis['priority']}, "
            f"Approval: {analysis['needs_approval']}")

        # Generate plan
        plan_content = self.generate_plan(filepath, content, analysis)

        # Save plan
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plan_filename = f"plan_{timestamp}.md"
        plan_path = self.needs_action / plan_filename

        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(plan_content)

        self.log("GENERATE", f"Created plan: {plan_filename}")

        # Move original to Done (using simple move)
        dest_path = self.done / filename
        filepath.rename(dest_path)
        self.log("ARCHIVE", f"Moved {filename} to Done")

        # Mark as processed
        self.mark_as_processed(filename, file_hash, plan_filename)
        self.log("COMPLETE", f"Processing complete for {filename}")

        return {
            "success": True,
            "source_file": filename,
            "plan_file": plan_filename,
            "analysis": analysis
        }

    def process_inbox(self):
        """
        Process all files in inbox

        Returns:
            dict: Results summary
        """
        self.log("START", "Task Planner started")

        if not self.inbox.exists():
            self.log("ERROR", f"Inbox not found: {self.inbox}")
            return {"success": False, "error": "Inbox not found"}

        # Get all .md files in inbox
        files = list(self.inbox.glob("*.md"))

        if not files:
            self.log("IDLE", "No files in inbox")
            return {"success": True, "files_processed": 0, "message": "No files to process"}

        self.log("SCAN", f"Found {len(files)} file(s) in inbox")

        results = []
        for filepath in files:
            result = self.process_file(filepath)
            results.append(result)

        successful = sum(1 for r in results if r.get("success"))
        skipped = sum(1 for r in results if r.get("skipped"))

        self.log("SUMMARY",
            f"Processed {successful} file(s), Skipped {skipped}, Total {len(files)}")

        return {
            "success": True,
            "files_processed": successful,
            "files_skipped": skipped,
            "total_files": len(files),
            "results": results
        }

    def run_test(self):
        """Create and process a test file"""
        self.log("TEST", "Creating test file...")

        test_content = f"""# Test Task for Task Planner

**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Objective

This is a test task to verify the task planner agent skill is working correctly.

## Requirements

- Analyze this test file
- Generate a step-by-step execution plan
- Move this file to Done
- Log all actions

## Expected Behavior

The task planner should:
1. Read this file from Inbox
2. Classify it as a test/general task
3. Generate a plan with multiple steps
4. Save the plan to Needs_Action
5. Archive this file to Done
6. Not process this file again (idempotency)

---

**Test ID:** test_{datetime.now().strftime("%Y%m%d_%H%M%S")}
**Status:** Awaiting Processing
"""

        test_file = self.inbox / f"test_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        self.log("TEST", f"Created test file: {test_file.name}")
        self.log("TEST", "Processing test file...")

        result = self.process_inbox()

        self.log("TEST", "Test complete! Check:")
        self.log("TEST", f"  - Needs_Action/ for generated plan")
        self.log("TEST", f"  - Done/ for original test file")
        self.log("TEST", f"  - logs/action.log for activity")

        return result


def main():
    """CLI interface"""
    planner = TaskPlanner()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--run":
            print("Running task planner...")
            result = planner.process_inbox()
            print(f"\nResult: {result}")

        elif command == "--file":
            if len(sys.argv) < 3:
                print("Usage: python task_planner.py --file <filepath>")
                return

            filepath = Path(sys.argv[2])
            if not filepath.exists():
                print(f"File not found: {filepath}")
                return

            print(f"Processing file: {filepath}")
            result = planner.process_file(filepath)
            print(f"\nResult: {result}")

        elif command == "--test":
            print("Running test...")
            result = planner.run_test()
            print(f"\nTest result: {result}")

        else:
            print(f"Unknown command: {command}")
            print("Use: --run, --file <path>, or --test")

    else:
        print("""
Task Planner - Agent Skill (Silver Tier)

Usage:
  python task_planner.py --run              # Process all inbox files
  python task_planner.py --file "path"      # Process specific file
  python task_planner.py --test             # Run test

Examples:
  python task_planner.py --run
  python task_planner.py --file "Inbox/my_task.md"
  python task_planner.py --test
        """)


if __name__ == "__main__":
    main()
