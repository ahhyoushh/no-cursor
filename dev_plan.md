# no-cursor (nc)
### Detailed Development Plan

---

## Phase 0 — Preparation

### Tasks
- Finalize scope (single-file only)
- Lock constraints
- Choose model and runtime

### Output
- Frozen requirements
- No scope creep allowed

---

## Phase 1 — Core CLI Skeleton

### Tasks
- Implement `nc` CLI entry point
- Implement `open` command
- Track open file in local state

### Files
- nc.py
- state.json

### Exit Criteria
- File can be opened and tracked

---

## Phase 2 — LLM Integration

### Tasks
- Integrate Ollama CLI calls
- Create LLM wrapper module
- Hard-code system prompt rules

### Files
- llm.py
- prompts.py

### Exit Criteria
- Model responds to prompts reliably

---

## Phase 3 — Ask Mode (Read-Only)

### Tasks
- Send file content + question to LLM
- Display explanation output
- Enforce no-edit behavior

### Commands
```bash
nc ask "question"
```

### Exit Criteria
- Accurate file explanations
- No file modification

---

## Phase 4 — Edit Mode (Diff Generation)

### Tasks
- Send file + instruction
- Force unified diff output
- Reject prose or invalid output

### Commands
```bash
nc edit "instruction"
```

### Exit Criteria
- Valid unified diff generated
- Diff only, no commentary

---

## Phase 5 — Diff Validation

### Tasks
- Validate diff format
- Enforce line-change limits
- Ensure correct file path

### Files
- diff_utils.py
- validators.py

### Exit Criteria
- Unsafe diffs rejected automatically

---

## Phase 6 — Apply / Revert

### Tasks
- Apply validated patch
- Create backup before apply
- Implement revert command

### Commands
```bash
nc apply
nc revert
```

### Exit Criteria
- Safe apply and rollback

---

## Phase 7 — UX Polish

### Tasks
- Improve CLI messages
- Add colorized diffs (optional)
- Better error reporting

### Exit Criteria
- Pleasant, clear CLI usage

---

## Phase 8 — Hardening

### Tasks
- Stress test with bad prompts
- Handle model failure cases
- Add timeouts

### Exit Criteria
- Tool fails safely

---

## Final Deliverable

A local, free, single-file agentic code editor that:
- Never edits without approval
- Never touches more than one file
- Always produces diffs
- Remains understandable

---
