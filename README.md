# no-cursor (nc)
### High-Level Plan — Agentic Code Editor (CLI-First, Local-Only)

---

## 1. Overview

**no-cursor** (`nc`) is a minimal, local, and free agentic code editor controlled entirely via the CLI.
VS Code acts only as a passive viewer for files, diffs, and test results.
 
Plan to make it vim or nvim.
The system is intentionally constrained to ensure completely local usage and reliability.

---

## 2. Core Goals

- Single-file intelligence
- Diff-only edits
- Fully local execution
- Predictable behavior
- Zero cloud dependency

---

## 3. Non-Goals

- Multi-file reasoning
- Autonomous planning
- API-based models
- IDE replacement
- Long-term memory

---

## 4. User Workflow

```bash
nc open src/example.py
nc ask "what does this file do?"
nc edit "add basic input validation"
nc diff
nc apply
```

---

## 5. Design Principles

- Constraints over autonomy
- Transparency over magic
- User-in-the-loop always
- Safety enforced in code

---

## 6. Architecture (High Level)

CLI → State → Prompt Engine → Local LLM → Diff → Validator → Apply/Revert

---

## 7. Model Strategy

- Model: Qwen2.5-Coder 7B Instruct
- Runtime: Ollama, llama.ccp
- Mode: Deterministic, single-file execution

---

## 8. Success Criteria

- Simple feature implementations
- Predictable diffs
- Minimal edits
- Low system requirements
- Easy to reason about

---
