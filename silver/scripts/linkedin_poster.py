#!/usr/bin/env python3
"""
LinkedIn Auto-Poster - Generate and publish LinkedIn content

Usage:
    python linkedin_poster.py --generate       # Generate new post
    python linkedin_poster.py --test           # Test with mock post
    python linkedin_poster.py --publish <id>   # Publish approved post
"""

import json
import random
from pathlib import Path
from datetime import datetime
import sys


class LinkedInPoster:
    """
    Generates and publishes LinkedIn content
    """

    def __init__(self, root_path=None, mock_mode=True):
        if root_path is None:
            self.root = Path(__file__).parent.parent
        else:
            self.root = Path(root_path)

        self.mock_mode = mock_mode

        # Paths
        self.needs_approval = self.root / "Needs_Approval"
        self.logs_dir = self.root / "logs"
        self.action_log = self.logs_dir / "actions.log"

        self._ensure_directories()
        self._load_templates()

    def _ensure_directories(self):
        """Create required directories"""
        for directory in [self.needs_approval, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_templates(self):
        """Load post templates"""
        self.templates = {
            "product_announcement": """🚀 Exciting News!

We're thrilled to announce {product_name}!

{key_benefits}

This means you can now:
✅ {benefit_1}
✅ {benefit_2}
✅ {benefit_3}

Learn more: {link}

#ProductLaunch #Innovation #Technology #AI #Automation""",

            "company_update": """💼 Company Update

We're excited to share that {achievement}!

{details}

Thank you to our amazing team and customers for making this possible.

#CompanyNews #Growth #TeamWork #Success""",

            "industry_insight": """💡 Industry Insight

{observation}

Here's what this means for {audience}:

{key_points}

What are your thoughts? Share in the comments!

#IndustryTrends #ThoughtLeadership #AI #Technology""",

            "team_highlight": """👏 Team Spotlight

Meet {name}, our {role}!

{bio}

We're proud to have {name} on our team!

#TeamCulture #EmployeeSpotlight #WorkLife""",

            "automation_success": """⚡ Automation Success Story

We've automated {process} and the results are impressive:

📊 {metric_1}
📊 {metric_2}
📊 {metric_3}

Automation isn't just about efficiency—it's about empowering our team to focus on what matters most.

Interested in automating your workflows? Let's talk!

#Automation #AIEmployee #Productivity #Innovation"""
        }

    def log(self, level, message):
        """Write to action log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}\n"

        with open(self.action_log, "a", encoding="utf-8") as f:
            f.write(entry)

        print(entry.strip())

    def generate_content(self, template_name="automation_success"):
        """Generate LinkedIn post content"""

        if template_name not in self.templates:
            template_name = random.choice(list(self.templates.keys()))

        template = self.templates[template_name]

        # Sample data for generation
        sample_data = {
            "product_name": "AI Employee Platform",
            "key_benefits": "Automated task management, intelligent decision-making, and seamless workflow integration.",
            "benefit_1": "Automate repetitive tasks",
            "benefit_2": "Get intelligent insights",
            "benefit_3": "Scale your operations",
            "link": "https://example.com/product",

            "achievement": "we've processed over 10,000 tasks autonomously",
            "details": "Our AI Employee has been working 24/7, handling emails, generating reports, and managing approvals with 99% accuracy.",

            "observation": "AI-powered automation is transforming how businesses operate.",
            "audience": "modern organizations",
            "key_points": """
• 40% increase in productivity
• 60% reduction in manual work
• 24/7 availability without burnout
• Consistent quality and accuracy
            """.strip(),

            "name": "Alex Johnson",
            "role": "AI Solutions Engineer",
            "bio": "Alex has been instrumental in building our AI Employee platform, bringing 10 years of experience in automation and machine learning.",

            "process": "email management and task routing",
            "metric_1": "500+ emails processed per day",
            "metric_2": "95% reduction in response time",
            "metric_3": "Zero missed follow-ups"
        }

        # Fill template
        try:
            content = template.format(**sample_data)
        except KeyError as e:
            content = template  # Use template as-is if missing data

        return content, template_name

    def create_approval_request(self, content, template_name):
        """Create approval request for LinkedIn post"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_post_{timestamp}.md"
        filepath = self.needs_approval / filename

        approval_content = f"""# Approval Request: LinkedIn Post

```yaml
type: linkedin_post
template: {template_name}
created_at: {datetime.now().isoformat()}
status: pending
visibility: public
```

## Post Content

{content}

---

## Metrics Target
- Expected reach: 1000+
- Expected engagement: 50+ reactions
- Expected comments: 10+

## Risk Assessment
**Risk Level:** MEDIUM

- This will be publicly visible
- Represents company brand
- Cannot be easily undone

---

## Manager Decision Required

⚠️ **This LinkedIn post requires your approval before publication.**

### How to Approve

Add this line:
```
DECISION: APPROVED
```

### How to Reject

Add this line with reason:
```
DECISION: REJECTED
Reason: [Your reason]
```

### Edit Content

If you want to modify the content, edit the "Post Content" section above before approving.

---

**Status:** Awaiting Decision
**Timeout:** 1 hour
**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(approval_content)

        self.log("LINKEDIN_POST", f"Created approval request: {filename}")
        self.log("LINKEDIN_POST", f"  Template: {template_name}")
        self.log("LINKEDIN_POST", f"  Length: {len(content)} characters")

        return filepath

    def publish_post(self, content):
        """Publish LinkedIn post (mock or real)"""
        if self.mock_mode:
            self.log("MOCK", "Mock publishing to LinkedIn")
            self.log("MOCK", f"Content preview: {content[:100]}...")

            return {
                "success": True,
                "post_id": f"mock_post_{int(datetime.now().timestamp())}",
                "url": "https://linkedin.com/posts/mock",
                "mock": True
            }
        else:
            # Real LinkedIn API publishing
            self.log("INFO", "Real LinkedIn API not yet implemented")
            return {
                "success": True,
                "post_id": f"simulated_{int(datetime.now().timestamp())}",
                "note": "Simulated - LinkedIn API not connected"
            }

    def generate_and_request_approval(self, template_name=None):
        """Generate post and create approval request"""
        self.log("START", "Generating LinkedIn post...")

        # Generate content
        content, template = self.generate_content(template_name)

        self.log("GENERATE", f"Generated post using template: {template}")

        # Create approval request
        filepath = self.create_approval_request(content, template)

        self.log("COMPLETE", f"Approval request created: {filepath.name}")

        return {
            "success": True,
            "approval_file": filepath.name,
            "template": template,
            "content_length": len(content)
        }

    def test_post(self):
        """Create a test post"""
        self.log("TEST", "Creating test LinkedIn post...")

        result = self.generate_and_request_approval("automation_success")

        print(f"\nTest post created!")
        print(f"  File: {result['approval_file']}")
        print(f"  Template: {result['template']}")
        print(f"\nNext steps:")
        print(f"1. Open Needs_Approval/{result['approval_file']}")
        print(f"2. Add: DECISION: APPROVED")
        print(f"3. Run MCP Executor to publish")

        return result


def main():
    """CLI interface"""
    poster = LinkedInPoster(mock_mode=True)

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--generate":
            template = None
            if len(sys.argv) > 3 and sys.argv[2] == "--template":
                template = sys.argv[3]

            result = poster.generate_and_request_approval(template)
            print(f"\nPost generated: {result['approval_file']}")

        elif command == "--test":
            poster.test_post()

        elif command == "--publish":
            if len(sys.argv) < 3:
                print("Usage: python linkedin_poster.py --publish <approval_id>")
                return

            approval_id = sys.argv[2]
            print(f"Publishing post {approval_id} (via MCP Executor)")
            print("Use MCP Executor to publish approved posts")

        else:
            print(f"Unknown command: {command}")
            print("Use: --generate, --test, or --publish")

    else:
        print("""
LinkedIn Auto-Poster - Content Generator

Usage:
  python linkedin_poster.py --generate                    # Generate new post
  python linkedin_poster.py --generate --template <name>  # Use specific template
  python linkedin_poster.py --test                        # Create test post
  python linkedin_poster.py --publish <id>                # Publish approved post

Templates:
  - product_announcement
  - company_update
  - industry_insight
  - team_highlight
  - automation_success (default)

Examples:
  # Generate post with default template
  python linkedin_poster.py --generate

  # Generate with specific template
  python linkedin_poster.py --generate --template "company_update"

  # Create test post
  python linkedin_poster.py --test
        """)


if __name__ == "__main__":
    main()
