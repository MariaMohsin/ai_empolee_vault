from flask import Flask, jsonify, render_template_string
from pathlib import Path
from datetime import datetime
import json, os

app = Flask(__name__)

VAULT = Path("/vault")
LOGS  = Path("/logs")

def count(folder):
    p = VAULT / folder
    return len(list(p.glob("*.md"))) if p.exists() else 0

def read_health():
    h = VAULT / "Logs" / "system_health.md"
    if h.exists():
        text = h.read_text()
        if "HEALTHY" in text: return "✅ HEALTHY"
        if "DEGRADED" in text: return "🔴 DEGRADED"
    return "⚠️ UNKNOWN"

def last_log_line(logfile):
    f = LOGS / logfile
    if not f.exists(): return "No log yet"
    lines = f.read_text(errors="ignore").strip().splitlines()
    return lines[-1] if lines else "Empty"

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>AI Employee Dashboard</title>
  <meta http-equiv="refresh" content="30">
  <style>
    body { font-family: Arial, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:20px; }
    h1   { color:#38bdf8; border-bottom:1px solid #334155; padding-bottom:10px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin:20px 0; }
    .card { background:#1e293b; border-radius:10px; padding:20px; text-align:center; }
    .card .num  { font-size:2.5em; font-weight:bold; color:#38bdf8; }
    .card .label{ font-size:0.85em; color:#94a3b8; margin-top:5px; }
    .status { background:#1e293b; border-radius:10px; padding:20px; margin:10px 0; }
    .status h3 { margin:0 0 10px; color:#7dd3fc; }
    .log { font-family:monospace; font-size:0.78em; color:#94a3b8; word-break:break-all; }
    .badge-ok  { color:#4ade80; } .badge-warn { color:#facc15; } .badge-err { color:#f87171; }
    .footer { color:#475569; font-size:0.75em; margin-top:30px; }
    table { width:100%; border-collapse:collapse; }
    td,th { padding:8px 12px; border-bottom:1px solid #334155; text-align:left; }
    th { color:#7dd3fc; font-size:0.85em; }
  </style>
</head>
<body>
  <h1>🤖 AI Employee — Platinum Dashboard</h1>
  <p style="color:#64748b">Auto-refreshes every 30 seconds &nbsp;|&nbsp; {{ now }}</p>

  <div class="grid">
    <div class="card">
      <div class="num">{{ q.needs_email }}</div>
      <div class="label">📧 Needs Action (Email)</div>
    </div>
    <div class="card">
      <div class="num">{{ q.needs_social }}</div>
      <div class="label">📱 Needs Action (Social)</div>
    </div>
    <div class="card">
      <div class="num" style="color:#facc15">{{ q.pending }}</div>
      <div class="label">⏳ Pending Approval</div>
    </div>
    <div class="card">
      <div class="num" style="color:#4ade80">{{ q.approved }}</div>
      <div class="label">✅ Approved Queue</div>
    </div>
    <div class="card">
      <div class="num">{{ q.in_cloud }}</div>
      <div class="label">☁️ In Progress (Cloud)</div>
    </div>
    <div class="card">
      <div class="num">{{ q.in_local }}</div>
      <div class="label">💻 In Progress (Local)</div>
    </div>
    <div class="card">
      <div class="num" style="color:#4ade80">{{ q.done }}</div>
      <div class="label">🏁 Done</div>
    </div>
    <div class="card">
      <div class="num" style="color:#f87171">{{ q.errors }}</div>
      <div class="label">❌ Errors</div>
    </div>
  </div>

  <div class="status">
    <h3>System Status</h3>
    <table>
      <tr><th>Service</th><th>Status</th></tr>
      <tr><td>System Health</td><td>{{ health }}</td></tr>
      <tr><td>Odoo</td><td class="badge-ok">✅ http://localhost:8069</td></tr>
    </table>
  </div>

  <div class="status">
    <h3>Recent Logs</h3>
    <table>
      <tr><th>Log</th><th>Last Entry</th></tr>
      <tr><td>cloud_agent</td><td class="log">{{ logs.cloud }}</td></tr>
      <tr><td>approval_workflow</td><td class="log">{{ logs.approval }}</td></tr>
      <tr><td>watchdog</td><td class="log">{{ logs.watchdog }}</td></tr>
    </table>
  </div>

  <p class="footer">Platinum AI Employee &nbsp;|&nbsp; Vault: /vault &nbsp;|&nbsp; Logs: /logs</p>
</body>
</html>
"""

@app.route("/")
def index():
    q = {
        "needs_email":  count("Needs_Action/email"),
        "needs_social": count("Needs_Action/social"),
        "pending":      count("Pending_Approval/email") + count("Pending_Approval/social") + count("Pending_Approval/payment"),
        "approved":     count("Approved"),
        "in_cloud":     count("In_Progress/cloud"),
        "in_local":     count("In_Progress/local"),
        "done":         count("Done"),
        "errors":       count("Errors"),
    }
    logs = {
        "cloud":    last_log_line("cloud_agent.log"),
        "approval": last_log_line("approval_workflow.log"),
        "watchdog": last_log_line("watchdog.log"),
    }
    return render_template_string(HTML,
        q=q, health=read_health(), logs=logs,
        now=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

@app.route("/api/status")
def api_status():
    return jsonify({
        "needs_action": count("Needs_Action/email") + count("Needs_Action/social"),
        "pending":      count("Pending_Approval/email") + count("Pending_Approval/social"),
        "approved":     count("Approved"),
        "done":         count("Done"),
        "errors":       count("Errors"),
        "health":       read_health(),
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
