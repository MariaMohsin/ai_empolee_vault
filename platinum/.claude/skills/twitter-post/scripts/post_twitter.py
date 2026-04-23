#!/usr/bin/env python3
"""
Twitter/X Post Skill - Gold Tier
Posts tweets via Twitter API v2 and saves history to Reports/Twitter_History.md

Usage:
    python post_twitter.py --content "Your tweet text"
    python post_twitter.py --content "Tweet" --mock
    python post_twitter.py --history
    python post_twitter.py --stats

Environment variables (.env):
    TWITTER_API_KEY            Twitter API Key (Consumer Key)
    TWITTER_API_SECRET         Twitter API Secret (Consumer Secret)
    TWITTER_ACCESS_TOKEN       Access Token
    TWITTER_ACCESS_TOKEN_SECRET Access Token Secret
    TWITTER_BEARER_TOKEN       Bearer Token (for read operations)
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
from base64 import b64encode
from datetime import datetime
from pathlib import Path
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError


# ── paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
VAULT = ROOT / "AI_Employee_Vault"
REPORTS_DIR = VAULT / "Reports"
TWITTER_HISTORY = REPORTS_DIR / "Twitter_History.md"
LOGS_DIR = ROOT / "Logs"
SOCIAL_LOG = LOGS_DIR / "social.log"

TWITTER_API_V2 = "https://api.twitter.com/2/tweets"
MAX_TWEET_LENGTH = 280


# ── env loader ────────────────────────────────────────────────────────────────

def _load_env() -> None:
    for candidate in [
        ROOT / ".env",
        Path(__file__).parent / ".env",
    ]:
        if candidate.exists():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
            break


def _ensure_dirs() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


# ── logging ───────────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(SOCIAL_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [TWITTER] {msg}\n")


# ── OAuth 1.0a helper ─────────────────────────────────────────────────────────

def _oauth1_header(method: str, url: str, params: dict) -> str:
    """Build OAuth 1.0a Authorization header for Twitter API v2."""
    api_key    = os.environ.get("TWITTER_API_KEY", "")
    api_secret = os.environ.get("TWITTER_API_SECRET", "")
    token      = os.environ.get("TWITTER_ACCESS_TOKEN", "")
    token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")

    ts    = str(int(time.time()))
    nonce = b64encode(os.urandom(32)).decode("utf-8").rstrip("=")

    oauth_params = {
        "oauth_consumer_key":     api_key,
        "oauth_nonce":            nonce,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        ts,
        "oauth_token":            token,
        "oauth_version":          "1.0",
    }

    # Signature base string
    all_params = {**params, **oauth_params}
    sorted_params = "&".join(
        f"{urllib_parse.quote(k, safe='')}={urllib_parse.quote(str(v), safe='')}"
        for k, v in sorted(all_params.items())
    )
    base_string = "&".join([
        method.upper(),
        urllib_parse.quote(url, safe=""),
        urllib_parse.quote(sorted_params, safe=""),
    ])

    signing_key = f"{urllib_parse.quote(api_secret, safe='')}&{urllib_parse.quote(token_secret, safe='')}"
    signature = b64encode(
        hmac.new(signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1).digest()
    ).decode("utf-8")

    oauth_params["oauth_signature"] = signature
    header = "OAuth " + ", ".join(
        f'{urllib_parse.quote(k, safe="")}="{urllib_parse.quote(str(v), safe="")}"'
        for k, v in sorted(oauth_params.items())
    )
    return header


# ── Twitter API call ──────────────────────────────────────────────────────────

def _post_tweet_real(content: str) -> dict:
    """Post a tweet via Twitter API v2 using OAuth 1.0a."""
    api_key = os.environ.get("TWITTER_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "Twitter credentials not configured.\n"
            "Add to .env: TWITTER_API_KEY, TWITTER_API_SECRET, "
            "TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET"
        )

    body = json.dumps({"text": content}).encode("utf-8")
    auth_header = _oauth1_header("POST", TWITTER_API_V2, {})

    req = urllib_request.Request(
        TWITTER_API_V2,
        data=body,
        headers={
            "Authorization":  auth_header,
            "Content-Type":   "application/json",
            "User-Agent":     "AIEmployee-GoldTier/1.0",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read())
            tweet_id = result.get("data", {}).get("id", "unknown")
            return {"tweet_id": tweet_id, "text": content}
    except HTTPError as exc:
        body_err = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Twitter API {exc.code}: {body_err}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def _post_tweet_mock(content: str) -> dict:
    mock_id = f"mock_{int(time.time())}"
    print(f"[MOCK] Tweet would be posted: {content[:60]}...")
    return {"tweet_id": mock_id, "text": content, "mock": True}


# ── history log ───────────────────────────────────────────────────────────────

def _init_history() -> None:
    if TWITTER_HISTORY.exists():
        return
    TWITTER_HISTORY.write_text(
        "# Twitter Post History\n\n"
        "> Auto-maintained by twitter-post skill.\n\n"
        "---\n\n"
        "## Posts\n\n"
        "| Date | Tweet ID | Preview | Status |\n"
        "|------|----------|---------|--------|\n"
        "\n---\n\n"
        "## Full Content\n\n"
        f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
        encoding="utf-8",
    )


def _save_to_history(content: str, tweet_id: str, status: str) -> None:
    _init_history()
    raw = TWITTER_HISTORY.read_text(encoding="utf-8")
    date = datetime.now().strftime("%Y-%m-%d")
    preview = content[:55] + "..." if len(content) > 55 else content
    table_row = f"| {date} | {tweet_id} | {preview} | {status} |"

    lines = raw.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("|---"):
            lines.insert(i + 1, table_row)
            break
    raw = "\n".join(lines)

    block = (
        f"\n### {tweet_id} — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"**Status:** {status}\n\n"
        f"> {content}\n\n"
        f"{'-'*50}\n"
    )
    ts_line = f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
    if "*Last updated:" in raw:
        raw = raw[:raw.rfind("*Last updated:")] + block + ts_line + "\n"
    else:
        raw += block + "\n" + ts_line + "\n"

    TWITTER_HISTORY.write_text(raw, encoding="utf-8")


# ── public function ───────────────────────────────────────────────────────────

def post_tweet(content: str, mock: bool = False) -> dict:
    """
    Post a tweet. Returns result dict.
    Saves to Reports/Twitter_History.md and Logs/social.log.
    """
    content = content.strip()
    if not content:
        raise ValueError("Tweet content cannot be empty")
    if len(content) > MAX_TWEET_LENGTH:
        raise ValueError(f"Tweet exceeds {MAX_TWEET_LENGTH} characters ({len(content)})")

    _ensure_dirs()

    if mock:
        result = _post_tweet_mock(content)
        status = "mock"
    else:
        result = _post_tweet_real(content)
        status = "posted"

    tweet_id = result.get("tweet_id", "unknown")
    _save_to_history(content, tweet_id, status)
    _log(f"Tweet {status}: id={tweet_id} | {content[:60]}")

    return {**result, "status": status, "history_file": str(TWITTER_HISTORY)}


# ── CLI commands ──────────────────────────────────────────────────────────────

def cmd_history() -> None:
    _ensure_dirs()
    _init_history()
    print(TWITTER_HISTORY.read_text(encoding="utf-8"))


def cmd_stats() -> None:
    _ensure_dirs()
    _init_history()
    raw = TWITTER_HISTORY.read_text(encoding="utf-8")
    total = sum(1 for l in raw.splitlines()
                if l.startswith("| ") and "Tweet ID" not in l and "---" not in l)
    print(f"\nTwitter History: {total} tweet(s) logged")
    print(f"File: {TWITTER_HISTORY}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    _load_env()
    parser = argparse.ArgumentParser(description="Twitter Post Skill - Gold Tier")
    parser.add_argument("--content",  help="Tweet text (max 280 chars)")
    parser.add_argument("--mock",     action="store_true", help="Mock mode (no real API call)")
    parser.add_argument("--history",  action="store_true", help="Show tweet history")
    parser.add_argument("--stats",    action="store_true", help="Show tweet count")
    args = parser.parse_args()

    if args.content:
        try:
            result = post_tweet(args.content, mock=args.mock)
            print(f"[OK] Tweet {result['status']}: id={result['tweet_id']}")
            print(f"     History: {result['history_file']}")
        except (ValueError, RuntimeError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            sys.exit(1)
    elif args.history:
        cmd_history()
    elif args.stats:
        cmd_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
