#!/usr/bin/env python3
"""
LinkedIn Post Publisher - Production Implementation
Creates real LinkedIn posts using Playwright browser automation
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Auto-load .env from project root
def _load_env():
    for candidate in [
        Path(__file__).parent.parent.parent.parent.parent / ".env",
        Path(__file__).parent / ".env",
    ]:
        if candidate.exists():
            with open(candidate) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ.setdefault(key.strip(), val.strip())
            break

_load_env()

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None
    PlaywrightTimeout = Exception


def post_to_linkedin(content, headless=True):
    """
    Post content to LinkedIn using browser automation

    Args:
        content: Post text content
        headless: Run browser in headless mode

    Returns:
        dict: {"success": bool, "message": str}
    """
    # Check if Playwright is available
    if not PLAYWRIGHT_AVAILABLE:
        return {
            "success": False,
            "message": "Playwright not installed. Run: pip install playwright && playwright install chromium"
        }

    # Get credentials from environment
    email = os.environ.get("LINKEDIN_EMAIL")
    password = os.environ.get("LINKEDIN_PASSWORD")

    if not email or not password:
        return {
            "success": False,
            "message": "Missing LINKEDIN_EMAIL or LINKEDIN_PASSWORD environment variables"
        }

    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()

            # Navigate to LinkedIn
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            time.sleep(2)

            # Login
            page.fill('input[id="username"]', email)
            page.fill('input[id="password"]', password)
            page.click('button[type="submit"]')

            # Wait for feed to load
            try:
                page.wait_for_selector('button[aria-label*="Start a post"]', timeout=15000)
            except PlaywrightTimeout:
                browser.close()
                return {
                    "success": False,
                    "message": "Login failed or feed did not load. Check credentials."
                }

            time.sleep(2)

            # Click "Start a post" button
            page.click('button[aria-label*="Start a post"]')
            time.sleep(2)

            # Wait for post editor to appear
            try:
                page.wait_for_selector('div[role="textbox"]', timeout=10000)
            except PlaywrightTimeout:
                browser.close()
                return {
                    "success": False,
                    "message": "Post editor did not appear"
                }

            # Type content
            editor = page.locator('div[role="textbox"]').first
            editor.click()
            editor.fill(content)
            time.sleep(1)

            # Click Post button
            post_button = page.locator('button:has-text("Post")').first
            post_button.click()

            # Wait for post to be published
            time.sleep(3)

            browser.close()

            return {
                "success": True,
                "message": "LinkedIn post published successfully"
            }

    except ImportError:
        return {
            "success": False,
            "message": "Playwright not installed. Run: pip install playwright && playwright install chromium"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to post: {str(e)}"
        }


def main():
    parser = argparse.ArgumentParser(description="Post to LinkedIn using browser automation")
    parser.add_argument("--content", required=True, help="Post content text")
    parser.add_argument(
        "--headless",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Run in headless mode (default: True)"
    )

    args = parser.parse_args()

    # Post to LinkedIn
    result = post_to_linkedin(content=args.content, headless=args.headless)

    # Print result
    print(result["message"])

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
