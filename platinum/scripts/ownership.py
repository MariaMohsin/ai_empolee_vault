#!/usr/bin/env python3
"""
ownership.py — Claim-by-move task ownership for Cloud and Local agents.

Rule: the first agent to atomically rename a file from /Needs_Action/<type>/
      into /In_Progress/<agent>/ owns it. All other agents must skip it.

All renames use os.replace() which is atomic on POSIX and best-effort on
Windows (same drive). On Linux VMs this is a true atomic claim.
"""

from __future__ import annotations

import os
import json
import time
from datetime import datetime
from pathlib import Path


AGENT_CLOUD = "cloud"
AGENT_LOCAL = "local"

# Task types — each maps to a sub-folder under Needs_Action and Pending_Approval
TASK_EMAIL  = "email"
TASK_SOCIAL = "social"
TASK_PAYMENT = "payment"
TASK_OTHER   = "other"


class OwnershipManager:

    def __init__(self, vault_root: Path) -> None:
        self.vault = vault_root
        self._ensure_structure()

    # ── directory bootstrap ────────────────────────────────────────────────────

    def _ensure_structure(self) -> None:
        for folder in [
            "Needs_Action/email",
            "Needs_Action/social",
            "Needs_Action/other",
            "Pending_Approval/email",
            "Pending_Approval/social",
            "Pending_Approval/payment",
            "Approved",
            "In_Progress/cloud",
            "In_Progress/local",
            "Done",
            "Errors",
        ]:
            (self.vault / folder).mkdir(parents=True, exist_ok=True)

    # ── claim ──────────────────────────────────────────────────────────────────

    def claim(self, task_file: Path, agent: str) -> Path | None:
        """
        Attempt to claim task_file by atomically moving it to
        In_Progress/<agent>/<filename>.

        Returns the new path on success, None if another agent beat us.
        """
        dest_dir = self.vault / "In_Progress" / agent
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / task_file.name

        try:
            # os.replace is atomic on POSIX (same filesystem).
            # If the source vanishes first, FileNotFoundError → another agent won.
            os.replace(task_file, dest)
            _stamp(dest, "claimed_by", agent)
            _stamp(dest, "claimed_at", _now())
            return dest
        except (FileNotFoundError, OSError):
            return None  # another agent already claimed it

    def release_to_done(self, task_file: Path) -> Path:
        """Move a claimed task to Done/."""
        dest = self.vault / "Done" / task_file.name
        _stamp(task_file, "completed_at", _now())
        os.replace(task_file, dest)
        return dest

    def release_to_error(self, task_file: Path, reason: str) -> Path:
        """Move a claimed task to Errors/."""
        dest = self.vault / "Errors" / task_file.name
        _stamp(task_file, "error_reason", reason)
        _stamp(task_file, "failed_at", _now())
        os.replace(task_file, dest)
        return dest

    def release_to_pending_approval(self, task_file: Path, task_type: str) -> Path:
        """Cloud releases a draft to Pending_Approval/<type>/."""
        dest_dir = self.vault / "Pending_Approval" / task_type
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / task_file.name
        _stamp(task_file, "pending_approval_at", _now())
        os.replace(task_file, dest)
        return dest

    def approve(self, pending_file: Path) -> Path:
        """Local moves a pending file to Approved/."""
        dest = self.vault / "Approved" / pending_file.name
        _stamp(pending_file, "approved_at", _now())
        os.replace(pending_file, dest)
        return dest

    def reject(self, pending_file: Path, reason: str = "") -> Path:
        """Local rejects a pending file → Done/ with rejected status."""
        dest = self.vault / "Done" / pending_file.name
        _stamp(pending_file, "rejected_at", _now())
        if reason:
            _stamp(pending_file, "rejection_reason", reason)
        os.replace(pending_file, dest)
        return dest

    # ── discovery ──────────────────────────────────────────────────────────────

    def available_tasks(self, task_type: str) -> list[Path]:
        """Return unclaimed tasks in Needs_Action/<type>/ sorted oldest-first."""
        folder = self.vault / "Needs_Action" / task_type
        if not folder.exists():
            return []
        return sorted(folder.glob("*.md"), key=lambda p: p.stat().st_mtime)

    def pending_approvals(self, task_type: str | None = None) -> list[Path]:
        """Return files waiting in Pending_Approval (optionally filtered by type)."""
        results = []
        base = self.vault / "Pending_Approval"
        types = [task_type] if task_type else [TASK_EMAIL, TASK_SOCIAL, TASK_PAYMENT]
        for t in types:
            folder = base / t
            if folder.exists():
                results.extend(sorted(folder.glob("*.md"), key=lambda p: p.stat().st_mtime))
        return results

    def approved_tasks(self) -> list[Path]:
        """Return files in Approved/ waiting for Local to execute."""
        folder = self.vault / "Approved"
        if not folder.exists():
            return []
        return sorted(folder.glob("*.md"), key=lambda p: p.stat().st_mtime)

    def in_progress(self, agent: str) -> list[Path]:
        """Return files currently claimed by agent."""
        folder = self.vault / "In_Progress" / agent
        if not folder.exists():
            return []
        return list(folder.glob("*.md"))


# ── helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp(md_file: Path, key: str, value: str) -> None:
    """Append a metadata line to a markdown file's YAML-ish header."""
    try:
        text = md_file.read_text(encoding="utf-8")
        # If line already exists, replace it
        lines = text.splitlines()
        tag = f"{key}:"
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith(tag):
                lines[i] = f"{key}: {value}"
                updated = True
                break
        if not updated:
            # Insert after the closing --- if YAML front-matter exists
            if lines and lines[0].strip() == "---":
                try:
                    close = lines.index("---", 1)
                    lines.insert(close, f"{key}: {value}")
                except ValueError:
                    lines.append(f"{key}: {value}")
            else:
                lines.append(f"{key}: {value}")
        md_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass  # file may be mid-move; non-fatal


def task_type_from_path(path: Path) -> str:
    """Infer task type from the file's parent folder name or filename prefix."""
    parent = path.parent.name
    if parent in (TASK_EMAIL, TASK_SOCIAL, TASK_PAYMENT):
        return parent
    # Fallback: detect from filename prefix (e.g. email-..., social-...)
    name = path.name.lower()
    if name.startswith("email"):
        return TASK_EMAIL
    if name.startswith("social") or name.startswith("linkedin"):
        return TASK_SOCIAL
    return TASK_OTHER
