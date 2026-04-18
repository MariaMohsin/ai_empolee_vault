#!/usr/bin/env python3
"""
AI Employee - Silver Tier
Autonomous AI worker that processes tasks independently

Usage:
    python ai_employee.py --once    # Run one cycle
    python ai_employee.py --loop    # Run continuously
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.reasoning_engine import ReasoningEngine
from scripts.approval_manager import ApprovalManager
from scripts.task_executor import TaskExecutor
from scripts.logger import Logger


class AIEmployee:
    """
    Main AI Employee orchestrator
    Coordinates all Silver Tier capabilities
    """

    def __init__(self):
        self.root = Path(__file__).parent.parent
        self.inbox = self.root / "Inbox"
        self.needs_action = self.root / "Needs_Action"
        self.needs_approval = self.root / "Needs_Approval"
        self.done = self.root / "Done"
        self.plans = self.root / "Plans"

        # Initialize components
        self.reasoning = ReasoningEngine()
        self.approvals = ApprovalManager()
        self.executor = TaskExecutor()
        self.logger = Logger()

        self._ensure_folders()

    def _ensure_folders(self):
        """Create required folders"""
        for folder in [self.inbox, self.needs_action, self.needs_approval, self.done, self.plans]:
            folder.mkdir(parents=True, exist_ok=True)

    def run_cycle(self):
        """
        Run one complete work cycle
        This is the main "work loop" of the AI Employee
        """
        self.logger.log("CYCLE_START", "Starting work cycle")

        # Step 1: Process Inbox (classify new items)
        self.logger.log("STEP", "Processing inbox...")
        inbox_count = self._process_inbox()

        # Step 2: Generate Plans (reasoning loop)
        self.logger.log("STEP", "Generating execution plans...")
        plan_count = self._generate_plans()

        # Step 3: Execute Safe Tasks
        self.logger.log("STEP", "Executing autonomous tasks...")
        executed_count = self._execute_tasks()

        # Step 4: Check Approvals
        self.logger.log("STEP", "Checking for approved actions...")
        approval_count = self._process_approvals()

        # Step 5: Report
        self.logger.log("CYCLE_END",
            f"Cycle complete: {inbox_count} classified, {plan_count} plans, "
            f"{executed_count} executed, {approval_count} approvals processed"
        )

        return {
            "inbox_processed": inbox_count,
            "plans_generated": plan_count,
            "tasks_executed": executed_count,
            "approvals_processed": approval_count
        }

    def _process_inbox(self):
        """Process new items in inbox"""
        count = 0

        if not self.inbox.exists():
            return count

        for item in self.inbox.glob("*.md"):
            try:
                # Classify the item
                classification = self.reasoning.classify_task(item)

                # Route based on classification
                if classification.get("needs_approval"):
                    # Move to approval queue
                    dest = self.needs_approval / item.name
                    item.rename(dest)
                    self.logger.log("ROUTE", f"{item.name} → Needs_Approval (sensitive)")
                else:
                    # Move to action queue
                    dest = self.needs_action / item.name
                    item.rename(dest)
                    self.logger.log("ROUTE", f"{item.name} → Needs_Action (safe)")

                count += 1

            except Exception as e:
                self.logger.log("ERROR", f"Failed to process {item.name}: {e}")

        return count

    def _generate_plans(self):
        """Generate execution plans for tasks"""
        count = 0

        # Get all tasks in Needs_Action
        tasks = list(self.needs_action.glob("*.md"))

        if not tasks:
            return count

        # Generate a plan
        try:
            plan = self.reasoning.generate_plan(tasks)

            # Save plan
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plan_file = self.plans / f"plan_{timestamp}.md"

            with open(plan_file, "w", encoding="utf-8") as f:
                f.write(plan)

            self.logger.log("PLAN", f"Generated plan: {plan_file.name}")
            count = 1

        except Exception as e:
            self.logger.log("ERROR", f"Plan generation failed: {e}")

        return count

    def _execute_tasks(self):
        """Execute tasks autonomously"""
        count = 0

        tasks = list(self.needs_action.glob("*.md"))

        for task_file in tasks[:5]:  # Limit to 5 per cycle
            try:
                result = self.executor.execute(task_file)

                if result.get("success"):
                    # Move to Done
                    dest = self.done / task_file.name
                    task_file.rename(dest)
                    self.logger.log("EXECUTE", f"Completed: {task_file.name}")
                    count += 1
                else:
                    self.logger.log("ERROR", f"Execution failed: {task_file.name}")

            except Exception as e:
                self.logger.log("ERROR", f"Task execution error: {e}")

        return count

    def _process_approvals(self):
        """Process approved items"""
        count = 0

        approved_items = list(self.needs_approval.glob("*.md"))

        for item in approved_items:
            try:
                # Check if approved
                status = self.approvals.check_status(item)

                if status == "APPROVED":
                    # Execute the approved action
                    result = self.executor.execute(item, approved=True)

                    if result.get("success"):
                        # Move to Done
                        dest = self.done / item.name
                        item.rename(dest)
                        self.logger.log("APPROVED", f"Executed approved action: {item.name}")
                        count += 1

                elif status == "REJECTED":
                    # Archive rejected item
                    dest = self.done / f"rejected_{item.name}"
                    item.rename(dest)
                    self.logger.log("REJECTED", f"Archived rejected item: {item.name}")

            except Exception as e:
                self.logger.log("ERROR", f"Approval processing error: {e}")

        return count

    def run_loop(self, interval=300):
        """
        Run continuously with specified interval

        Args:
            interval (int): Seconds between cycles (default 5 minutes)
        """
        self.logger.log("START", f"AI Employee starting (interval: {interval}s)")

        try:
            while True:
                self.run_cycle()
                self.logger.log("SLEEP", f"Sleeping for {interval} seconds...")
                time.sleep(interval)

        except KeyboardInterrupt:
            self.logger.log("STOP", "AI Employee stopped by user")


def main():
    """Main entry point"""
    employee = AIEmployee()

    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == "--once":
            print("Running one cycle...")
            result = employee.run_cycle()
            print("\nResults:")
            for key, value in result.items():
                print(f"  {key}: {value}")

        elif mode == "--loop":
            print("Running continuously (Ctrl+C to stop)...")
            employee.run_loop(interval=300)  # 5 minutes

        else:
            print(f"Unknown mode: {mode}")
            print("Use: --once or --loop")
    else:
        print("AI Employee - Silver Tier")
        print("\nUsage:")
        print("  python ai_employee.py --once    # Run one cycle")
        print("  python ai_employee.py --loop    # Run continuously")


if __name__ == "__main__":
    main()
