# Silver Tier Implementation Roadmap

**Status:** In Progress
**Language:** Python
**Approach:** Modular, step-by-step

---

## ✅ Implementation Order

### Phase 1: Core Foundation (30 min)
- [x] Folder structure
- [ ] Logging system
- [ ] Agent Skills framework
- [ ] Configuration management

### Phase 2: Reasoning Loop (45 min)
- [ ] Plan generator
- [ ] Task analyzer
- [ ] Priority system
- [ ] Plan.md template

### Phase 3: Approval Workflow (30 min)
- [ ] Approval manager
- [ ] Approval templates
- [ ] Decision tracking

### Phase 4: Watchers (60 min)
- [ ] Gmail watcher (mock + real)
- [ ] LinkedIn watcher (simulation)
- [ ] Watcher orchestrator

### Phase 5: LinkedIn Posting (45 min)
- [ ] Post generator
- [ ] Template system
- [ ] Approval integration
- [ ] Mock poster (+ optional real Playwright)

### Phase 6: MCP Server (45 min)
- [ ] Email sender tool
- [ ] MCP server setup
- [ ] Tool registration

### Phase 7: Scheduling (30 min)
- [ ] Task scheduler
- [ ] Health check
- [ ] Auto-retry logic

### Phase 8: Integration (30 min)
- [ ] Main orchestrator
- [ ] End-to-end testing
- [ ] Documentation

---

**Total Estimated Time:** 4-5 hours
**Current Phase:** Phase 1

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         WATCHERS (Input Layer)          │
│  Gmail | LinkedIn | File | WhatsApp     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│              INBOX                       │
│        (All inputs land here)            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│        REASONING LOOP (Brain)            │
│  - Analyze tasks                         │
│  - Generate Plan.md                      │
│  - Determine priority                    │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
┌─────────────┐  ┌─────────────────┐
│Needs_Action │  │ Needs_Approval  │
│(Safe tasks) │  │(Risky actions)  │
└──────┬──────┘  └────────┬────────┘
       │                  │
       │         ┌────────▼────────┐
       │         │ Human Review    │
       │         └────────┬────────┘
       │                  │
       └──────┬───────────┘
              │
              ▼
      ┌───────────────┐
      │   EXECUTOR    │
      │  (MCP Server) │
      └───────┬───────┘
              │
              ▼
      ┌───────────────┐
      │     DONE      │
      └───────────────┘
```

---

## 📦 Component Specifications

### 1. Agent Skills (Modular AI Logic)
```python
skills/
├── classify_input.py      # Categorize incoming tasks
├── generate_plan.py       # Create Plan.md
├── prioritize_tasks.py    # Assign priority
├── linkedin_post.py       # Generate LinkedIn content
├── email_handler.py       # Process emails
└── approval_check.py      # Determine if needs approval
```

### 2. Watchers
```python
scripts/
├── watch_gmail.py         # Gmail integration
├── watch_linkedin.py      # LinkedIn monitoring
├── watch_file.py          # File-based (from Bronze)
└── watcher_orchestrator.py # Coordinate all watchers
```

### 3. Reasoning Loop
```python
scripts/
├── reasoning_engine.py    # Main reasoning system
└── plan_generator.py      # Generate Plan.md files
```

### 4. Approval System
```python
scripts/
├── approval_manager.py    # Manage approvals
└── decision_tracker.py    # Track decisions
```

### 5. MCP Server
```python
mcp_server/
├── server.py             # Main MCP server
├── tools/
│   ├── email_tool.py    # Send emails
│   └── log_tool.py      # External logging
└── config.json          # Server config
```

### 6. Scheduler
```python
scripts/
├── scheduler.py          # Main scheduler
├── health_check.py       # System health
└── retry_manager.py      # Retry failed tasks
```

---

## 🔧 Tech Stack

**Core:**
- Python 3.11+
- Standard library (minimal dependencies)

**Optional (if needed):**
- `schedule` - Task scheduling
- `playwright` - LinkedIn automation
- `google-api-python-client` - Gmail API
- `anthropic` - Claude API (if using MCP)

**Philosophy:** Start with stdlib, add dependencies only when necessary.

---

## 🎯 Success Criteria

Silver Tier complete when:
1. ✅ 2+ watchers converting inputs to Inbox
2. ✅ Reasoning loop generates Plan.md
3. ✅ Sensitive actions go to Needs_Approval
4. ✅ LinkedIn posts can be generated + approved
5. ✅ 1 MCP tool works (email or webhook)
6. ✅ Scheduler runs reasoning loop periodically
7. ✅ All logic in modular Agent Skills

---

**Next Step:** Implement Phase 1 - Core Foundation
