# business-mcp

Gold Tier MCP server for external business actions.  
Protocol: **JSON-RPC 2.0 over stdio** (Model Context Protocol).

---

## Exposed Tools

| Tool | Description |
|---|---|
| `send_email` | Send email via Gmail SMTP |
| `post_linkedin` | Publish post to LinkedIn (Playwright) |
| `log_activity` | Append entry to `Vault/Logs/Business.log` |

---

## Tool Signatures

### `send_email`
```json
{
  "to":      "recipient@example.com",
  "subject": "Hello",
  "body":    "Plain-text email body"
}
```

### `post_linkedin`
```json
{
  "content":  "Your LinkedIn post text (max 3000 chars)",
  "headless": true
}
```

### `log_activity`
```json
{
  "message": "Sent proposal to Client X"
}
```

---

## Setup

### 1. Environment variables

Add to `gold/.env`:
```env
EMAIL_ADDRESS=you@gmail.com
EMAIL_PASSWORD=your-app-password

LINKEDIN_EMAIL=you@linkedin.com
LINKEDIN_PASSWORD=your-linkedin-password
```

> Gmail App Password: https://myaccount.google.com/apppasswords

### 2. Install dependencies (LinkedIn only)
```bash
pip install playwright
playwright install chromium
```

### 3. Register with Claude Code

Add to `gold/.claude/settings.json`:
```json
{
  "mcpServers": {
    "business-mcp": {
      "command": "python",
      "args": ["mcp/business_mcp/server.py"],
      "cwd": "C:/Users/HP/Desktop/ai_employee/gold"
    }
  }
}
```

Then restart Claude Code. The tools will appear automatically.

---

## Usage from Claude Code

Once registered, ask Claude directly:

```
Send an email to boss@company.com with subject "Weekly Report" and body "All tasks complete."
```

```
Post to LinkedIn: "Excited to share our Q2 results! 🚀 #Growth"
```

```
Log business activity: "Client meeting completed with Acme Corp"
```

---

## Output Logs

| Log file | Content |
|---|---|
| `Vault/Logs/Business.log` | All business activity entries |
| `Logs/business_mcp_server.log` | Server-level debug log |

---

## Architecture

```
Claude Code
    │
    │  JSON-RPC 2.0 (stdio)
    ▼
server.py  (business-mcp)
    ├── send_email()     → Gmail SMTP
    ├── post_linkedin()  → .claude/skills/linkedin-post/scripts/post_linkedin.py
    └── log_activity()   → Vault/Logs/Business.log
```

---

## Error Handling

- Missing env vars → clear `RuntimeError` message returned as `isError: true`
- LinkedIn script missing → descriptive error with install instructions
- SMTP failure → exception propagated with SMTP error detail
- All errors logged to `Logs/business_mcp_server.log`

---

## Extending

To add a new tool, append to `TOOL_REGISTRY` in `server.py`:

```python
TOOL_REGISTRY["my_tool"] = {
    "fn": my_tool_function,
    "description": "What it does",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "..."}
        },
        "required": ["param"],
    },
}
```

No other changes needed — the server auto-registers all entries.
