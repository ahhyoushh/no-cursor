import argparse
import json
import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime, UTC
import hashlib

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.prompt import Prompt

from .llm import (
    start_server, ask_once, run_edit_llm, get_confidence_score,
    run_chat_llm, run_search_llm, run_plan_llm, run_fix_llm
)
from .diff_utils import validate_unified_diff, apply_diff, generate_diff
from .utils import die, read_text_file, split_response




NC_DIR, LOCK_FILE, LAST_DIFF = Path(".nc"), Path(".nc/lock"), Path(".nc/last.diff")
STATE_FILE, BACKUP_DIR = Path(".nc/state.json"), Path(".nc/backup")

console = Console()

def info(msg):
    console.print(f"[bold blue][nc][/bold blue] {msg}")


def warn(msg):
    console.print(f"[bold yellow][nc:warn][/bold yellow] [red]{msg}[/red]")


def success(msg):
    console.print(f"[bold green][nc:ok][/bold green] {msg}")




def acquire_lock():
    try:
        NC_DIR.mkdir(exist_ok=True)
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





def load_state():
    if not STATE_FILE.exists():
        die("workspace not initialized (run `nc init`)")
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def write_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def update_metrics(metrics):
    state = load_state()
    ms = state.setdefault("metrics", {"tokens": 0, "duration": 0, "calls": 0})
    ms["tokens"] += metrics["completion_tokens"] + metrics["prompt_tokens"]
    ms["duration"] += metrics["duration"]
    ms["calls"] += 1
    write_state(state)


def compute_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()





def cmd_init():
    if not NC_DIR.exists():
        NC_DIR.mkdir()
        BACKUP_DIR.mkdir()

    acquire_lock()

    with console.status("[bold green]Starting local model server...", spinner="dots"):
        try:
            process, port = start_server()
        except Exception as e:
            die(f"failed to start model server: {e}")

    state = {
        "open_file": None,
        "file_hash": None,
        "opened_at": None,
        "llama_pid": process.pid,
        "llama_port": port,
        "chat_history": [],
        "metrics": {"tokens": 0, "duration": 0, "calls": 0}
    }

    write_state(state)
    console.print(Panel.fit(
        "[bold green]Workspace initialized![/bold green]\n"
        "Local model server is running. Entering shell.",
        title="Welcome to nc",
        border_style="green"
    ))
    shell_loop()


def cmd_exit():
    try:
        if not STATE_FILE.exists():
            return
        state = load_state()
        pid = state.get("llama_pid")
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)
            except Exception:
                pass
    except Exception:
        pass
    finally:
        release_lock()
        info("Exited and stopped server.")
        sys.exit(0)


def cmd_quit():
    release_lock()
    info("Exited shell (server still running).")
    sys.exit(0)





def cmd_open(arg):
    if not arg:
        warn("usage: open <file>")
        return

    path = Path(arg).resolve()
    if not path.exists() or not path.is_file():
        warn(f"file does not exist: {arg}")
        return

    state = load_state()
    state.setdefault("files", {}).setdefault(str(path), {"chat_history": [], "plans": []})
    state.update({"open_file": str(path), "file_hash": compute_hash(path), "opened_at": datetime.now(UTC).isoformat()})
    write_state(state)
    success(f"Opened [cyan]{path}[/cyan]")


def _ensure_clean_file():
    state = load_state()
    if not state.get("open_file"):
        die("no file open")
    path = Path(state["open_file"])
    if compute_hash(path) != state["file_hash"]:
        warn("file changed since open. use 'open <file>' again to refresh.")
        return None, None
    return state, path


def cmd_ask(arg):
    if not arg:
        warn("usage: ask <question>")
        return

    state, path = _ensure_clean_file()
    if not state: return
    
    text = read_text_file(path)
    prompt = f"FILE:\n{text}\n\nQUESTION:\n{arg}"

    with console.status("[bold cyan]Thinking...", spinner="brain"):
        try:
            content, metrics = ask_once(state["llama_port"], prompt)
            update_metrics(metrics)
            console.print(Panel(content, title="Response", border_style="cyan"))
            console.print(f"[dim][metrics] {metrics['completion_tokens']} tokens, {metrics['tokens_per_sec']:.1f} t/s, {metrics['duration']:.2f}s[/dim]")
        except Exception as e:
            warn(str(e))


