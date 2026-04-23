---
task_id: {{TASK_ID}}
task_type: {{TASK_TYPE}}
status: pending
created_at: {{CREATED_AT}}
expires_at: {{EXPIRES_AT}}
sender: {{SENDER}}
subject: {{SUBJECT}}
---

# Approval Request — {{TASK_TYPE_UPPER}}

**Task ID:** `{{TASK_ID}}`
**Created:** {{CREATED_AT}}
**Expires:** {{EXPIRES_AT}}

---

## Draft Content

{{DRAFT_BODY}}

---

## ⚠️ Human Decision Required

Review the draft above. Write ONE of these lines at the **bottom** of this
file, then save. The system picks it up within 60 seconds.

**To approve:**
```
DECISION: APPROVED
```

**To reject:**
```
DECISION: REJECTED
Reason: (your reason here)
```

### Expiry Rules

| Task Type | Expires After |
|-----------|--------------|
| email     | 4 hours      |
| social    | 8 hours      |
| payment   | 24 hours     |
| other     | 2 hours      |

Expired items auto-move to `/Done/` with status `expired`.
**Nothing executes without `DECISION: APPROVED` written in this file.**

---

<!-- system: do not edit below this line -->
