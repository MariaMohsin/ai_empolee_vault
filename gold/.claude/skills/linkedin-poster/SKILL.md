# Skill: linkedin-poster

Generate professional LinkedIn posts from templates and queue them for approval.

## Usage

```bash
# List available templates
python .claude/skills/linkedin-poster/scripts/generate_post.py --list

# Generate from template
python .claude/skills/linkedin-poster/scripts/generate_post.py --template automation_success

# Preview without saving
python .claude/skills/linkedin-poster/scripts/generate_post.py --template company_update --preview

# Custom post
python .claude/skills/linkedin-poster/scripts/generate_post.py --custom "Your post text here"
```

## Templates

- `automation_success` - Share an automation win
- `company_update`     - Share a milestone
- `industry_insight`   - Share AI insight
- `team_highlight`     - Highlight team/collaborators
- `product_launch`     - Announce product/feature

## Flow

1. Generator creates approval file in `AI_Employee_Vault/Needs_Approval/`
2. Manager adds `DECISION: APPROVED` to the file
3. MCP Executor detects approval and calls `linkedin-post` skill
4. Playwright posts live to LinkedIn

## Notes

- Never posts directly — always goes through approval
- Works with MCP Executor routing (action_type: linkedin_post)
- Connects to existing `linkedin-post` skill for actual posting
