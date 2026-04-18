#!/usr/bin/env python3
"""
Gmail Watcher - Monitor Gmail inbox and convert emails to tasks

Usage:
    python watch_gmail.py --mock      # Mock mode (testing)
    python watch_gmail.py --once      # Check once
    python watch_gmail.py --api       # Real Gmail API (requires setup)
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
import sys
import time


class GmailWatcher:
    """
    Monitors Gmail inbox and converts emails to tasks
    """

    def __init__(self, root_path=None, mock_mode=True):
        if root_path is None:
            self.root = Path(__file__).parent.parent
        else:
            self.root = Path(root_path)

        self.mock_mode = mock_mode

        # Paths
        self.inbox = self.root / "AI_Employee_Vault" / "Inbox"
        self.logs_dir = self.root / "logs"
        self.action_log = self.logs_dir / "actions.log"
        self.processed_log = self.logs_dir / "processed_emails.json"

        self._ensure_directories()

    def _ensure_directories(self):
        """Create required directories"""
        for directory in [self.inbox, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def log(self, level, message):
        """Write to action log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}\n"

        with open(self.action_log, "a", encoding="utf-8") as f:
            f.write(entry)

        print(entry.strip())

    def is_email_processed(self, email_id):
        """Check if email already processed"""
        if not self.processed_log.exists():
            return False

        try:
            with open(self.processed_log, "r") as f:
                data = json.load(f)

            for entry in data.get("processed_emails", []):
                if entry["email_id"] == email_id:
                    return True

            return False

        except:
            return False

    def mark_email_processed(self, email_id, subject):
        """Mark email as processed"""
        data = {"processed_emails": []}

        if self.processed_log.exists():
            try:
                with open(self.processed_log, "r") as f:
                    data = json.load(f)
            except:
                pass

        entry = {
            "email_id": email_id,
            "subject": subject,
            "processed_at": datetime.now().isoformat()
        }

        data["processed_emails"].append(entry)

        with open(self.processed_log, "w") as f:
            json.dump(data, f, indent=2)

    def generate_mock_emails(self):
        """Generate mock emails for testing"""
        mock_emails = [
            {
                "id": "mock_001",
                "from": "client@example.com",
                "subject": "Project Status Update Needed",
                "body": "Hi,\n\nCan you provide an update on the project timeline?\nWe need this by end of week.\n\nThanks,\nJohn",
                "received": datetime.now().isoformat(),
                "labels": ["INBOX", "IMPORTANT"]
            },
            {
                "id": "mock_002",
                "from": "partner@business.com",
                "subject": "Partnership Opportunity",
                "body": "Hello,\n\nWe'd like to discuss a potential partnership.\nAre you available for a call this week?\n\nBest regards,\nSarah",
                "received": datetime.now().isoformat(),
                "labels": ["INBOX"]
            }
        ]

        return mock_emails

    def fetch_emails_api(self):
        """Fetch emails using Gmail API (placeholder)"""
        self.log("INFO", "Gmail API mode not yet implemented")
        self.log("INFO", "Falling back to mock mode for now")
        return self.generate_mock_emails()

    def fetch_emails(self):
        """Fetch emails (mock or real)"""
        if self.mock_mode:
            self.log("INFO", "Fetching emails (mock mode)")
            return self.generate_mock_emails()
        else:
            self.log("INFO", "Fetching emails (Gmail API)")
            return self.fetch_emails_api()

    def convert_email_to_task(self, email):
        """Convert email to task markdown"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        email_id = email["id"]
        filename = f"email_{timestamp}_{email_id}.md"

        # Classify priority
        priority = "medium"
        if "IMPORTANT" in email.get("labels", []):
            priority = "high"

        # Check for urgency keywords
        body_lower = email["body"].lower()
        if any(kw in body_lower for kw in ["urgent", "asap", "immediately"]):
            priority = "high"

        content = f"""# Email Task: {email['subject']}

```yaml
type: email_task
source: gmail
from: {email['from']}
subject: {email['subject']}
received: {email['received']}
email_id: {email['id']}
priority: {priority}
labels: {email.get('labels', [])}
```

## Email Content

**From:** {email['from']}
**Subject:** {email['subject']}
**Received:** {email['received']}

---

{email['body']}

---

## Suggested Actions

1. Read and understand the email content
2. Determine appropriate response
3. Draft reply if needed
4. Execute required actions

## Response Required
- [ ] Reply to {email['from']}
- [ ] Address the request/question
- [ ] Follow up as needed

---

**Status:** New Email Task
**Created by:** Gmail Watcher (Silver Tier)
"""

        return filename, content

    def process_emails(self):
        """Process all fetched emails"""
        self.log("GMAIL_WATCHER", "Starting Gmail check...")

        # Fetch emails
        emails = self.fetch_emails()

        if not emails:
            self.log("IDLE", "No new emails")
            return {"emails_processed": 0}

        self.log("SCAN", f"Found {len(emails)} email(s)")

        processed = 0

        for email in emails:
            email_id = email["id"]
            subject = email["subject"]

            # Check if already processed
            if self.is_email_processed(email_id):
                self.log("SKIP", f"Email already processed: {subject}")
                continue

            # Convert to task
            filename, content = self.convert_email_to_task(email)

            # Save to Inbox
            filepath = self.inbox / filename

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            self.log("CONVERT", f"Created task: {filename}")
            self.log("TASK", f"  From: {email['from']}")
            self.log("TASK", f"  Subject: {subject}")

            # Mark as processed
            self.mark_email_processed(email_id, subject)

            processed += 1

        self.log("COMPLETE", f"Processed {processed} email(s)")

        return {"emails_processed": processed}

    def run_once(self):
        """Run one check cycle"""
        return self.process_emails()

    def run_loop(self, interval=60):
        """Run continuously"""
        self.log("START", f"Gmail Watcher started (interval: {interval}s)")

        try:
            while True:
                self.process_emails()

                self.log("SLEEP", f"Sleeping {interval} seconds...")
                time.sleep(interval)

        except KeyboardInterrupt:
            self.log("STOP", "Gmail Watcher stopped by user")


def main():
    """CLI interface"""
    mock_mode = True
    run_once = False

    # Parse arguments
    for arg in sys.argv[1:]:
        if arg == "--api":
            mock_mode = False
        elif arg == "--mock":
            mock_mode = True
        elif arg == "--once":
            run_once = True

    watcher = GmailWatcher(mock_mode=mock_mode)

    if run_once:
        print("Running once...")
        result = watcher.run_once()
        print(f"\nResult: {result}")
    elif len(sys.argv) > 1:
        print(f"Starting Gmail Watcher ({'mock' if mock_mode else 'API'} mode)...")
        watcher.run_loop()
    else:
        print("""
Gmail Watcher - Email to Task Converter

Usage:
  python watch_gmail.py --mock      # Mock mode (testing)
  python watch_gmail.py --once      # Check once
  python watch_gmail.py --api       # Real Gmail API (requires setup)

Examples:
  # Test with mock emails
  python watch_gmail.py --mock --once

  # Run continuously (mock)
  python watch_gmail.py --mock
        """)


if __name__ == "__main__":
    main()
