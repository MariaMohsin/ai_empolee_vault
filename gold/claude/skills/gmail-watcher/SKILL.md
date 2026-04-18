# Skill: Gmail Watcher

## Metadata
```yaml
name: gmail-watcher
type: watcher
tier: silver
status: active
version: 1.0.0
created: 2026-04-17
```

## Goal
Monitor Gmail inbox for new emails, convert them to structured tasks, and route to AI Employee Inbox for processing.

---

## Core Responsibilities

### 1. Email Monitoring
- Check Gmail inbox periodically
- Fetch unread emails
- Filter by labels/criteria
- Mark as processed

### 2. Email Conversion
- Convert email to structured markdown
- Extract: sender, subject, body, attachments
- Classify by urgency/importance
- Add metadata

### 3. Task Routing
- Save to AI_Employee_Vault/Inbox
- Trigger task planner
- Track processed emails
- Prevent duplicates

### 4. Integration Modes
- **API Mode**: Gmail API (production)
- **Mock Mode**: Simulated emails (testing)
- **IMAP Mode**: Direct IMAP access (alternative)

---

## Email → Task Conversion

### Input: Gmail Email
```
From: client@example.com
To: you@company.com
Subject: Project Status Update Needed
Date: 2026-04-17 10:30:00

Hi,

Can you provide an update on the project timeline?
We need this by end of week.

Thanks,
John
```

### Output: Task File
**File:** `AI_Employee_Vault/Inbox/email_20260417_103000_abc123.md`

```markdown
# Email Task: Project Status Update Needed

```yaml
type: email_task
source: gmail
from: client@example.com
subject: Project Status Update Needed
received: 2026-04-17T10:30:00Z
email_id: abc123xyz
priority: medium
labels: [inbox, important]
```

## Email Content

**From:** client@example.com
**Subject:** Project Status Update Needed
**Received:** 2026-04-17 10:30:00

---

Can you provide an update on the project timeline?
We need this by end of week.

Thanks,
John

---

## Suggested Actions

1. Review current project status
2. Prepare timeline update
3. Draft response email
4. Send update to client

## Response Required
- [ ] Reply to client@example.com
- [ ] Provide project timeline update
- [ ] Deadline: End of week
```

---

## Configuration

```json
{
  "gmail": {
    "mode": "mock",
    "check_interval_seconds": 60,
    "max_emails_per_check": 10,
    "mark_as_read": true,
    "labels_to_watch": ["INBOX", "IMPORTANT"],
    "exclude_labels": ["SPAM", "TRASH"]
  },
  "api": {
    "credentials_file": "config/gmail_credentials.json",
    "token_file": "config/gmail_token.json",
    "scopes": ["https://www.googleapis.com/auth/gmail.readonly"]
  },
  "processing": {
    "deduplicate": true,
    "processed_log": "logs/processed_emails.json"
  }
}
```

---

## Usage

### Mock Mode (Testing)
```bash
python scripts/watch_gmail.py --mock
```

### API Mode (Production)
```bash
python scripts/watch_gmail.py --api
```

### Once Mode
```bash
python scripts/watch_gmail.py --once
```

---

## Dependencies

**Mock Mode:** None (built-in)

**API Mode:**
```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

---

**Status:** ✅ Ready (Mock Mode)
**API Setup:** Optional (for production)
