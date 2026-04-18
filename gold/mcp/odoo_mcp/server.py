#!/usr/bin/env python3
"""
odoo-mcp  |  Gold Tier MCP Server
Odoo 19 JSON-RPC integration via Model Context Protocol (stdio transport)

Exposed tools:
  create_invoice(partner, amount, description, currency)
  list_invoices(state, limit)
  record_payment(invoice_id, amount, journal)

Odoo JSON-RPC endpoint: http://<host>:<port>/web/dataset/call_kw
Auth:  /web/session/authenticate  (username + password + db)

Environment variables (add to .env):
  ODOO_URL       = http://localhost:8069
  ODOO_DB        = mycompany
  ODOO_USERNAME  = admin
  ODOO_PASSWORD  = admin

Run (registered via .claude/settings.json mcpServers):
    python mcp/odoo_mcp/server.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent.parent   # gold/
SERVER_LOG = ROOT / "Logs" / "odoo_mcp_server.log"


# ── bootstrap ─────────────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    SERVER_LOG.parent.mkdir(parents=True, exist_ok=True)


def _load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(SERVER_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except OSError:
        pass


# ── Odoo JSON-RPC client ──────────────────────────────────────────────────────

class OdooClient:
    """Minimal Odoo JSON-RPC client — no external dependencies."""

    def __init__(self) -> None:
        self.url      = os.environ.get("ODOO_URL", "http://localhost:8069").rstrip("/")
        self.db       = os.environ.get("ODOO_DB", "")
        self.username = os.environ.get("ODOO_USERNAME", "admin")
        self.password = os.environ.get("ODOO_PASSWORD", "admin")
        self.uid: int | None = None

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = self.url + endpoint
        data = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=15) as resp:
                body = resp.read()
                result = json.loads(body)
                if "error" in result:
                    raise RuntimeError(f"Odoo error: {result['error'].get('message', result['error'])}")
                return result.get("result", {})
        except URLError as exc:
            raise RuntimeError(f"Cannot reach Odoo at {self.url}: {exc}") from exc

    def authenticate(self) -> int:
        if self.uid is not None:
            return self.uid
        if not self.db:
            raise RuntimeError("ODOO_DB not set in .env")
        result = self._post("/web/session/authenticate", {
            "jsonrpc": "2.0", "method": "call", "id": 1,
            "params": {
                "db": self.db,
                "login": self.username,
                "password": self.password,
            },
        })
        uid = result.get("uid")
        if not uid:
            raise RuntimeError("Odoo authentication failed — check credentials")
        self.uid = uid
        _log(f"Authenticated as uid={uid}")
        return uid

    def call_kw(self, model: str, method: str, args: list, kwargs: dict | None = None) -> object:
        uid = self.authenticate()
        return self._post("/web/dataset/call_kw", {
            "jsonrpc": "2.0", "method": "call", "id": 1,
            "params": {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": kwargs or {},
                "context": {},
            },
        })


# ── tool implementations ───────────────────────────────────────────────────────

_client: OdooClient | None = None


def _get_client() -> OdooClient:
    global _client
    if _client is None:
        _client = OdooClient()
    return _client


def tool_create_invoice(args: dict) -> dict:
    """
    Create a customer invoice (account.move) in Odoo.
    Required: partner (name or id), amount, description
    Optional: currency (default USD)
    """
    partner_input = str(args.get("partner", "")).strip()
    amount        = float(args.get("amount", 0))
    description   = str(args.get("description", "Invoice")).strip()
    currency_name = str(args.get("currency", "USD")).strip().upper()

    if not partner_input:
        raise ValueError("'partner' is required")
    if amount <= 0:
        raise ValueError("'amount' must be positive")

    client = _get_client()

    # Resolve partner id
    if partner_input.isdigit():
        partner_id = int(partner_input)
    else:
        ids = client.call_kw("res.partner", "search",
                             [[["name", "ilike", partner_input]]], {"limit": 1})
        if not ids:
            raise RuntimeError(f"Partner '{partner_input}' not found in Odoo")
        partner_id = ids[0]

    # Resolve currency id
    currency_ids = client.call_kw("res.currency", "search",
                                  [[["name", "=", currency_name]]], {"limit": 1})
    currency_id = currency_ids[0] if currency_ids else False

    # Build invoice vals
    invoice_vals = {
        "move_type":   "out_invoice",
        "partner_id":  partner_id,
        "currency_id": currency_id,
        "invoice_line_ids": [(0, 0, {
            "name":       description,
            "quantity":   1.0,
            "price_unit": amount,
        })],
    }

    invoice_id = client.call_kw("account.move", "create", [invoice_vals])
    _log(f"Invoice created: id={invoice_id} partner={partner_input} amount={amount}")

    return {
        "status":     "created",
        "invoice_id": invoice_id,
        "partner":    partner_input,
        "amount":     amount,
        "currency":   currency_name,
        "description": description,
    }


def tool_list_invoices(args: dict) -> dict:
    """
    List invoices from Odoo.
    Optional: state (draft/posted/cancel/all), limit (default 20)
    """
    state = str(args.get("state", "posted")).lower()
    limit = int(args.get("limit", 20))

    client = _get_client()

    domain: list = [["move_type", "=", "out_invoice"]]
    if state != "all":
        domain.append(["state", "=", state])

    ids = client.call_kw("account.move", "search", [domain], {"limit": limit})
    if not ids:
        return {"invoices": [], "count": 0}

    records = client.call_kw(
        "account.move", "read", [ids],
        {"fields": ["name", "partner_id", "amount_total", "currency_id",
                    "state", "invoice_date", "invoice_date_due"]},
    )

    invoices = []
    for r in records:
        invoices.append({
            "id":          r["id"],
            "name":        r.get("name", ""),
            "partner":     r["partner_id"][1] if r.get("partner_id") else "",
            "amount":      r.get("amount_total", 0),
            "currency":    r["currency_id"][1] if r.get("currency_id") else "",
            "state":       r.get("state", ""),
            "date":        r.get("invoice_date", ""),
            "due_date":    r.get("invoice_date_due", ""),
        })

    _log(f"Listed {len(invoices)} invoices (state={state})")
    return {"invoices": invoices, "count": len(invoices)}


def tool_record_payment(args: dict) -> dict:
    """
    Register payment for an invoice.
    Required: invoice_id, amount
    Optional: journal (default 'Bank')
    """
    invoice_id  = int(args.get("invoice_id", 0))
    amount      = float(args.get("amount", 0))
    journal_name = str(args.get("journal", "Bank")).strip()

    if not invoice_id:
        raise ValueError("'invoice_id' is required")
    if amount <= 0:
        raise ValueError("'amount' must be positive")

    client = _get_client()

    # Resolve journal
    journal_ids = client.call_kw("account.journal", "search",
                                  [[["name", "ilike", journal_name],
                                    ["type", "in", ["bank", "cash"]]]], {"limit": 1})
    if not journal_ids:
        raise RuntimeError(f"Journal '{journal_name}' not found in Odoo")
    journal_id = journal_ids[0]

    # Create payment wizard
    payment_vals = {
        "invoice_ids": [(4, invoice_id)],
        "journal_id":  journal_id,
        "amount":      amount,
        "payment_date": datetime.now().strftime("%Y-%m-%d"),
        "payment_type": "inbound",
        "partner_type": "customer",
    }

    payment_id = client.call_kw("account.payment", "create", [payment_vals])
    # Post the payment
    client.call_kw("account.payment", "action_post", [[payment_id]])

    _log(f"Payment recorded: invoice={invoice_id} amount={amount} journal={journal_name}")

    return {
        "status":     "payment_recorded",
        "payment_id": payment_id,
        "invoice_id": invoice_id,
        "amount":     amount,
        "journal":    journal_name,
    }


# ── tool registry ──────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, dict] = {
    "create_invoice": {
        "fn": tool_create_invoice,
        "description": "Create a customer invoice in Odoo",
        "inputSchema": {
            "type": "object",
            "properties": {
                "partner":     {"type": "string",  "description": "Customer name or Odoo partner ID"},
                "amount":      {"type": "number",  "description": "Invoice total amount"},
                "description": {"type": "string",  "description": "Line item description"},
                "currency":    {"type": "string",  "description": "Currency code (default: USD)"},
            },
            "required": ["partner", "amount", "description"],
        },
    },
    "list_invoices": {
        "fn": tool_list_invoices,
        "description": "List customer invoices from Odoo",
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": {"type": "string", "enum": ["draft", "posted", "cancel", "all"],
                          "description": "Invoice state filter (default: posted)"},
                "limit": {"type": "integer", "description": "Max records to return (default: 20)"},
            },
        },
    },
    "record_payment": {
        "fn": tool_record_payment,
        "description": "Register a payment against an Odoo invoice",
        "inputSchema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer", "description": "Odoo invoice ID"},
                "amount":     {"type": "number",  "description": "Payment amount"},
                "journal":    {"type": "string",  "description": "Payment journal name (default: Bank)"},
            },
            "required": ["invoice_id", "amount"],
        },
    },
}


# ── MCP protocol ───────────────────────────────────────────────────────────────

def _ok(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}

def _err(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

def _send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def handle_initialize(req_id, _p):
    return _ok(req_id, {
        "protocolVersion": "2024-11-05",
        "serverInfo": {"name": "odoo-mcp", "version": "1.0.0"},
        "capabilities": {"tools": {}},
    })

def handle_tools_list(req_id, _p):
    return _ok(req_id, {"tools": [
        {"name": n, "description": i["description"], "inputSchema": i["inputSchema"]}
        for n, i in TOOL_REGISTRY.items()
    ]})

def handle_tools_call(req_id, params):
    name = params.get("name", "")
    arguments = params.get("arguments") or {}
    if name not in TOOL_REGISTRY:
        return _err(req_id, -32601, f"Unknown tool: '{name}'")
    try:
        result = TOOL_REGISTRY[name]["fn"](arguments)
        return _ok(req_id, {"content": [{"type": "text", "text": json.dumps(result, indent=2)}], "isError": False})
    except Exception as exc:
        _log(f"Tool error [{name}]: {traceback.format_exc()}")
        return _ok(req_id, {"content": [{"type": "text", "text": f"Error: {exc}"}], "isError": True})

DISPATCH = {
    "initialize":                handle_initialize,
    "tools/list":                handle_tools_list,
    "tools/call":                handle_tools_call,
    "notifications/initialized": lambda r, p: None,
}

def main() -> None:
    _ensure_dirs()
    _load_env()
    _log("odoo-mcp server started (stdio)")
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
            resp = handler(req_id, params)
        except Exception as exc:
            resp = _err(req_id, -32603, str(exc))
        if resp is not None:
            _send(resp)

if __name__ == "__main__":
    main()
