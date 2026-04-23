# CEO Weekly Briefing — {{DATE}}

**Period:** {{PERIOD_FROM}} → {{PERIOD_TO}}  |  **Generated:** {{GENERATED_AT}}  |  **System:** {{HEALTH_STATUS}}

---

## ⚠️ Alerts

{{ALERTS}}

---

## 1. Revenue Summary

| Metric | Amount |
|--------|--------|
| Income | {{INCOME}} |
| Expenses | {{EXPENSES}} |
| **Net** | **{{NET}} [{{NET_TAG}}]** |

**Transactions this period:**

{{TRANSACTIONS}}

---

## 2. Tasks Completed ({{TASK_COUNT}})

Breakdown by type: {{TYPE_BREAKDOWN}}

{{TASK_LIST}}

---

## 3. Pending Approvals ({{PENDING_COUNT}})

{{PENDING_LIST}}

> **Action:** Open `AI_Employee_Vault/Pending_Approval/` and add `DECISION: APPROVED` or `DECISION: REJECTED`.

---

## 4. Cloud Agent Activity

| Metric | Count |
|--------|-------|
| Cycles run | {{CYCLES}} |
| Emails triaged | {{EMAILS_TRIAGED}} |
| Drafts created | {{DRAFTS}} |
| Errors logged | {{ERRORS}} |

**Approval decisions:** Approved {{APPROVED}} | Rejected {{REJECTED}} | Expired {{EXPIRED}}

---

## 5. System Health — {{HEALTH_STATUS}}

{{HEALTH_ISSUES}}

> Full report: `AI_Employee_Vault/Logs/system_health.md`

---

## 6. Suggestions

{{SUGGESTIONS}}

---

*Platinum AI Employee — auto-generated every Sunday*
*Next briefing: {{NEXT_SUNDAY}}*