def cmd_edit(arg):
    if not arg:
        warn("usage: edit <instruction>")
        return

    state, path = _ensure_clean_file()
    if not state: return
    
    text = read_text_file(path)

    diff = None
    last_error = "model failed to produce a valid diff"
    
    with console.status("[bold yellow]Editing code...", spinner="bouncingBar"):
        for attempt in range(2):
            try:
                out, metrics = run_edit_llm(state["llama_port"], text, arg)
                update_metrics(metrics)
                
                if not out.strip():
                    last_error = "model returned empty response"
                    continue
                
                if out.strip().upper() == "ERROR GENERATING DIFF":
                    warn("Model failed to generate a diff for this request.")
                    return

                preamble, contents = split_response(out)
                
                extracted_diff = None
                for ctype, cblock in contents:
                    if ctype == 'diff' or (ctype == 'code' and ("@@ " in cblock or "--- " in cblock)):
                        try:
                            extracted_diff = validate_unified_diff(cblock)
                            break
                        except Exception as ve:
                            last_error = f"Validating diff block failed: {ve}"
                            continue
                
                if not extracted_diff:
                    try:
                        extracted_diff = validate_unified_diff(out)
                    except Exception as ve:
                        if not last_error or "Validating" not in last_error:
                            last_error = f"Validating whole response as diff failed: {ve}"
                
                if not extracted_diff:
                    code_blocks = [cblock for ctype, cblock in contents if ctype == 'code']
                    if code_blocks:
                        new_code = code_blocks[-1]
                        extracted_diff = generate_diff(text, new_code, path.name)
                        if not extracted_diff.strip():
                            extracted_diff = None
                            last_error = "Model code block matches existing code (no changes)."

                if extracted_diff:
                    score, reason = get_confidence_score(state["llama_port"], text, arg, extracted_diff)
                    
                    if score <= 0:
                        last_error = f"Model produced an invalid or template response: {reason}"
                        continue

                    # We skip printing preamble as per user request for "only reply using a proper diff"
                    
                    diff = extracted_diff
                    success(f"Generated diff ({metrics['completion_tokens']} tokens at {metrics['tokens_per_sec']:.1f} t/s)")
                    
                    color = "green" if score >= 90 else "yellow" if score >= 60 else "red"
                    console.print(f"[bold {color}]Confidence: {score}%[/bold {color}] - [dim]{reason}[/dim]")
                    
                    LAST_DIFF.write_text(diff, encoding="utf-8")
                    
                    # Automatically show the diff
                    syntax = Syntax(diff, "diff", theme="monokai", line_numbers=True)
                    console.print(Panel(syntax, title="Proposed Changes", border_style="yellow"))
                    
                    if score < 60:
                        warn("Low confidence. Review changes carefully before applying.")
                    else:
                        info("Use 'apply' to commit these changes.")
                    break
                else:
                    last_error = "Model failed to produce a valid diff in its response."
                    continue

            except Exception as e:
                last_error = f"Edit attempt {attempt+1} failed: {str(e)}"
                continue

    if not diff:
        warn(f"Failed to generate valid changes: {last_error}")
        return


