# Platinum AI Employee — Complete Quickstart

## Project Status: ✅ COMPLETE

---

## Required APIs (3 mandatory, 3 optional)

### Mandatory

| API | What for | Where to get |
|-----|----------|-------------|
| **Anthropic API Key** | Claude drafts emails, suggestions, reasoning | https://console.anthropic.com → API Keys |
| **Gmail App Password** | Watch inbox + send approved emails | https://myaccount.google.com → Security → 2-Step → App passwords |
| **Gmail address** | The account the AI monitors | Your existing Gmail |

### Optional (enable more features)

| API | What for | Where to get |
|-----|----------|-------------|
| LinkedIn email + password | Post LinkedIn content via automation | Your LinkedIn account credentials |
| Twitter API v2 | Post tweets | https://developer.twitter.com → Projects |
| Odoo credentials | Accounting / invoicing | Self-hosted Odoo VM (free) |

---

## Step 1 — Install Dependencies (run once)

```powershell
cd C:\Users\HP\Desktop\ai_employee\platinum

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install all packages
pip install anthropic watchdog google-auth google-auth-oauthlib google-api-python-client python-dotenv requests playwright

# Install browser for LinkedIn automation
playwright install chromium
```

---

## Step 2 — Set Up .env (run once)

```powershell
copy .env.example .env
notepad .env
```

Fill in at minimum:
```
EMAIL_ADDRESS=your_gmail@gmail.com
EMAIL_PASSWORD=your_16_char_app_password
ANTHROPIC_API_KEY=sk-ant-...

ODOO_URL=http://localhost:8069
ODOO_DB=mycompany
ODOO_USERNAME=admin
ODOO_PASSWORD=admin
```

---

## Step 3 — Clean Up Old Error Files (run once)

```powershell
python scripts\cleanup_errors.py
```

---

## Step 4 — Run the System

### Option A — Run everything locally (Windows, no VM)

Open 3 separate PowerShell windows:

**Window 1 — Cloud Agent (email triage + drafting):**
```powershell
cd C:\Users\HP\Desktop\ai_employee\platinum
venv\Scripts\activate
python scripts\orchestrator.py --cloud --once
```

**Window 2 — Approval Workflow (auto-processes decisions):**
```powershell
cd C:\Users\HP\Desktop\ai_employee\platinum
venv\Scripts\activate
python scripts\approval_workflow.py --daemon
```

**Window 3 — Watchdog (health monitoring):**
```powershell
cd C:\Users\HP\Desktop\ai_employee\platinum
venv\Scripts\activate
python scripts\watchdog.py --daemon
```

**To approve a draft and send it (Local Agent):**
```powershell
python scripts\local_agent.py --review    # see pending drafts, type A to approve
python scripts\local_agent.py --execute   # send approved items
```

---

### Option B — Single test cycle (quickest way to verify everything works)

```powershell
cd C:\Users\HP\Desktop\ai_employee\platinum
venv\Scripts\activate

# 1. Run cloud agent once (creates mock email task + draft)
python scripts\cloud_agent.py --once

# 2. List what's waiting for approval
python scripts\approval_workflow.py --list

# 3. Approve interactively
python scripts\local_agent.py --review

# 4. Execute approved tasks
python scripts\local_agent.py --execute

# 5. Check system status
python scripts\orchestrator.py --status
```

---

### Option C — Full daemon mode (production)

```powershell
cd C:\Users\HP\Desktop\ai_employee\platinum
venv\Scripts\activate
python scripts\orchestrator.py --cloud     # runs forever, polls every 2 min
```

In a second window:
```powershell
python scripts\orchestrator.py --local     # runs forever, polls every 60s
```

---

## Step 5 — Generate CEO Briefing

```powershell
# Preview (does not save)
python scripts\ceo_briefing.py --preview

# Force generate and save to AI_Employee_Vault/Briefings/YYYY-MM-DD.md
python scripts\ceo_briefing.py --force
```

---

## Step 6 — Health Check

```powershell
# System status snapshot
python scripts\orchestrator.py --status

# Watchdog single check (writes system_health.md)
python scripts\watchdog.py --once

# View health report
Get-Content AI_Employee_Vault\Logs\system_health.md

# View any log (PowerShell tail equivalent)
Get-Content Logs\cloud_agent.log -Wait -Tail 20
Get-Content Logs\approval_workflow.log -Wait -Tail 20
```

---

## Platinum Demo Flow (Minimum Passing Gate)

This is the exact flow described in the hackathon docs:

```
1. Email arrives in Gmail
        ↓
2. Cloud Agent triages it → Needs_Action/email/task-xyz.md
        ↓
3. Cloud Agent claims it → In_Progress/cloud/task-xyz.md
        ↓
4. Cloud Agent drafts reply via Claude API
        ↓
5. Cloud Agent writes → Pending_Approval/email/task-xyz.md
        ↓
6. [User opens file, adds:  DECISION: APPROVED]
        ↓
7. approval_workflow.py detects decision → Approved/task-xyz.md
        ↓
8. Local Agent picks up → In_Progress/local/task-xyz.md
        ↓
9. Local Agent sends email via Gmail SMTP
        ↓
10. Done/task-xyz.md  ← audit trail complete
```

**To demo this end-to-end:**
```powershell
# Cloud does its part (or it's running on VM already)
python scripts\cloud_agent.py --once

# You approve
python scripts\local_agent.py --review

# Local executes
python scripts\local_agent.py --execute

# Verify
Get-ChildItem AI_Employee_Vault\Done\
```

---

## Folder Reference

```
AI_Employee_Vault/
├── Needs_Action/
│   ├── email/        ← Cloud writes new email tasks here
│   └── social/       ← Cloud writes new social tasks here
├── In_Progress/
│   ├── cloud/        ← Cloud's claimed workspace (atomic lock)
│   └── local/        ← Local's claimed workspace
├── Pending_Approval/
│   ├── email/        ← Drafts waiting for your DECISION: APPROVED
│   ├── social/       ← Social drafts waiting
│   └── payment/      ← Payment drafts (Local ONLY executes)
├── Approved/         ← You approved → Local will execute
├── Done/             ← Completed tasks (full audit trail)
├── Errors/           ← Failed tasks (max 3 retries, then stays here)
├── Accounting/       ← Monthly ledger
├── Briefings/        ← Weekly CEO reports (YYYY-MM-DD.md)
├── Logs/             ← system_health.md lives here
└── Templates/        ← approval_template.md, briefing_template.md
```

---

## Safety Rules (always enforced)

| Rule | Enforced by |
|------|------------|
| Nothing sends without DECISION: APPROVED | approval_workflow.py |
| Cloud never sends emails or posts | cloud_agent.py has no SMTP/MCP calls |
| Max 3 retries on failed tasks | error_recovery.py (fixed) |
| Secrets never in vault | .gitignore blocks .env, tokens, sessions |
| Dashboard writes are atomic | os.replace() + advisory lock |
| Task ownership is exclusive | os.replace() claim-by-move |
