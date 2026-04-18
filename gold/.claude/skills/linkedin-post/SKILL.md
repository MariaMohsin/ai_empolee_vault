# Skill: linkedin-post

Create real LinkedIn posts using browser automation (Playwright).

## Usage

```bash
python .claude/skills/linkedin-post/scripts/post_linkedin.py \
  --content "Your post content here"
```

## Setup

1. Install Playwright:
```bash
pip install playwright
playwright install chromium
```

2. Set environment variables:
```bash
export LINKEDIN_EMAIL="your-email@example.com"
export LINKEDIN_PASSWORD="your-password"
```

## Input Parameters

- `--content`: Post content text (required)
- `--headless`: Run in headless mode (optional, default: True)

## Output

Success: "LinkedIn post published successfully"
Error: "Failed to post: [error message]"

## Notes

- Uses Playwright for browser automation
- Logs into LinkedIn automatically
- Creates text-only posts
- Headless mode for production
- Visible browser for debugging (--headless=False)
- Takes ~10-15 seconds to complete
- Production-ready with error handling
