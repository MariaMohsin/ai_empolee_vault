# Skill: Task Planner (Silver Tier Preview)

## Trigger Phrase
When the user says: **"Make a plan for tasks"**

## Purpose
Analyze pending tasks and create a strategic execution plan before taking action.
This promotes thoughtful planning over reactive execution (Silver Tier reasoning).

## Inputs
- All markdown files in `/Needs_Action`
- Current context and priorities

## Behavior

### Step 1: Read All Pending Tasks
- Scan all files in `/Needs_Action`
- Extract task descriptions and requirements
- Note any dependencies or relationships

### Step 2: Analyze Task Types
Categorize tasks by:
- **Type**: Research, Writing, Data Processing, Testing, etc.
- **Complexity**: Simple, Moderate, Complex
- **Urgency**: Time-sensitive, Normal, Low priority
- **Dependencies**: What must be done first?

### Step 3: Create Plan Document
Generate a new file: `Plans/plan_<timestamp>.md`

Timestamp format: `YYYY-MM-DD_HH-MM-SS`

### Step 4: Plan Structure

```markdown
# Task Execution Plan
**Created:** <timestamp>
**Tasks Analyzed:** <count>

## Summary of Pending Tasks
- Brief list of all tasks with their types
- Current backlog size
- Notable patterns or themes

## Suggested Execution Order
1. Task Name (Reason for priority)
2. Task Name (Reason for priority)
3. ...

## Risks & Unclear Items
- Missing information or clarifications needed
- Potential blockers or challenges
- Assumptions being made

## Strategy
<2-3 paragraph narrative describing:>
- Overall approach to completing these tasks
- Grouping or batching strategy
- Quality vs. speed trade-offs
- How to handle dependencies
```

## Constraints
- **DO NOT** complete any tasks during planning
- **DO NOT** modify files in `/Needs_Action`
- **ONLY** create the plan document
- If `/Needs_Action` is empty, report "No tasks to plan"

## Output
- Create: `Plans/plan_<timestamp>.md`
- Report: "Plan created: plan_<timestamp>.md"
- Summary: Brief statement of findings

## Example Trigger
User: "Make a plan for tasks"
AI: [Reads Needs_Action → Analyzes → Creates Plan → Reports completion]

## Silver Tier Value
- Encourages **thinking before acting**
- Reveals **task relationships** and dependencies
- Allows **user review** before execution begins
- Demonstrates **strategic reasoning** capability

---

**Status:** Ready for Silver Tier
**Dependencies:** None
**Last Updated:** 2026-02-10
