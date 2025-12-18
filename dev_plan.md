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

## Phase 12 (NEXT)

* Undo / revert stack
* Status / health command
* Diff confidence scoring
* Structured multi-line edit input

---

## Non-Goals

* Autonomous agents
* Background daemons
* Cloud inference
* Silent edits

---

## Current Status

Core system complete.
Remaining work is UX polish and safety hardening.

