# Agent Skills - Silver Tier

## What are Agent Skills?

Agent Skills are **modular AI logic functions** that encapsulate specific behaviors of the AI assistant. Each skill is a focused, reusable capability.

## Available Skills

### Input Processing
- **classify_input()** - Categorize incoming tasks
- **extract_metadata()** - Pull key info from inputs

### Planning & Reasoning
- **generate_plan()** - Create comprehensive Plan.md
- **prioritize_tasks()** - Assign urgency/importance
- **analyze_dependencies()** - Identify task relationships

### Content Generation
- **generate_linkedin_post()** - Create LinkedIn content
- **generate_email()** - Draft email responses
- **summarize_content()** - Create summaries

### Decision Making
- **needs_approval()** - Determine if action requires review
- **estimate_risk()** - Assess action risk level
- **suggest_actions()** - Recommend next steps

### Execution
- **send_email()** - Execute email sending
- **post_to_linkedin()** - Publish LinkedIn post
- **log_action()** - Record external actions

## Usage Pattern

```python
from Skills import skill_name

# Use a skill
result = skill_name.execute(input_data, context)
```

## Creating New Skills

1. Create `my_skill.py` in `Skills/` folder
2. Implement `execute(input_data, context)` function
3. Add docstring explaining purpose
4. Register in `__init__.py`

## Skill Template

```python
\"\"\"
Skill: My Custom Skill
Purpose: Brief description of what this skill does
\"\"\"

def execute(input_data, context=None):
    \"\"\"
    Main execution function

    Args:
        input_data: Input to process
        context: Optional context (dict)

    Returns:
        Result of skill execution
    \"\"\"
    # Your logic here
    return result
```

## Design Principles

- **Single Responsibility**: One skill = one capability
- **Stateless**: Skills don't store state between calls
- **Composable**: Skills can call other skills
- **Testable**: Each skill can be tested independently
- **Documented**: Clear docstrings and examples
