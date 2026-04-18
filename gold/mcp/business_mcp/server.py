#!/usr/bin/env python3
"""
business-mcp  |  Gold Tier MCP Server
Model Context Protocol server (stdio / JSON-RPC 2.0)

Exposed tools:
  send_email(to, subject, body)   – Gmail SMTP
  post_linkedin(content)          – Playwright browser automation
  log_activity(message)           – Append to Vault/Logs/Business.log

Run (Claude Code will launch this automatically via mcpServers config):
    python mcp/business_mcp/server.py
"""

from __future__ import annotations

import json
import os
import smtplib
import subprocess
import sys
import traceback
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


# ─── paths ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent   # gold/
LOGS_DIR = ROOT / "Vault" / "Logs"
BUSINESS_LOG = LOGS_DIR / "Business.log"
SERVER_LOG = ROOT / "Logs" / "business_mcp_server.log"

LINKEDIN_SCRIPT = (
    ROOT / ".claude" / "skills" / "linkedin-post" / "scripts" / "post_linkedin.py"
)


# ─── bootstrap ────────────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SERVER_LOG.parent.mkdir(parents=True, exist_ok=True)


def _load_env() -> None:
    """Load .env from project root (idempotent)."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _log_server(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(SERVER_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except OSError:
        pass


# ─── tool: send_email ─────────────────────────────────────────────────────────

def tool_send_email(args: dict) -> dict:
    """
    Send an email via Gmail SMTP.
    Required: to, subject, body
    """
    to = str(args.get("to", "")).strip()
    subject = str(args.get("subject", "")).strip()
    body = str(args.get("body", "")).strip()

    if not to:
        raise ValueError("'to' is required")
    if not subject:
        raise ValueError("'subject' is required")
    if not body:
        raise ValueError("'body' is required")

    email_addr = os.environ.get("EMAIL_ADDRESS", "")
    email_pass = os.environ.get("EMAIL_PASSWORD", "")

    if not email_addr or not email_pass:
        raise RuntimeError(
            "EMAIL_ADDRESS and EMAIL_PASSWORD must be set in .env"
        )

    msg = MIMEMultipart("alternative")
    msg["From"] = email_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(email_addr, email_pass)
        smtp.sendmail(email_addr, [to], msg.as_string())

    tool_log_activity({"message": f"Email sent to {to} | Subject: {subject}"})
    _log_server(f"send_email → {to} | {subject}")

    return {
        "status": "sent",
        "to": to,
        "subject": subject,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ─── tool: post_linkedin ──────────────────────────────────────────────────────

def tool_post_linkedin(args: dict) -> dict:
    """
    Post content to LinkedIn via the existing Playwright skill.
    Required: content
    Optional: headless (bool, default True)
    """
    content = str(args.get("content", "")).strip()
    headless = bool(args.get("headless", True))

    if not content:
        raise ValueError("'content' is required")
    if len(content) > 3000:
        raise ValueError("LinkedIn posts are limited to 3000 characters")

    if not LINKEDIN_SCRIPT.exists():
        raise RuntimeError(
            f"LinkedIn skill script not found: {LINKEDIN_SCRIPT}\n"
            "Ensure the linkedin-post skill is installed."
        )

    headless_flag = "--headless" if headless else "--no-headless"
    result = subprocess.run(
        [sys.executable, str(LINKEDIN_SCRIPT), "--content", content, headless_flag],
        capture_output=True,
        text=True,
        timeout=120,
        env=os.environ.copy(),
    )

    success = result.returncode == 0
    output = (result.stdout + result.stderr).strip()

    tool_log_activity({
        "message": (
            f"LinkedIn post {'published' if success else 'FAILED'} | "
            f"Preview: {content[:80]}..."
        )
    })
    _log_server(f"post_linkedin → {'ok' if success else 'fail'} | {content[:60]}")

    if not success:
        raise RuntimeError(f"LinkedIn post failed: {output}")

    return {
        "status": "published",
        "content_preview": content[:100] + ("..." if len(content) > 100 else ""),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "output": output,
    }


# ─── tool: log_activity ───────────────────────────────────────────────────────

def tool_log_activity(args: dict) -> dict:
    """
    Append a structured entry to Vault/Logs/Business.log.
    Required: message
    """
    message = str(args.get("message", "")).strip()
    if not message:
        raise ValueError("'message' is required")

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"[{ts}] {message}\n"

    with open(BUSINESS_LOG, "a", encoding="utf-8") as f:
        f.write(entry)

    _log_server(f"log_activity → {message[:80]}")

    return {
        "status": "logged",
        "log_file": str(BUSINESS_LOG),
        "entry": entry.strip(),
    }


# ─── tool registry ────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, dict] = {
    "send_email": {
        "fn": tool_send_email,
        "description": "Send an email via Gmail SMTP",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to":      {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body":    {"type": "string", "description": "Plain-text email body"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    "post_linkedin": {
        "fn": tool_post_linkedin,
        "description": "Publish a post to LinkedIn via browser automation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content":  {"type": "string", "description": "Post text (max 3000 chars)"},
                "headless": {"type": "boolean", "description": "Run browser headless (default: true)"},
            },
            "required": ["content"],
        },
    },
    "log_activity": {
        "fn": tool_log_activity,
        "description": "Append a business activity entry to Vault/Logs/Business.log",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Activity message to log"},
            },
            "required": ["message"],
        },
    },
}


# ─── MCP protocol helpers ─────────────────────────────────────────────────────

def _ok(req_id, result: object) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


# ─── MCP method handlers ──────────────────────────────────────────────────────

def handle_initialize(req_id, _params: dict) -> dict:
    return _ok(req_id, {
        "protocolVersion": "2024-11-05",
        "serverInfo": {"name": "business-mcp", "version": "1.0.0"},
        "capabilities": {"tools": {}},
    })


def handle_tools_list(req_id, _params: dict) -> dict:
    tools = [
        {
            "name": name,
            "description": info["description"],
            "inputSchema": info["inputSchema"],
        }
        for name, info in TOOL_REGISTRY.items()
    ]
    return _ok(req_id, {"tools": tools})


def handle_tools_call(req_id, params: dict) -> dict:
    name = params.get("name", "")
    arguments = params.get("arguments") or {}

    if name not in TOOL_REGISTRY:
        return _err(req_id, -32601, f"Unknown tool: '{name}'")

    try:
        result = TOOL_REGISTRY[name]["fn"](arguments)
        return _ok(req_id, {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            "isError": False,
        })
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        _log_server(f"Tool error [{name}]: {exc}")
        return _ok(req_id, {
            "content": [{"type": "text", "text": f"Error: {exc}"}],
            "isError": True,
        })
    except Exception as exc:  # noqa: BLE001
        _log_server(f"Unexpected error [{name}]: {traceback.format_exc()}")
        return _ok(req_id, {
            "content": [{"type": "text", "text": f"Unexpected error: {exc}"}],
            "isError": True,
        })


DISPATCH = {
    "initialize":                handle_initialize,
    "tools/list":                handle_tools_list,
    "tools/call":                handle_tools_call,
    "notifications/initialized": lambda rid, p: None,
}


# ─── main loop ────────────────────────────────────────────────────────────────

def main() -> None:
    _ensure_dirs()
    _load_env()
    _log_server("business-mcp server started (stdio)")

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue

        try:
            req = json.loads(raw)
        except json.JSONDecodeError as exc:
            _send(_err(None, -32700, f"Parse error: {exc}"))
            continue

        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params") or {}

        handler = DISPATCH.get(method)
        if handler is None:
            _send(_err(req_id, -32601, f"Method not found: '{method}'"))
            continue

        try:
            response = handler(req_id, params)
        except Exception as exc:  # noqa: BLE001
            response = _err(req_id, -32603, f"Internal error: {exc}")

        if response is not None:
            _send(response)


if __name__ == "__main__":
    main()
