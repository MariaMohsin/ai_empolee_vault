# Bronze Tier Watcher Test Guide

## Step-by-Step Testing Instructions

### Test 1: Start the File Watcher

**Open a terminal/command prompt and run:**

```bash
cd C:\Users\HP\Desktop\ai_employee\bronze
python file_watcher.py
```

**Expected output:**
```
[FILE WATCHER] Starting up...
[SETUP] Created missing folder: ... (if any)
[FILE WATCHER] Running and monitoring Inbox folder...
[INFO] Press Ctrl+C to stop
```

**Status:** Leave this terminal running (don't close it)

---

### Test 2: Create a Test File in Inbox

**While the watcher is running, in a NEW terminal:**

**Method 1: Using echo command**
```bash
cd C:\Users\HP\Desktop\ai_employee\bronze\Inbox
echo "# Test Task\n\nPlease analyze this test document and provide a summary." > test_document.md
```

**Method 2: Using Python**
```bash
cd C:\Users\HP\Desktop\ai_employee\bronze\Inbox
python -c "with open('test_document.md', 'w') as f: f.write('# Test Task\n\nPlease analyze this test document.')"
```

**Method 3: Manual (recommended for first test)**
- Open Notepad
- Paste this content:
```
# Test Task

Please analyze this test document and provide a summary of its contents.

This is a test to verify the Bronze Tier watcher is working correctly.
```
- Save as: `C:\Users\HP\Desktop\ai_employee\bronze\Inbox\test_document.md`

---

### Test 3: Verify Automation Worked

**Within 1-2 seconds, check the watcher terminal. You should see:**
```
[NEW FILE] Detected: test_document.md
  -> Archived to: Inbox_Archive/test_document.md
  -> Created task: task_test_document.md
[SUCCESS] Structured task created for test_document.md
```

---

### Test 4: Verify File Locations

**Check these folders:**

1. **Inbox should be EMPTY:**
   ```bash
   ls bronze/Inbox/
   ```
   Expected: Empty (file was moved)

2. **Inbox_Archive should contain original:**
   ```bash
   ls bronze/Inbox_Archive/
   ```
   Expected: `test_document.md`

3. **Needs_Action should contain task:**
   ```bash
   ls bronze/Needs_Action/
   ```
   Expected: `task_test_document.md`

---

### Test 5: Inspect Generated Task

**Open the generated task file:**
```bash
cat bronze/Needs_Action/task_test_document.md
```

**Expected structure:**
- YAML frontmatter with metadata
- Task description
- Content preview
- Action items checklist
- Processing guidelines

---

### Test 6: Stop the Watcher

**In the watcher terminal, press:** `Ctrl+C`

**Expected output:**
```
[SHUTDOWN] Stopping file watcher...
[FILE WATCHER] Stopped successfully
```

---

## Quick Test Results Checklist

- [ ] Watcher starts without errors
- [ ] Test file detected within 2 seconds
- [ ] Original file moved to Inbox_Archive
- [ ] Structured task created in Needs_Action
- [ ] Task file contains YAML frontmatter
- [ ] Task file has content preview
- [ ] Watcher stops cleanly with Ctrl+C

---

## Test 7: Claude Code Integration Test

**This tests if Claude Code can interact with your vault.**

Run these commands in Claude Code:
```
1. "Read the file bronze/Needs_Action/task_test_document.md"
2. "Create a response to this task and write it in the same file"
3. "Move the completed task to bronze/Done/"
```

**Expected:** Claude should be able to read, edit, and organize files.

---

## Troubleshooting

### Problem: Watcher doesn't start
**Solution:** Check Python path and install watchdog:
```bash
pip install watchdog==3.0.0
```

### Problem: Files not detected
**Solution:**
- Ensure you're saving to the correct Inbox folder
- Wait 1-2 seconds for detection
- Check Logs/watcher_error.log for errors

### Problem: Folder not found errors
**Solution:** Watcher auto-creates folders, but ensure you're in the right directory:
```bash
cd C:\Users\HP\Desktop\ai_employee\bronze
```

---

## Success Criteria

✅ **Bronze Tier is working if:**
1. Watcher runs without crashing
2. Files in Inbox are automatically detected
3. Structured tasks are created in Needs_Action
4. Original files are archived
5. Claude Code can read and write to vault folders

---

**Next:** Once all tests pass, you're ready for Silver Tier! 🥈
