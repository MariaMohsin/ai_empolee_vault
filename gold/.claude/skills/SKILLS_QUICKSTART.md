# Production Skills - Quick Reference

## 4 Production-Ready Agent Skills

All skills perform **REAL actions** (no simulations).

---

## 1. gmail-send - Real Email Sending

```bash
python .claude/skills/gmail-send/scripts/send_email.py \
  --to "recipient@example.com" \
  --subject "Subject" \
  --body "Message"
```

**Setup:**
```bash
set EMAIL_ADDRESS=your@gmail.com
set EMAIL_PASSWORD=app-password-here
```

Get App Password: https://myaccount.google.com/apppasswords

---

## 2. linkedin-post - Real LinkedIn Posts

```bash
python .claude/skills/linkedin-post/scripts/post_linkedin.py \
  --content "Your post content #hashtags"
```

**Setup:**
```bash
pip install playwright && playwright install chromium
set LINKEDIN_EMAIL=your-email@example.com
set LINKEDIN_PASSWORD=your-password
```

**Debug mode:** Add `--headless False` to see browser

---

## 3. vault-file-manager - Task Workflow

```bash
python .claude/skills/vault-file-manager/scripts/move_task.py \
  --file "task.md" \
  --from "Inbox" \
  --to "Done"
```

**Folders:** Inbox, Needs_Action, Done, Needs_Approval

**No setup required** ✅

---

## 4. human-approval - Approval Workflow

```bash
python .claude/skills/human-approval/scripts/request_approval.py \
  --action "Send email to CEO" \
  --details "Details here" \
  --timeout 3600 \
  --risk high
```

**Approve:** Edit approval file, add `DECISION: APPROVED`
**Reject:** Edit approval file, add `DECISION: REJECTED\nReason: Your reason`

**No setup required** ✅

---

## Combined Workflow Example

```bash
# Request approval
python .claude/skills/human-approval/scripts/request_approval.py \
  --action "Send project update email" \
  --details "To: client@example.com\nSubject: Project Update" \
  --timeout 1800

# If approved (exit code 0), send email
if [ $? -eq 0 ]; then
  python .claude/skills/gmail-send/scripts/send_email.py \
    --to "client@example.com" \
    --subject "Project Update" \
    --body "Your project is on track for delivery"
fi
```

---

## Status

| Skill | Status | Setup Required |
|-------|--------|----------------|
| gmail-send | ✅ Ready | Gmail App Password |
| linkedin-post | ✅ Ready | Playwright + Credentials |
| vault-file-manager | ✅ Working | None |
| human-approval | ✅ Working | None |

**All 4 skills tested and production-ready!** 🚀

See `PRODUCTION_SKILLS_GUIDE.md` for detailed documentation.
See `PRODUCTION_SKILLS_TEST_RESULTS.md` for test results.