def cmd_diff():
    state = load_state()
    if not state.get("open_file"):
        warn("No file open.")
        return
    if not LAST_DIFF.exists():
        warn("no diff available")
        return
    syntax = Syntax(LAST_DIFF.read_text(encoding="utf-8"), "diff", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Generated Diff", border_style="yellow"))


def cmd_apply(arg=None):
    state, path = _ensure_clean_file()
    if not state: return

    if not LAST_DIFF.exists():
        warn("no diff to apply")
        return

    if arg == "--dry-run":
        info("Dry run: previewing changes")
        cmd_diff()
        return

    backup = BACKUP_DIR / path.name
    backup.write_bytes(path.read_bytes())

    try:
        apply_diff(LAST_DIFF, path)
        state["file_hash"] = compute_hash(path)
        write_state(state)
        success("Diff applied successfully (backup created).")
    except Exception as e:
        warn(str(e))


def cmd_revert():
    state = load_state()
    if not state.get("open_file"):
        warn("no file open")
        return
    
    path = Path(state["open_file"])
    backup = BACKUP_DIR / path.name
    
    if not backup.exists():
        warn(f"no backup found for {path.name}")
        return

    try:
        path.write_bytes(backup.read_bytes())
        state["file_hash"] = compute_hash(path)
        write_state(state)
        success(f"Reverted {path.name} to previous state.")
    except Exception as e:
        warn(f"revert failed: {e}")


def cmd_status():
    state = {}
    try:
        state = load_state()
    except Exception:
        pass
    
    table = Table(title="NC Status", border_style="blue")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Open File", state.get("open_file") or "None")
    table.add_row("Server PID", str(state.get("llama_pid") or "N/A"))
    table.add_row("Server Port", str(state.get("llama_port") or "N/A"))
    table.add_row("Opened At", state.get("opened_at") or "N/A")
    
    if LAST_DIFF.exists():
        table.add_row("Last Diff", "Available (use 'diff' to see)")
    else:
        table.add_row("Last Diff", "None")
        
    console.print(table)


def cmd_explain():
    state, path = _ensure_clean_file()
    if not state: return
    
    text = read_text_file(path)
    prompt = f"FILE:\n{text}\n\nINSTRUCTION:\nExplain this code clearly and concisely, focusing on its purpose and key logic."

    with console.status("[bold cyan]Analyzing code...", spinner="bouncingBar"):
        try:
            content, metrics = ask_once(state["llama_port"], prompt)
            update_metrics(metrics)
            console.print(Panel(content, title=f"Explanation: {path.name}", border_style="cyan"))
            console.print(f"[dim][metrics] {metrics['completion_tokens']} tokens, {metrics['tokens_per_sec']:.1f} t/s, {metrics['duration']:.2f}s[/dim]")
        except Exception as e:
            warn(str(e))


def cmd_chat(arg):
    state = load_state()
    open_file = state.get("open_file")
    if not open_file:
        warn("Chat is only available when a file is open. Run 'open <file>' first.")
        return
        
    port = state["llama_port"]

    def talk(msg):
        s = load_state()
        f_state = s.get("files", {}).get(open_file, {})
        history = f_state.get("chat_history", [])
        
        # Add file content as context for the model
        file_text = read_text_file(Path(open_file))
        context_msg = f"CONTEXT (Current File: {Path(open_file).name}):\n```\n{file_text}\n```"
        
        # We don't append context_msg to history, just send it with the request
        actual_user_msg = f"{context_msg}\n\nUSER MESSAGE: {msg}"
        
        with console.status("[bold cyan]Thinking...", spinner="dots"):
            try:
                content, metrics = run_chat_llm(port, history, actual_user_msg)
                update_metrics(metrics)
                
                history.append({"role": "user", "content": msg})
                history.append({"role": "assistant", "content": content})
                
                # Update specifically for this file
                if "files" not in s: s["files"] = {}
                if open_file not in s["files"]: s["files"][open_file] = {}
                s["files"][open_file]["chat_history"] = history[-20:]
                write_state(s)
                return content
            except Exception as e:
                return f"Error: {e}"

    if arg:
        content = talk(arg)
        console.print(Panel(content, title="Assistant", border_style="cyan"))
        return

    console.print(f"[bold cyan]Entering Interactive Chat for {Path(open_file).name}. Type 'exit' or 'quit' to return.[/bold cyan]")
    while True:
        try:
            line = console.input(f"[bold cyan]nc (chat:{Path(open_file).name})[/bold cyan]> ").strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit"):
                break
            
            content = talk(line)
            console.print(Panel(content, title="Assistant", border_style="cyan"))
        except (EOFError, KeyboardInterrupt):
            break
    info("Exited chat mode.")

def cmd_fix(_):
    state, path = _ensure_clean_file()
    if not state: return
    
    file_text = read_text_file(path)
    with console.status("[bold red]Auditing file for bugs...", spinner="dots"):
        try:
            content, metrics = run_fix_llm(state["llama_port"], file_text)
            update_metrics(metrics)
            
            if "no errors detected" in content.lower():
                success("No errors detected in the file.")
                return
            
            console.print(Panel(content, title="Bug Audit & Fix Suggestion", border_style="red"))
            
            # If a diff is present, offer to apply
            if "--- a/" in content:
                choice = Prompt.ask("Apply detected fix?", choices=["y", "n"], default="n")
                if choice == "y":
                    with open(LAST_DIFF, "w", encoding="utf-8") as f:
                        f.write(validate_unified_diff(content))
                    cmd_apply(None)
        except Exception as e:
            warn(str(e))



def cmd_search(arg):
    if not arg:
        warn("usage: search <query>")
        return
    state = load_state()
    open_file = state.get("open_file")
    if not open_file:
        warn("Search is only available when a file is open.")
        return
    
    path = Path(open_file)
    content = read_text_file(path)
    # We send the whole content or a localized snippet
    snippet = f"--- FILE: {path.name} ---\n{content}\n"

    with console.status("[bold yellow]Searching code...", spinner="dots"):
        try:
            content, metrics = run_search_llm(state["llama_port"], arg, snippet)
            update_metrics(metrics)
            console.print(Panel(content, title=f"Search Results in {path.name}: {arg}", border_style="yellow"))
        except Exception as e:
            warn(str(e))

def cmd_plan(arg):
    if not arg:
        warn("usage: plan <goal>")
        return
    
    state = load_state()
    open_file = state.get("open_file")
    if not open_file:
        warn("Planning is only available when a file is open.")
        return

    file_text = read_text_file(Path(open_file))
    context = f"Active file: {Path(open_file).name}\nFILE CONTENT:\n{file_text}\n"
    
    with console.status("[bold green]Planning...", spinner="dots"):
        try:
            content, metrics = run_plan_llm(state["llama_port"], arg, context)
            update_metrics(metrics)
            console.print(Panel(content, title="Implementation Plan", border_style="green"))
            
            # Store as pending for this specific file
            s = load_state()
            f_state = s.setdefault("files", {}).setdefault(open_file, {})
            f_state["pending_plan"] = {
                "goal": arg,
                "content": content,
                "timestamp": datetime.now(UTC).isoformat()
            }
            write_state(s)
            info("Plan generated. Use 'save-plan' to keep it.")
        except Exception as e:
            warn(str(e))

def cmd_save_plan():
    state = load_state()
    open_file = state.get("open_file")
    if not open_file:
        warn("No file open.")
        return
    
    f_state = state.get("files", {}).get(open_file, {})
    pending = f_state.get("pending_plan")
    
    if not pending:
        warn("No unsaved plan found for this file. Run 'plan <goal>' first.")
        return
    
    plans = f_state.setdefault("plans", [])
    plans.append(pending)
    f_state["pending_plan"] = None # Clear pending
    
    write_state(state)
    success(f"Plan for '[cyan]{pending['goal']}[/cyan]' saved to workspace.")

def cmd_show_plans():
    state = load_state()
    open_file = state.get("open_file")
    if not open_file:
        warn("No file open. Plans are file-specific.")
        return
    
    plans = state.get("files", {}).get(open_file, {}).get("plans", [])
    if not plans:
        info("No saved plans for this file.")
        return
    
    for i, plan in enumerate(plans):
        console.print(Panel(plan["content"], title=f"Plan {i+1}: {plan['goal']}", border_style="green"))

def cmd_show_chat():
    state = load_state()
    open_file = state.get("open_file")
    if not open_file:
        warn("No file open. Chat history is file-specific.")
        return
    
    history = state.get("files", {}).get(open_file, {}).get("chat_history", [])
    if not history:
        info("No chat history for this file.")
        return
    
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        style = "cyan" if role == "assistant" else "green"
        title = "Assistant" if role == "assistant" else "User"
        console.print(Panel(content, title=title, border_style=style))

def cmd_stats():
    state = load_state()
    ms = state.get("metrics", {"tokens": 0, "duration": 0, "calls": 0})
    
    table = Table(title="Usage Statistics", border_style="green")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Total Calls", str(ms["calls"]))
    table.add_row("Total Tokens", f"{ms['tokens']:,}")
    table.add_row("Total Time", f"{ms['duration']:.1f}s")
    if ms["duration"] > 0:
        table.add_row("Avg Speed", f"{ms['tokens']/ms['duration']:.1f} t/s")
    
    console.print(table)

def cmd_help():
    from rich import box
    table = Table(
        title="[bold magenta]NC Assistant Console[/bold magenta]",
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="dim",
        show_header=True,
        expand=True
    )
    table.add_column("Category", style="bold yellow", width=12)
    table.add_column("Command", style="bold white", width=20)
    table.add_column("Description", style="dim white")
    
    table.add_row("Editor", "open <file>", "Focus a file for editing")
    table.add_row("", "[green]edit <msg>[/green]", "Request code modifications")
    table.add_row("", "diff", "Preview generated changes")
    table.add_row("", "apply", "Commit changes to disk")
    table.add_row("", "revert", "Undo last committed change")
    
    table.add_row(end_section=True)
    
    table.add_row("Assistance", "chat", "Live file-bound conversation")
    table.add_row("", "ask <msg>", "Direct question about code")
    table.add_row("", "explain", "Summarize file logic")
    table.add_row("", "show-chat", "Review file chat history")
    
    table.add_row("Automation", "fix", "Audit active file for bugs")
    table.add_row("", "plan <goal>", "Strategize implementation steps")
    table.add_row("", "save-plan", "Save the last generated plan")
    table.add_row("", "show-plans", "List saved file-specific plans")
    table.add_row("", "search <msg>", "Semantic search in active file")
    
    table.add_row(end_section=True)
    
    table.add_row("Internal", "status / stats", "Check system/usage state")
    table.add_row("", "ls / cat / pwd", "File system utilities")
    table.add_row("", "clear / help", "Console management")
    table.add_row("", "exit", "Shutdown server and exit")
    table.add_row("", "q / qs / quit", "Exit shell (server stays running)")
    
    console.print(table)




def shell_loop():
    cmd_help()

    commands = {
        "open": cmd_open,
        "ask": cmd_ask,
        "chat": cmd_chat,
        "fix": lambda _: cmd_fix(None),
        "search": cmd_search,
        "plan": cmd_plan,
        "save-plan": lambda _: cmd_save_plan(),
        "show-plans": lambda _: cmd_show_plans(),
        "show-chat": lambda _: cmd_show_chat(),
        "stats": lambda _: cmd_stats(),
        "explain": lambda _: cmd_explain(),
        "edit": cmd_edit,
        "diff": lambda _: cmd_diff(),
        "apply": cmd_apply,
        "revert": lambda _: cmd_revert(),
        "status": lambda _: cmd_status(),
        "exit": lambda _: cmd_exit(),
        "q": lambda _: cmd_quit(),
        "qs": lambda _: cmd_quit(),
        "quit": lambda _: cmd_quit(),
        "help": lambda _: cmd_help(),
        "ls": lambda a: subprocess.run(["dir", "/b"] if os.name == "nt" else ["ls", "-F"], shell=True),
        "dir": lambda a: subprocess.run(["dir"] if os.name == "nt" else ["ls", "-l"], shell=True),
        "cat": lambda a: console.print(Syntax(Path(a).read_text(encoding="utf-8") if a and Path(a).exists() else "File not found", "python")),
        "clear": lambda _: console.clear(),
        "pwd": lambda _: console.print(os.getcwd()),
    }

    while True:
        try:
            # Get current open file for prompt
            state_data = {}
            active_file = "None"
            try:
                state_data = load_state()
                if state_data.get("open_file"):
                    active_file = Path(state_data["open_file"]).name
            except Exception:
                pass

            prompt_text = f"[bold magenta]nc[/bold magenta] ([cyan]{active_file}[/cyan])> "
            line = console.input(prompt_text).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            cmd_exit()

        if not line:
            continue

        parts = line.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else None

        fn = commands.get(cmd)
        if not fn:
            # Try running as system command if not internal
            try:
                subprocess.run(line, shell=True)
            except Exception as e:
                warn(f"unknown command and system execution failed: {e}")
            continue

        try:
            if fn.__code__.co_argcount > 0:
                fn(arg)
            else:
                fn()
        except Exception as e:
            warn(f"command execution failed: {e}")





def main():
    parser = argparse.ArgumentParser(prog="nc")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("init")
    sub.add_parser("exit")
    sub.add_parser("shell")
    sub.add_parser("stats")
    sub.add_parser("status")

    args = parser.parse_args()
    if args.cmd == "init":
        cmd_init()
    elif args.cmd == "exit":
        cmd_exit()
    elif args.cmd == "shell":
        shell_loop()
    elif args.cmd == "stats":
        cmd_stats()
    elif args.cmd == "status":
        cmd_status()
    else:
        # Default behavior if run without args (and initialized)
        if STATE_FILE.exists():
            shell_loop()
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
