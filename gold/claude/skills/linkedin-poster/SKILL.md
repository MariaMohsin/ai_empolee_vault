# Skill: LinkedIn Auto-Poster

## Metadata
```yaml
name: linkedin-poster
type: content_generator
tier: silver
status: active
version: 1.0.0
created: 2026-04-17
```

## Goal
Automatically generate professional LinkedIn posts for business development, request human approval, and publish approved content.

---

## Core Responsibilities

### 1. Content Generation
- Generate business-focused posts
- Follow company voice/tone
- Include relevant hashtags
- Optimize for engagement

### 2. Post Templates
- Product announcements
- Company updates
- Industry insights
- Thought leadership
- Team highlights

### 3. Approval Workflow
- Create approval request
- Wait for manager review
- Publish only after approval
- Track published posts

### 4. Publishing
- **Mock Mode**: Simulated posting (testing)
- **API Mode**: Real LinkedIn API (production)
- **Playwright Mode**: Browser automation (alternative)

---

## Content Templates

### 1. Product Announcement
```
🚀 Exciting News!

We're thrilled to announce [Product/Feature]!

[Key benefits - 2-3 bullet points]

This means you can now:
✅ [Benefit 1]
✅ [Benefit 2]
✅ [Benefit 3]

Learn more: [Link]

#ProductLaunch #Innovation #Technology
```

### 2. Company Update
```
💼 Company Update

We're excited to share that [Achievement/Milestone]!

[Details about the update]

Thank you to our amazing team and customers for making this possible.

#CompanyNews #Growth #TeamWork
```

### 3. Industry Insight
```
💡 Industry Insight

[Interesting observation or trend]

Here's what this means for [your industry/audience]:

[3-5 key points]

What are your thoughts? Share in the comments!

#IndustryTrends #ThoughtLeadership #[YourIndustry]
```

### 4. Team Highlight
```
👏 Team Spotlight

Meet [Name], our [Role]!

[Brief bio and achievements]

We're proud to have [Name] on our team!

#TeamCulture #EmployeeSpotlight #WorkLife
```

---

## Workflow

```
1. GENERATE CONTENT
   ↓
2. CREATE APPROVAL REQUEST
   ↓
3. SAVE TO Needs_Approval/
   ↓
4. WAIT FOR MANAGER APPROVAL
   ↓
5. IF APPROVED → PUBLISH
   IF REJECTED → LOG & SKIP
   IF TIMEOUT → CANCEL
   ↓
6. LOG PUBLICATION
   ↓
7. TRACK METRICS
```

---

## Configuration

```json
{
  "linkedin": {
    "mode": "mock",
    "post_frequency": "daily",
    "auto_generate": true,
    "approval_timeout": 3600
  },
  "content": {
    "templates": [
      "product_announcement",
      "company_update",
      "industry_insight",
      "team_highlight"
    ],
    "hashtags": {
      "default": ["#AI", "#Automation", "#Technology"],
      "max_count": 5
    },
    "tone": "professional",
    "max_length": 3000
  },
  "publishing": {
    "visibility": "public",
    "comments_enabled": true,
    "track_metrics": true
  }
}
```

---

## Usage

### Generate Post
```bash
python scripts/linkedin_poster.py --generate --template "product_announcement"
```

### Publish Approved Post
```bash
python scripts/linkedin_poster.py --publish <approval_id>
```

### Test Mode
```bash
python scripts/linkedin_poster.py --test
```

---

## Example Flow

### Step 1: Generate Content
```bash
python scripts/linkedin_poster.py --generate
```

**Output:** Creates approval request in Needs_Approval/

### Step 2: Manager Reviews
Opens `Needs_Approval/linkedin_post_*.md`:
```markdown
# Approval Request: LinkedIn Post

## Post Content

🚀 Exciting news from our team!

We've just launched our AI-powered automation platform...

[Full post content]

## Decision Required

DECISION: [Add APPROVED or REJECTED]
```

Manager adds: `DECISION: APPROVED`

### Step 3: Auto-Publish
MCP Executor detects approval and publishes

---

## Dependencies

**Mock Mode:** None (built-in)

**API Mode:**
```bash
pip install linkedin-api
```

**Playwright Mode:**
```bash
pip install playwright
playwright install chromium
```

---

**Status:** ✅ Ready (Mock Mode)
**API Setup:** Optional (for production)
