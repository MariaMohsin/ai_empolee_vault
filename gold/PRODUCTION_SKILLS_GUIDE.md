# Production Agent Skills - Complete Guide

## Overview

4 production-ready Agent Skills for autonomous AI Employee operations.
**All skills perform REAL actions** - no simulations or mocks.

---

## Skill 1: gmail-send

**Purpose:** Send real emails via Gmail SMTP

**Location:** `.claude/skills/gmail-send/`

**Setup:**
```bash
# Set environment variables (Windows)
set EMAIL_ADDRESS=your-email@gmail.com
set EMAIL_PASSWORD=your-app-password

# Linux/Mac
export EMAIL_ADDRESS="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"
```

**Gmail App Password:**
1. Go to https://myaccount.google.com/apppasswords
2. Create app password for "Mail"
3. Use this password (not your regular Gmail password)

**Usage:**
```bash
python .claude/skills/gmail-send/scripts/send_email.py \
  --to "recipient@example.com" \
  --subject "Test Email" \
  --body "This is a test email from AI Employee"
```

**Optional Parameters:**
```bash
--cc "person1@example.com,person2@example.com"
--bcc "hidden@example.com"
```

---

## Skill 2: linkedin-post

**Purpose:** Create real LinkedIn posts via browser automation

**Location:** `.claude/skills/linkedin-post/`

**Setup:**
```bash
# Install Playwright
pip install playwright
playwright install chromium

# Set environment variables (Windows)
set LINKEDIN_EMAIL=your-email@example.com
set LINKEDIN_PASSWORD=your-password

# Linux/Mac
export LINKEDIN_EMAIL="your-email@example.com"
export LINKEDIN_PASSWORD="your-password"
```

**Usage:**
```bash
# Headless mode (production)
python .claude/skills/linkedin-post/scripts/post_linkedin.py \
  --content "Excited to share our latest AI Employee update! #AI #Automation"

# Visible browser (debugging)
python .claude/skills/linkedin-post/scripts/post_linkedin.py \
  --content "Your post here" \
  --headless False
```

**Notes:**
- Takes ~10-15 seconds to complete
- Logs into LinkedIn automatically
- Creates text-only posts
- Use visible mode to debug login issues

---

## Skill 3: vault-file-manager

**Purpose:** Manage task workflow between vault folders

**Location:** `.claude/skills/vault-file-manager/`

**No setup required** - works with local filesystem

**Vault Folders:**
- `AI_Employee_Vault/Inbox/` - New tasks
- `AI_Employee_Vault/Needs_Action/` - Pending tasks
- `AI_Employee_Vault/Done/` - Completed tasks
- `AI_Employee_Vault/Needs_Approval/` - Awaiting approval

**Usage:**
```bash
# Move task from Inbox to Needs_Action
python .claude/skills/vault-file-manager/scripts/move_task.py \
  --file "task_20260417.md" \
  --from "Inbox" \
  --to "Needs_Action"

# Move completed task to Done
python .claude/skills/vault-file-manager/scripts/move_task.py \
  --file "task_20260417.md" \
  --from "Needs_Action" \
  --to "Done"
```

---

## Skill 4: human-approval

**Purpose:** Request human approval for sensitive actions

**Location:** `.claude/skills/human-approval/`

**No setup required** - works with local filesystem

**Usage:**
```bash
python .claude/skills/human-approval/scripts/request_approval.py \
  --action "Send email to CEO" \
  --details "Subject: Quarterly Report\nAttachment: Q1_Report.pdf" \
  --timeout 3600 \
  --risk high
```

**Approval Workflow:**

1. **AI Creates Request:**
   - File created in `AI_Employee_Vault/Needs_Approval/`
   - Script waits for decision

2. **Manager Reviews:**
   - Opens approval file
   - Reads action details
   - Adds decision:

   **To Approve:**
   ```
   DECISION: APPROVED
   ```

   **To Reject:**
   ```
   DECISION: REJECTED
   Reason: Not authorized for CEO emails
   ```

3. **Script Returns Result:**
   - Approved: Exit code 0
   - Rejected: Exit code 1
   - Timeout: Exit code 1
   - File renamed: `.approved`, `.rejected`, or `.timeout`

**Parameters:**
- `--timeout`: Seconds to wait (default: 3600 = 1 hour)
- `--risk`: low/medium/high (default: medium)

---

## Integration Example

**Automated Email Workflow with Approval:**

```bash
# Step 1: Request approval for email
python .claude/skills/human-approval/scripts/request_approval.py \
  --action "Send project update email" \
  --details "To: client@example.com\nSubject: Project Status\nBody: Project on track for delivery" \
  --risk medium \
  --timeout 1800

# If approved (exit code 0), send email
if [ $? -eq 0 ]; then
  python .claude/skills/gmail-send/scripts/send_email.py \
    --to "client@example.com" \
    --subject "Project Status" \
    --body "Project on track for delivery"
fi
```

**LinkedIn Posting with Approval:**

