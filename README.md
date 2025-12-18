# no-cursor (nc)

A **local, CLI-first, deterministic code assistant** built for completely local experience and reproducing simple unifile code.

Was fed up from the gemini ratelimit ragebaits.

No cloud APIs. No background agents. No autonomous edits.

---

## Installation

```bash
pip install -e .
```

Requires:

* Python 3.10+
* llama.cpp `llama-server`
* A local GGUF model (tested with [Qwen2.5-Coder-3B-instruct-q4_k_m.gguf](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/tree/main) and planned with deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B) 

---

## Quick Start

```bash
nc init
```

This will:

* Create a `.nc/` workspace
* Start the local llama.cpp model server
* Drop you into the interactive `nc>` shell

---

## Typical Workflow

```bash
nc init
nc> open test.py
nc> ask explain this file
nc> edit "replace b = x with b = a + x and print a + b"
nc> diff
nc> apply --dry-run
nc> apply
nc> exit
```

---

## Shell Commands

| Command              | Description             |
| -------------------- | ----------------------- |
| `open <file>`        | Track a single file     |
| `ask <question>`     | Read-only explanation   |
| `edit <instruction>` | Generate a unified diff |
| `diff`               | Show last diff          |
| `apply`              | Apply diff              |
| `apply --dry-run`    | Preview only            |
| `exit`               | Clean shutdown          |

---

## Guarantees

* One file at a time
* File hash verified before edits
* Diff-only edits
* No auto-apply
* Deterministic local model

---

## Terminal Compatibility

Designed to work reliably with:

* PowerShell
* Windows Terminal
* VS Code integrated terminal ? Vim

No readline / curses / external UI libraries used.

---

## Status

MVP complete.
