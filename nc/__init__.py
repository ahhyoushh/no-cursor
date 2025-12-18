#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import signal
from pathlib import Path
from datetime import datetime, UTC
import hashlib

from .llm import start_server, ask_once, run_edit_llm
from .diff_utils import validate_unified_diff, apply_diff
from .utils import die, read_text_file

# --------------------
# Paths
# --------------------

NC_DIR = Path(".nc")
STATE_FILE = NC_DIR / "state.json"
BACKUP_DIR = NC_DIR / "backup"
LOCK_FILE = NC_DIR / "lock"
LAST_DIFF = NC_DIR / "last.diff"

# --------------------
# Output helpers (no readline, Windows-safe)
# --------------------

def info(msg):
    print(f"[nc] {msg}")


def warn(msg):
    print(f"[nc:warn] {msg}")


# --------------------
# Locking
# --------------------

def acquire_lock():
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        die("workspace is locked (another nc process is running)")


def release_lock():
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


# --------------------
# State
# --------------------

def load_state():
    if not STATE_FILE.exists():
        die("workspace not initialized (run `nc init`)")
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def write_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def compute_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------
# INIT / EXIT
# --------------------

def cmd_init():
    if not NC_DIR.exists():
        NC_DIR.mkdir()
        BACKUP_DIR.mkdir()

    acquire_lock()

    info("Starting local model server…")
    process, port = start_server()

    state = {
        "open_file": None,
        "file_hash": None,
        "opened_at": None,
        "llama_pid": process.pid,
        "llama_port": port,
    }

    write_state(state)
    info("Workspace initialized. Entering shell.")
    shell_loop()


def cmd_exit():
    try:
        state = load_state()
        pid = state.get("llama_pid")
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
            except Exception:
                pass
    finally:
        release_lock()
        info("Exited.")
        sys.exit(0)


# --------------------
# Commands
# --------------------

def cmd_open(arg):
    if not arg:
        warn("usage: open <file>")
        return

    path = Path(arg).resolve()
    if not path.exists() or not path.is_file():
        warn("file does not exist")
        return

    state = load_state()
    state.update({
        "open_file": str(path),
        "file_hash": compute_hash(path),
        "opened_at": datetime.now(UTC).isoformat(),
    })
    write_state(state)
    info(f"Opened {path}")


def _ensure_clean_file():
    state = load_state()
    if not state.get("open_file"):
        die("no file open")
    path = Path(state["open_file"])
    if compute_hash(path) != state["file_hash"]:
        die("file changed since open")
    return state, path


def cmd_ask(arg):
    if not arg:
        warn("usage: ask <question>")
        return

    state, path = _ensure_clean_file()
    text = read_text_file(path)
    prompt = f"FILE:\n{text}\n\nQUESTION:\n{arg}"

    try:
        print(ask_once(state["llama_port"], prompt))
    except Exception as e:
        warn(str(e))


def cmd_edit(arg):
    if not arg:
        warn("usage: edit <instruction>")
        return

    state, path = _ensure_clean_file()
    text = read_text_file(path)

    diff = None
    for _ in range(3):
        out = run_edit_llm(state["llama_port"], text, arg)
        if not out.strip():
            continue
        try:
            validate_unified_diff(out)
            diff = out
            break
        except ValueError:
            continue

    if not diff:
        warn("model failed to produce a valid diff")
        return

    LAST_DIFF.write_text(diff, encoding="utf-8")
    info("Diff generated. Use `diff` or `apply`. (Use `apply --dry-run` to preview)")


def cmd_diff():
    if not LAST_DIFF.exists():
        warn("no diff available")
        return
    print(LAST_DIFF.read_text(encoding="utf-8"))


def cmd_apply(arg=None):
    state, path = _ensure_clean_file()

    if arg == "--dry-run":
        info("Dry run: no changes written")
        print(LAST_DIFF.read_text(encoding="utf-8"))
        return

    backup = BACKUP_DIR / path.name
    backup.write_bytes(path.read_bytes())

    try:
        apply_diff(LAST_DIFF, path)
        state["file_hash"] = compute_hash(path)
        write_state(state)
        info("Diff applied.")
    except Exception as e:
        warn(str(e))


# --------------------
# Shell (Windows-safe, no readline)
# --------------------

def shell_loop():
    info("Type 'help' for commands. 'exit' to quit.")

    commands = {
        "open": cmd_open,
        "ask": cmd_ask,
        "edit": cmd_edit,
        "diff": lambda _: cmd_diff(),
        "apply": cmd_apply,
        "exit": lambda _: cmd_exit(),
        "help": None,
    }

    while True:
        try:
            line = input("nc> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            cmd_exit()

        if not line:
            continue

        if line == "help":
            print("Commands: open, ask, edit, diff, apply [--dry-run], exit")
            continue

        parts = line.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else None

        fn = commands.get(cmd)
        if not fn:
            warn("unknown command")
            continue

        fn(arg)


# --------------------
# Entry
# --------------------

def main():
    parser = argparse.ArgumentParser(prog="nc")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("exit")
    sub.add_parser("shell")

    args = parser.parse_args()
    if args.cmd == "init":
        cmd_init()
    elif args.cmd == "exit":
        cmd_exit()
    elif args.cmd == "shell":
        shell_loop()


if __name__ == "__main__":
    main()
