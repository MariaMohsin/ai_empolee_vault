# Skill: vault-file-manager

Manage task workflow by moving files between vault folders.

## Usage

```bash
python .claude/skills/vault-file-manager/scripts/move_task.py \
  --file "task_file.md" \
  --from "Inbox" \
  --to "Done"
```

## Vault Folders

- `AI_Employee_Vault/Inbox/` - New incoming tasks
- `AI_Employee_Vault/Needs_Action/` - Tasks awaiting execution
- `AI_Employee_Vault/Done/` - Completed tasks
- `AI_Employee_Vault/Needs_Approval/` - Tasks requiring approval

## Input Parameters

- `--file`: Filename to move (required)
- `--from`: Source folder name (required)
- `--to`: Destination folder name (required)

## Output

Success: "Moved task_file.md from Inbox to Done"
Error: "Failed to move file: [error message]"

## Examples

```bash
# Move task from Inbox to Needs_Action
python .claude/skills/vault-file-manager/scripts/move_task.py \
  --file "email_task.md" --from "Inbox" --to "Needs_Action"

# Move completed task to Done
python .claude/skills/vault-file-manager/scripts/move_task.py \
  --file "completed_task.md" --from "Needs_Action" --to "Done"
```

## Notes

- Automatically creates destination folders if missing
- Preserves file content and metadata
- Production-ready with error handling