```bash
# Step 1: Request approval
python .claude/skills/human-approval/scripts/request_approval.py \
  --action "Post to LinkedIn" \
  --details "Content: Excited to announce our AI Employee platform launch! #AI" \
  --risk high \
  --timeout 3600

# If approved, post
if [ $? -eq 0 ]; then
  python .claude/skills/linkedin-post/scripts/post_linkedin.py \
    --content "Excited to announce our AI Employee platform launch! #AI #Automation"
fi
```

---

## Testing Guide

### Test 1: gmail-send (REAL EMAIL)

```bash
# ⚠️ WARNING: This sends a REAL email
python .claude/skills/gmail-send/scripts/send_email.py \
  --to "your-test-email@example.com" \
  --subject "AI Employee Test" \
  --body "This is a test email from the AI Employee system"
```

**Expected:** Email received in inbox

### Test 2: linkedin-post (REAL POST)

```bash
# ⚠️ WARNING: This creates a REAL LinkedIn post
python .claude/skills/linkedin-post/scripts/post_linkedin.py \
  --content "Testing my AI Employee automation system! #AI #Automation" \
  --headless False
```

**Expected:** Post visible on your LinkedIn profile

### Test 3: vault-file-manager

```bash
# Create test file
echo "# Test Task" > AI_Employee_Vault/Inbox/test_task.md

# Move it
python .claude/skills/vault-file-manager/scripts/move_task.py \
  --file "test_task.md" \
  --from "Inbox" \
  --to "Done"

# Verify
ls AI_Employee_Vault/Done/test_task.md
```

**Expected:** File moved successfully

### Test 4: human-approval

**Terminal 1 (Request):**
```bash
python .claude/skills/human-approval/scripts/request_approval.py \
  --action "Test approval workflow" \
  --details "This is a test of the approval system" \
  --timeout 300
```

**Terminal 2 (Approve):**
```bash
# Find the approval file
ls AI_Employee_Vault/Needs_Approval/

# Edit and add:
echo "DECISION: APPROVED" >> AI_Employee_Vault/Needs_Approval/approval_*.md
```

**Expected:** Terminal 1 shows "Action approved by manager"

---

## Error Handling

All skills include:
- ✅ Input validation
- ✅ Environment variable checks
- ✅ Clear error messages
- ✅ Proper exit codes (0 = success, 1 = failure)
- ✅ Exception handling

**Common Errors:**

**gmail-send:**
- `Authentication failed` → Check EMAIL_ADDRESS and EMAIL_PASSWORD
- Use App Password, not regular password

**linkedin-post:**
- `Playwright not installed` → Run `pip install playwright && playwright install chromium`
- `Login failed` → Check credentials, try visible mode (--headless False)

**vault-file-manager:**
- `File not found` → Check filename and source folder
- `Permission denied` → Check file permissions

**human-approval:**
- `Approval timeout` → Manager didn't respond in time
- File renamed to `.timeout` for audit trail

---

## Production Deployment

### Environment Variables (Production)

**Linux/Mac (.bashrc or .zshrc):**
```bash
export EMAIL_ADDRESS="ai-employee@company.com"
export EMAIL_PASSWORD="app-password-here"
export LINKEDIN_EMAIL="ai-employee@company.com"
export LINKEDIN_PASSWORD="linkedin-password"
```

**Windows (System Properties > Environment Variables):**
```
EMAIL_ADDRESS = ai-employee@company.com
EMAIL_PASSWORD = app-password-here
LINKEDIN_EMAIL = ai-employee@company.com
LINKEDIN_PASSWORD = linkedin-password
```

**Docker (.env file):**
```env
EMAIL_ADDRESS=ai-employee@company.com
EMAIL_PASSWORD=app-password-here
LINKEDIN_EMAIL=ai-employee@company.com
LINKEDIN_PASSWORD=linkedin-password
```

### Security Best Practices

1. **Never commit credentials to git**
   - Add `.env` to `.gitignore`
   - Use environment variables only

2. **Use App Passwords**
   - Gmail: App Password (not regular password)
   - LinkedIn: Consider creating dedicated account

3. **Restrict Permissions**
   - Limit AI Employee account permissions
   - Use separate account for automation

4. **Audit Trail**
   - All actions logged
   - Approval files renamed (not deleted)
   - Track what was approved/rejected/timeout

---

## Skill Architecture Benefits

**vs MCP Servers:**
- ✅ Lighter weight (no server processes)
- ✅ Simpler deployment (just Python scripts)
- ✅ Token efficient (concise SKILL.md files)
- ✅ Directly executable (no protocol overhead)
- ✅ Easy to test (run scripts directly)

**Production Ready:**
- ✅ Real actions (not simulations)
- ✅ Error handling
- ✅ Clean output
- ✅ Exit codes
- ✅ Subprocess safe

---

## Next Steps

1. **Set up credentials** for gmail-send and linkedin-post
2. **Test each skill** individually
3. **Integrate** with Silver Scheduler (run_ai_employee.py)
4. **Deploy** to production

**All 4 skills are production-ready and tested!** 🚀
