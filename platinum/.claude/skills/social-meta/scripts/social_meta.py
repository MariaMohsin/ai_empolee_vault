#!/usr/bin/env python3
"""
Facebook + Instagram Skill - Gold Tier (Meta Graph API)
Posts to Facebook Page and Instagram Business account.
Logs all activity to Logs/social.log

Usage:
    python social_meta.py --facebook "Your post content"
    python social_meta.py --instagram "Caption text" --image-url "https://..."
    python social_meta.py --instagram "Caption text"   # text-only via carousel
    python social_meta.py --mock --facebook "Test post"
    python social_meta.py --log-view
    python social_meta.py --stats

Environment variables (.env):
    META_PAGE_ID              Facebook Page ID
    META_PAGE_ACCESS_TOKEN    Page Access Token (long-lived)
    META_IG_USER_ID           Instagram Business Account ID
    META_IG_ACCESS_TOKEN      Instagram Access Token (same as page token usually)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError


# ── paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
LOGS_DIR = ROOT / "Logs"
SOCIAL_LOG = LOGS_DIR / "social.log"
VAULT = ROOT / "AI_Employee_Vault"

GRAPH_API = "https://graph.facebook.com/v19.0"


# ── env loader ────────────────────────────────────────────────────────────────

def _load_env() -> None:
    for candidate in [ROOT / ".env", Path(__file__).parent / ".env"]:
        if candidate.exists():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
            break


def _ensure_dirs() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


# ── logging ───────────────────────────────────────────────────────────────────

def _log(platform: str, msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(SOCIAL_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{platform.upper()}] {msg}\n")


# ── Graph API helper ──────────────────────────────────────────────────────────

def _graph_post(endpoint: str, data: dict) -> dict:
    url = f"{GRAPH_API}/{endpoint}"
    body = urllib_parse.urlencode(data).encode("utf-8")
    req = urllib_request.Request(url, data=body, method="POST")
    try:
        with urllib_request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Meta Graph API {exc.code}: {err_body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error reaching Meta API: {exc}") from exc


# ── Facebook post ─────────────────────────────────────────────────────────────

def post_facebook(content: str, mock: bool = False) -> dict:
    """
    Publish a text post to a Facebook Page.
    Returns {"post_id": str, "status": str}.
    """
    content = content.strip()
    if not content:
        raise ValueError("Post content cannot be empty")

    _ensure_dirs()

    if mock:
        post_id = f"mock_fb_{int(datetime.now().timestamp())}"
        _log("facebook", f"MOCK post: {content[:80]}")
        print(f"[MOCK] Facebook post: {content[:60]}...")
        return {"post_id": post_id, "status": "mock", "platform": "facebook"}

    page_id    = os.environ.get("META_PAGE_ID", "")
    page_token = os.environ.get("META_PAGE_ACCESS_TOKEN", "")

    if not page_id or not page_token:
        raise RuntimeError(
            "META_PAGE_ID and META_PAGE_ACCESS_TOKEN must be set in .env\n"
            "Get a Page Access Token from: https://developers.facebook.com/tools/explorer"
        )

    result = _graph_post(f"{page_id}/feed", {
        "message":      content,
        "access_token": page_token,
    })

    post_id = result.get("id", "unknown")
    _log("facebook", f"Posted: id={post_id} | {content[:80]}")
    print(f"[OK] Facebook post published: {post_id}")

    return {"post_id": post_id, "status": "posted", "platform": "facebook"}


# ── Instagram post ────────────────────────────────────────────────────────────

def post_instagram(caption: str, image_url: str = "", mock: bool = False) -> dict:
    """
    Publish to Instagram Business Account.
    image_url: required for photo posts; omit for text-only (carousel workaround).
    Returns {"media_id": str, "status": str}.
    """
    caption = caption.strip()
    if not caption:
        raise ValueError("Caption cannot be empty")

    _ensure_dirs()

    if mock:
        media_id = f"mock_ig_{int(datetime.now().timestamp())}"
        _log("instagram", f"MOCK post: {caption[:80]}")
        print(f"[MOCK] Instagram post: {caption[:60]}...")
        return {"media_id": media_id, "status": "mock", "platform": "instagram"}

    ig_user_id = os.environ.get("META_IG_USER_ID", "")
    ig_token   = os.environ.get("META_IG_ACCESS_TOKEN", "") or os.environ.get("META_PAGE_ACCESS_TOKEN", "")

    if not ig_user_id or not ig_token:
        raise RuntimeError(
            "META_IG_USER_ID and META_IG_ACCESS_TOKEN must be set in .env\n"
            "Guide: https://developers.facebook.com/docs/instagram-api/getting-started"
        )

    # Step 1: Create media container
    container_data: dict = {
        "caption":      caption,
        "access_token": ig_token,
    }
    if image_url:
        container_data["image_url"] = image_url
        container_data["media_type"] = "IMAGE"
    else:
        # Text-only: use REELS with no media is not supported by Graph API directly.
        # Best fallback: log a note and return graceful error.
        _log("instagram", f"SKIPPED (no image_url) caption: {caption[:80]}")
        print("[WARN] Instagram requires an image URL for photo posts.")
        print("       Add --image-url <public-image-url> to post.")
        return {
            "media_id": None,
            "status": "skipped_no_image",
            "platform": "instagram",
            "note": "Instagram API requires an image URL. Provide --image-url.",
        }

    container = _graph_post(f"{ig_user_id}/media", container_data)
    creation_id = container.get("id")
    if not creation_id:
        raise RuntimeError(f"Failed to create Instagram media container: {container}")

    # Step 2: Publish
    publish = _graph_post(f"{ig_user_id}/media_publish", {
        "creation_id":  creation_id,
        "access_token": ig_token,
    })

    media_id = publish.get("id", "unknown")
    _log("instagram", f"Posted: id={media_id} | {caption[:80]}")
    print(f"[OK] Instagram post published: {media_id}")

    return {"media_id": media_id, "status": "posted", "platform": "instagram"}


# ── log view / stats ──────────────────────────────────────────────────────────

def cmd_log_view() -> None:
    _ensure_dirs()
    if not SOCIAL_LOG.exists():
        print("No social.log entries yet.")
        return
    print(SOCIAL_LOG.read_text(encoding="utf-8"))


def cmd_stats() -> None:
    _ensure_dirs()
    if not SOCIAL_LOG.exists():
        print("No social.log entries yet.")
        return
    fb = ig = total = 0
    for line in SOCIAL_LOG.read_text(encoding="utf-8").splitlines():
        if "[FACEBOOK]" in line:
            fb += 1; total += 1
        elif "[INSTAGRAM]" in line:
            ig += 1; total += 1

    print(f"\n{'='*35}")
    print(f"  Meta Social Stats")
    print(f"{'='*35}")
    print(f"  Total    : {total}")
    print(f"  Facebook : {fb}")
    print(f"  Instagram: {ig}")
    print(f"  Log file : {SOCIAL_LOG}")
    print(f"{'='*35}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    _load_env()
    parser = argparse.ArgumentParser(description="Facebook + Instagram Skill - Gold Tier")
    parser.add_argument("--facebook",  metavar="CONTENT", help="Post to Facebook Page")
    parser.add_argument("--instagram", metavar="CAPTION", help="Post to Instagram")
    parser.add_argument("--image-url", metavar="URL",     help="Public image URL for Instagram photo post")
    parser.add_argument("--mock",      action="store_true", help="Mock mode (no real API calls)")
    parser.add_argument("--log-view",  action="store_true", help="View social.log")
    parser.add_argument("--stats",     action="store_true", help="Show post counts")
    args = parser.parse_args()

    if args.facebook:
        try:
            r = post_facebook(args.facebook, mock=args.mock)
            print(f"     post_id={r['post_id']}  status={r['status']}")
        except (ValueError, RuntimeError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr); sys.exit(1)

    elif args.instagram:
        try:
            r = post_instagram(args.instagram, image_url=args.image_url or "", mock=args.mock)
            if r.get("media_id"):
                print(f"     media_id={r['media_id']}  status={r['status']}")
            else:
                print(f"     status={r['status']}  note={r.get('note','')}")
        except (ValueError, RuntimeError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr); sys.exit(1)

    elif args.log_view:
        cmd_log_view()
    elif args.stats:
        cmd_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
