# Skill: ceo-briefing

Generate a weekly CEO briefing report covering all AI Employee activity.

Output file: `AI_Employee_Vault/Reports/CEO_Weekly_<YYYY-MM-DD>.md`

---

## Usage

### Generate this week's briefing (saves to Reports/)
```bash
python .claude/skills/ceo-briefing/scripts/ceo_briefing.py
```

### Preview without saving
```bash
python .claude/skills/ceo-briefing/scripts/ceo_briefing.py --preview
```

### Custom lookback window
```bash
python .claude/skills/ceo-briefing/scripts/ceo_briefing.py --days 14
```

---

## Report Sections

| # | Section | Data Source |
|---|---------|-------------|
| 1 | Tasks Completed | `AI_Employee_Vault/Done/*.md` |
| 2 | Emails Processed | `Logs/processed_emails.json` |
| 3 | LinkedIn Activity | `AI_Employee_Vault/Needs_Approval/` + `Logs/action.log` |
| 4 | Pending Approvals | `AI_Employee_Vault/Needs_Approval/*.md` |
| 5 | Financial Summary | `AI_Employee_Vault/Accounting/Current_Month.md` |
| 6 | System Health | Log sizes, last AI run time, vault folder status |

---

## Sample Output

```markdown
# CEO Weekly Briefing

**Period:** Apr 11, 2026 to Apr 18, 2026
**Generated:** 2026-04-18 14:00
**System Status:** OK

## 1. Tasks Completed (3)
- [2026-04-18] approval send email 20260417
- ...

## 2. Emails Processed (2)
- [2026-04-18] Project Status Update Needed
- [2026-04-18] Partnership Opportunity

## 3. LinkedIn Activity (2)
- [2026-04-18] Pending — linkedin_post_20260418_162906.md

## 4. Pending Approvals (2)
- linkedin_post_20260418_162906.md  (waiting since 2026-04-18 16:29)
> Action Required: Review files in AI_Employee_Vault/Needs_Approval/

## 5. Financial Summary (Month to Date)
| Metric | Amount |
| Total Income | PKR 6,500.00 |
| Total Expenses | PKR 200.00 |
| Net Balance | PKR 6,300.00 [PROFIT] |

## 6. System Health — OK
...
```

---

## Auto-Run via Scheduler

### Windows Task Scheduler (run once to register)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/schedule_ceo_briefing.ps1
```

This registers a weekly Task Scheduler job that runs every Monday at 08:00.

### Manual weekly run (alternative)
```bash
python scripts/run_weekly_briefing.py
```

---

## Output Location

```
AI_Employee_Vault/
└── Reports/
    ├── CEO_Weekly_2026-04-18.md   ← this week
    ├── CEO_Weekly_2026-04-11.md   ← last week
    └── ...
```

Each run creates a new dated file. Old reports are never overwritten.

---

## Notes

- No external dependencies — pure Python stdlib
- Safe to run multiple times in a day (each run creates a new file)
- `--preview` flag is useful for testing without cluttering Reports/
