#!/usr/bin/env python3
"""
cleanup_errors.py — One-time cleanup of infinite RETRY_ chains in Errors/

Run once: python scripts/cleanup_errors.py
"""
from pathlib import Path
from datetime import datetime

ROOT   = Path(__file__).resolve().parent.parent
ERRORS = ROOT / "AI_Employee_Vault" / "Errors"

def cleanup():
    if not ERRORS.exists():
        print("No Errors/ folder found.")
        return

    removed = 0
    kept    = 0
    for f in list(ERRORS.glob("*.md")):
        retry_count = f.name.count("RETRY_")
        if retry_count > 1:
            # Keep only the first retry; delete deep chains
            f.unlink()
            print(f"  Removed (depth {retry_count}): {f.name[:80]}...")
            removed += 1
        else:
            kept += 1

    print(f"\nDone — removed {removed} infinite-retry files, kept {kept}.")

if __name__ == "__main__":
    cleanup()
