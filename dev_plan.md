# no-cursor Development Plan

## Vision

A deterministic, local-first code assistant that prioritizes safety, inspectability, and explicit user control over autonomy.

---

## Phase 1–5 (DONE)

* Workspace initialization
* Single-file tracking
* Content hashing
* Read-only ask mode
* Local llama.cpp integration

---

## Phase 6–9 (DONE)

* Unified diff–only edit mode
* Diff validation
* Deterministic apply pipeline
* Encoding-safe file handling
* Windows compatibility fixes

---

## Phase 10 (DONE)

* Persistent interactive shell
* Non-crashing error handling
* Explicit apply / no auto-mutate
* Backup before apply

---

## Phase 11 (DONE)

* Windows-safe shell (no readline)
* VS Code / PowerShell compatibility
* Dry-run support
* Improved UX messaging

---

## Phase 12 (DONE)

* Undo / revert stack (Single-level backup)
* Status / stats tracking (Usage metrics)
* Diff confidence scoring (Model self-evaluation)
* Logic-aware automated fixing (`fix` audit)
* Semantic code search (Active file scope)

---

## Phase 13 (DONE)

* Persistent file-specific states
* High-res Implementation Planning (`plan`)
* Decoupled Plan/Save workflow
* Multi-stage resilient diff application
* Rich UI console experience

---

## Phase 14 (NEXT)

* Multi-file context injection
* Sequential plan execution automation
* Conversation summary for long histories
* Workspace-wide semantic indexing

---

## Non-Goals

* Autonomous agents (Auto-mutate without user `apply`)
* Cloud inference
* Background daemons

---

## Current Status

Assistant ecosystem ready.
Focus shifting to multi-file awareness and workspace-level intelligence.

