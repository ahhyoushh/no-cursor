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
- Implement workspace init (`nc init`)
- Implement `open` command
- Track open file in local state

### Files
- nc.py
- state.json

### Exit Criteria
- Workspace initializes safely
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
- Model responds deterministically

---

## Phase 3 — Ask Mode (Read-Only)

### Tasks
- Implement interactive `nc ask` shell
- Load file content once per session
- Enforce zero disk writes

### Exit Criteria
- Accurate file explanations
- No file modification possible

---

## Phase 4 — Edit Mode (Basic)

### Tasks
- Implement `nc edit "instruction"`
- Send file + instruction to model
- Force unified diff output

### Exit Criteria
- Valid unified diff generated
- Diff-only output enforced

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

### Exit Criteria
- Safe apply and rollback

---

## Phase 7 — Edit Instruction Shell (Post-MVP)

### Tasks
- Add optional interactive `nc edit` shell
- Allow multi-line natural language input
- Buffer instructions without calling model
- Generate diff only on explicit `generate`

### Rules
- One diff per session
- No iterative regeneration
- Abortable without side effects

### Exit Criteria
- Instruction shell produces same diffs as single-shot edit
- No additional autonomy introduced

---

## Phase 8 — Intent Normalization via Embeddings (Optional)

### Tasks
- Add local embedding model
- Implement fuzzy matching for constraints and goals
- Map natural language → fixed buckets
- Enforce confidence thresholds

### Constraints
- No intent generation
- No hidden behavior
- No scope expansion

### Exit Criteria
- Improved UX for informal language
- Identical model prompt semantics

---

## Phase 9 — UX Polish

### Tasks
- Improve CLI messages
- Add colorized diffs (optional)
- Better error reporting

### Exit Criteria
- Pleasant, clear CLI usage

---

## Phase 10 — Hardening

### Tasks
- Stress test with bad prompts
- Handle model failure cases
- Add timeouts and locks

### Exit Criteria
- Tool fails safely

---

## Final Deliverable

A local, free, single-file agentic code editor that:
- Never edits without approval
- Never touches more than one file
- Always produces diffs
- Remains understandable
