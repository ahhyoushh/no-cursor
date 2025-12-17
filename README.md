# no-cursor (nc)
### High-Level Plan — Agentic Code Editor (CLI-First, Local-Only)

---

## 1. Overview

**no-cursor** (`nc`) is a minimal, local, and free agentic code editor controlled entirely via the CLI.
VS Code (or vim/nvim) acts only as a passive viewer for files, diffs, and test results.

Made coz tired of api ratelimits.

The system is intentionally constrained to ensure completely local usage, safety, and predictability.

Not competing with cursor obviously 🥀
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
nc init
nc open src/example.py
nc ask
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

- Code model: Qwen2.5-Coder 7B Instruct (via Ollama)
- Embeddings (optional, local-only): small deterministic model
- Mode: deterministic, single-file execution

---

## 8. Interaction Modes

### Ask Mode (Read-Only)
- Interactive shell
- No disk writes
- Pure explanation

### Edit Mode (Transactional)
- Single-shot by default
- Optional constrained instruction shell
- Always diff-only
- Never auto-apply

---

## 9. Intent Normalization (Post-MVP)

After the basic `ask` and `edit` functionality is stable, nc may optionally introduce
**embedding-based intent normalization** to improve UX in the edit shell.

Scope is strictly limited:
- Fuzzy matching of synonyms
- Classification into fixed buckets (goal / constraints)
- No autonomous reasoning
- No hidden intent generation

Embeddings are used only as a parser, never as a decision-maker.

---

## 10. Success Criteria

- Simple feature implementations
- Predictable diffs
- Minimal edits
- Low system requirements
- Easy to reason about
