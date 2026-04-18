# Skill: social-summary

Log every social media post to `AI_Employee_Vault/Social_Log.md`.
Includes platform, content, date, and status in both a summary table and a full content block.

---

## Usage

### Log a LinkedIn post directly
```bash
python .claude/skills/social-summary/scripts/social_summary.py \
  --log linkedin "We just shipped a new feature! #AI #Automation"
```

### Log from an existing approval file (auto-parses content + status)
```bash
python .claude/skills/social-summary/scripts/social_summary.py \
  --from-file AI_Employee_Vault/Needs_Approval/linkedin_post_20260418_162906.md
```

### Log with explicit status
```bash
python .claude/skills/social-summary/scripts/social_summary.py \
  --log twitter "Exciting news coming soon..." --status approved
```

### View full Social_Log.md
```bash
python .claude/skills/social-summary/scripts/social_summary.py --view
```

### Stats by platform and status
```bash
python .claude/skills/social-summary/scripts/social_summary.py --stats
```

---

## Input Parameters

| Flag | Args | Description |
|------|------|-------------|
| `--log` | `PLATFORM CONTENT` | Platform + post text |
| `--from-file` | `PATH` | Parse approval file automatically |
| `--status` | `STATUS` | `posted` / `approved` / `rejected` / `pending` (default: posted) |
| `--view` | — | Print full log |
| `--stats` | — | Summary counts |

**Supported platforms:** `linkedin`, `twitter`, `facebook`, `instagram`

---

## Output — Social_Log.md

```markdown
# Social Media Log

---

## Posts

| Date | Platform | Preview | Status |
|------|----------|---------|--------|
| 2026-04-18 | Linkedin | We just shipped a new feature! #AI... | Posted |
| 2026-04-18 | Twitter  | Exciting news coming soon...          | Approved |

---

## Full Content

### Linkedin — 2026-04-18 17:00

**Status:** Posted

```
We just shipped a new feature! #AI #Automation
```
```

---

## Integration with linkedin-post skill

After a LinkedIn post is published or approved, call this skill immediately:

```python
import subprocess, sys

subprocess.run([
    sys.executable,
    ".claude/skills/social-summary/scripts/social_summary.py",
    "--from-file", str(approval_file_path),
])
```

Or from the Ralph Wiggum Loop — add `social-summary` as a post-execution step after any `linkedin_post` / `twitter` action.

---

## Notes

- `Social_Log.md` is auto-created on first run
- Each `--from-file` call parses platform from filename and content from the `**Content:**` block
- Status is detected from `DECISION: APPROVED` / `DECISION: REJECTED` markers
- Entries are never deleted — append-only log
