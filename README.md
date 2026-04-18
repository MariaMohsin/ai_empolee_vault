# AI Employee — Autonomous Digital Worker

A fully autonomous AI Employee built with Claude Code Agent Skills.
Three-tier progression from basic file automation to full business operations.

---

## Project Structure

```
ai_employee/
├── bronze/    Tier 1 — File watcher, vault, basic automation
├── silver/    Tier 2 — Gmail, LinkedIn, reasoning loop, approvals, MCP server
└── gold/      Tier 3 — Full autonomous business + personal operations
```

---

## Gold Tier Capabilities

| Feature | Description |
|---|---|
| 13 Agent Skills | Gmail, LinkedIn, Twitter, Facebook, Instagram, Accounting, CEO Briefing, Error Recovery, Ralph Loop, Personal Tasks |
| 2 MCP Servers | `business-mcp` (email/social/log) + `odoo-mcp` (invoicing/payments) |
| Ralph Wiggum Loop | Autonomous 5-step task executor with approval gate |
| Accounting Manager | Income/expense ledger with monthly rollover |
| CEO Weekly Briefing | Auto-generated every Monday with full business summary |
| Error Recovery | Log → quarantine → retry after 5 min |
| Cross-domain | Separate Business and Personal task pipelines |
| Social Media | Post + log to LinkedIn, Twitter, Facebook, Instagram |

---

## Quick Start (Gold Tier)

```bash
cd gold

# 1. Copy and fill credentials
cp .env.example .env

# 2. Run once
python scripts/run_ai_employee.py --once

# 3. Run as daemon (every 5 min)
python scripts/run_ai_employee.py --daemon
```

---

## Scheduler Work Cycle (Gold)

```
Every 5 minutes:
  Step 1  Gmail Watcher     — fetch emails → Inbox
  Step 2  Vault Watcher     — Inbox → Needs_Action
  Step 3  Ralph Wiggum Loop — Needs_Action → Done (autonomous 5-step)
  Step 4  Personal Tasks    — Personal/Inbox → Personal/Done
  Step 5  MCP Executor      — execute approved actions
```

---

## Requirements

- Python 3.11+
- No external dependencies for core system
- Optional: `playwright` for LinkedIn browser automation

---

## Author

Maria Mohsin — AI Employee Project
