# Skill: accounting-manager

Maintain the business accounting ledger and generate financial summaries.

Ledger file: `AI_Employee_Vault/Accounting/Current_Month.md`

---

## Usage

### Log an income entry
```bash
python .claude/skills/accounting-manager/scripts/accounting_manager.py \
  --add income 5000 "Client payment - Acme Corp"
```

### Log an expense entry
```bash
python .claude/skills/accounting-manager/scripts/accounting_manager.py \
  --add expense 200 "Office supplies"
```

### Generate monthly summary (total income / expenses / net)
```bash
python .claude/skills/accounting-manager/scripts/accounting_manager.py \
  --summary
```

### Generate weekly summary (last 7 days)
```bash
python .claude/skills/accounting-manager/scripts/accounting_manager.py \
  --weekly
```

### View full ledger
```bash
python .claude/skills/accounting-manager/scripts/accounting_manager.py \
  --view
```

---

## Input Parameters

| Flag | Args | Required | Description |
|------|------|----------|-------------|
| `--add` | `TYPE AMOUNT DESCRIPTION` | — | Log income or expense |
| `--summary` | — | — | Show month totals |
| `--weekly` | — | — | Show last-7-day breakdown |
| `--view` | — | — | Print full Current_Month.md |

**TYPE** must be `income` or `expense`  
**AMOUNT** must be a positive number (commas allowed, e.g. `5,000`)

---

## Output

### `--add`
```
✓ Income logged: +PKR 5,000.00 | Client payment - Acme Corp
  File: AI_Employee_Vault/Accounting/Current_Month.md
```

### `--summary`
```
=============================================
  Accounting Summary — April 2026
=============================================
  Total Income   : PKR      5,000.00
  Total Expenses : PKR        200.00
  ────────────────────────────────
  Net Balance    : PKR      4,800.00  ✅
  Entries        : 2
=============================================
```

### `--weekly`
```
=============================================
  Weekly Summary  (Apr 11 – Apr 18, 2026)
=============================================
  2026-04-15  Income     +PKR   5,000.00  Client payment - Acme Corp
  2026-04-17  Expense    -PKR     200.00  Office supplies
  ─────────────────────────────────────────
  Income   : PKR   5,000.00
  Expenses : PKR     200.00
  Net      : PKR   4,800.00  ✅
=============================================
```

---

## File Structure

```
AI_Employee_Vault/
└── Accounting/
    ├── Current_Month.md      ← Active ledger (auto-created)
    └── History/
        ├── March_2026.md     ← Auto-archived at month rollover
        └── February_2026.md
```

### Current_Month.md format

```markdown
# Accounting Ledger — April 2026

## Entries

| Date | Type | Amount (PKR) | Description |
|------|------|-------------|-------------|
| 2026-04-15 | Income  | 5,000.00 | Client payment - Acme Corp |
| 2026-04-17 | Expense |   200.00 | Office supplies |

## Summary

- **Total Income:** PKR 5,000.00
- **Total Expenses:** PKR 200.00
- **Net Balance:** PKR 4,800.00

*Last updated: 2026-04-17 14:30*
```

---

## Behaviour

- **Month rollover:** When a new month starts, `Current_Month.md` is automatically archived to `History/` and a fresh ledger is created.
- **Summary auto-update:** Every `--add` call recalculates and rewrites the Summary section.
- **No dependencies:** Pure Python standard library — no installs required.

---

## Notes

- Currency displayed as PKR (editable in script line `"Amount (PKR)"`)
- History files are read-only archives — never modified after archiving
- Safe to run multiple times; entries are appended, not overwritten
