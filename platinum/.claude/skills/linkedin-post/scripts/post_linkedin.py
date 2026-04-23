#!/usr/bin/env python3
"""
post_linkedin.py — Post to LinkedIn via Playwright browser automation.

Usage:
  python post_linkedin.py --content "Post text here" [--headless|--no-headless]
  python post_linkedin.py --save-session        # Manual login + save cookies (run once)

Exit 0 = success, Exit 1 = failure.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

SESSION_FILE = Path(__file__).parent / "linkedin_session.json"


def save_session(email: str, password: str) -> None:
    """Open visible browser, let user complete login/2FA, then save cookies."""
    from playwright.sync_api import sync_playwright

    print("Opening browser for manual LinkedIn login...")
    print("Complete any security checks, then the session will be saved automatically.")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        page.fill("#username", email)
        page.fill("#password", password)
        page.click('button[type="submit"]')

        print("Waiting for you to reach the LinkedIn feed (complete any 2FA if prompted)...")
        try:
            page.wait_for_url("**/feed/**", timeout=120000)
        except Exception:
            pass

        if "feed" in page.url or "mynetwork" in page.url:
            cookies = context.cookies()
            SESSION_FILE.write_text(json.dumps(cookies), encoding="utf-8")
            print(f"Session saved to {SESSION_FILE}")
            print("SUCCESS: You can now run posts in headless mode.")
        else:
            print(f"ERROR: Did not reach feed. Current URL: {page.url}", file=sys.stderr)
            browser.close()
            sys.exit(1)

        browser.close()


def post_content(content: str, headless: bool) -> None:
    """Post to LinkedIn using saved session or fresh login."""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    email    = os.environ.get("LINKEDIN_EMAIL", "")
    password = os.environ.get("LINKEDIN_PASSWORD", "")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

        # Load saved session if available
        if SESSION_FILE.exists():
            cookies = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            context.add_cookies(cookies)
            print("Loaded saved session.")

        page = context.new_page()

        try:
            # Check if session is still valid
            print("Checking session...")
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            if "login" in page.url or "authwall" in page.url:
                # Session expired — try fresh login
                if not email or not password:
                    print("ERROR: Session expired and no credentials set.", file=sys.stderr)
                    browser.close()
                    sys.exit(1)

                print("Session expired, logging in again...")
                page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
                page.fill("#username", email)
                page.fill("#password", password)
                page.click('button[type="submit"]')
                try:
                    page.wait_for_url("**/feed/**", timeout=20000)
                except PWTimeout:
                    current = page.url
                    if "checkpoint" in current or "challenge" in current:
                        print("ERROR: LinkedIn security check required. Run: python post_linkedin.py --save-session", file=sys.stderr)
                        browser.close()
                        sys.exit(1)
                    print(f"ERROR: Login failed. URL: {current}", file=sys.stderr)
                    browser.close()
                    sys.exit(1)

            print("Session valid. Opening post dialog...")
            time.sleep(3)

            # Click "Start a post"
            start = page.locator('[aria-label="Start a post"]').first
            start.wait_for(state="visible", timeout=10000)
            start.click(timeout=5000)
            time.sleep(3)

            # Wait for post dialog
            dialog = page.locator('[role="dialog"]').first
            dialog.wait_for(state="visible", timeout=10000)

            # Type content into editor
            print("Typing post content...")
            editor = dialog.locator('div.ql-editor').first
            editor.wait_for(state="visible", timeout=8000)
            editor.click()
            editor.fill(content)
            time.sleep(1)

            # Click Post button inside dialog
            print("Submitting post...")
            post_btn = dialog.locator('button:has-text("Post")').last
            post_btn.wait_for(state="visible", timeout=5000)
            post_btn.click(timeout=5000)
            time.sleep(3)

            # Save updated cookies
            cookies = context.cookies()
            SESSION_FILE.write_text(json.dumps(cookies), encoding="utf-8")

            print("SUCCESS: LinkedIn post published.")
            browser.close()
            sys.exit(0)

        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            browser.close()
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", nargs="?", help="'login' to save session, or omit with --content to post")
    parser.add_argument("--content", help="Post content to publish")
    parser.add_argument("--headless", dest="headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    if args.mode == "login":
        email    = os.environ.get("LINKEDIN_EMAIL", "")
        password = os.environ.get("LINKEDIN_PASSWORD", "")
        if not email or not password:
            print("ERROR: LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in .env", file=sys.stderr)
            sys.exit(1)
        save_session(email, password)

    elif args.content:
        post_content(args.content, args.headless)

    else:
        print("ERROR: Provide 'login' or --content", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
