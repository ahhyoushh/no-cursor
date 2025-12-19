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
nc> chat                     # Start a conversation about the code
nc> search "divide logic"    # Find specific logic in the active file
nc> fix                      # Audit the file for bugs and auto-repair
nc> plan "Add error logs"    # Generate a roadmap
nc> save-plan                # Persist the plan for later
nc> edit "Apply the plan"    # Request the code changes
nc> diff                     # Preview changes (includes Confidence Score)
nc> apply                    # Commit to disk (auto-backup created)
nc> stats                    # See usage metrics
nc> exit
```

---

## Shell Commands

### Core Operations
| Command              | Description                               |
| -------------------- | ----------------------------------------- |
| `open <file>`        | Focus a single file for editing           |
| `edit <msg>`         | Request code changes (Unified Diff)      |
| `diff`               | Preview generated changes                 |
| `apply`              | Commit changes with auto-backup           |
| `revert`             | Restore the last committed backup         |

### Assistance & AI
| Command              | Description                               |
| -------------------- | ----------------------------------------- |
| `chat [<msg>]`       | Interactive conversation (with history)   |
| `ask <msg>`          | One-off read-only question                |
| `explain`            | Concise logic summary                     |
| `show-chat`          | View full history for active file        |

### Automation & Tools
| Command              | Description                               |
| -------------------- | ----------------------------------------- |
| `fix`                | Proactive bug audit and auto-repair       |
| `plan <goal>`        | Generate a step-by-step roadmap           |
| `save-plan`          | Store the generated plan file-specifically|
| `show-plans`         | List all saved plans for the active file |
| `search <query>`     | Semantic search within the active file    |

### System
| Command              | Description                               |
| -------------------- | ----------------------------------------- |
| `status / stats`     | Workspace health and usage metadata       |
| `ls / cat / pwd`     | standard filesystem utilities             |
| `help / clear`       | Console management                        |
| `exit`               | Clean shutdown of server and console      |

---

## Guarantees

* **Context Awareness**: Chat and Plans are tied to the active file.
* **Deterministic**: No cloud calls. All logic processed by the local model.
* **Inspectable**: Diffs are validated and shown with confidence scores.
* **Safety First**: Manual `apply` and automated backups for every edit.

---

## Status
Active development. All features listed above are fully implemented and functional locally.

