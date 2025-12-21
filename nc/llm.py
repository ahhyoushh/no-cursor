import subprocess
import time
import json
import urllib.request
import socket
from pathlib import Path

from .config import (
    LLAMA_SERVER_BIN,
    MODEL_PATH,
    TEMPERATURE,
    TOP_P,
    SEED,
    MAX_TOKENS,
    CONTEXT_SIZE,
)
from .prompts import (
    ASK_SYSTEM_PROMPT, EDIT_SYSTEM_PROMPT, VERIFY_SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT, SEARCH_SYSTEM_PROMPT, PLAN_SYSTEM_PROMPT, FIX_SYSTEM_PROMPT
)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_server():
    if not Path(LLAMA_SERVER_BIN).exists():
        raise FileNotFoundError(f"llama-server binary not found at: {LLAMA_SERVER_BIN}")

    port = _free_port()

    process = subprocess.Popen(
        [
            LLAMA_SERVER_BIN,
            "--model", MODEL_PATH,
            "--host", "127.0.0.1",
            "--port", str(port),
            "--ctx-size", str(CONTEXT_SIZE),
            "--cache-ram", "0",
            "--temp", str(TEMPERATURE),
            "--top-p", str(TOP_P),
            "--seed", str(SEED),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    url = f"http://127.0.0.1:{port}/v1/models"
    for _ in range(60):
        try:
            with urllib.request.urlopen(url, timeout=0.3):
                return process, port
        except Exception:
            time.sleep(0.2)

    process.terminate()
    raise RuntimeError("llama-server failed to start")


def _chat(port, system_content, user_content, history=None, max_tokens=None):
    if max_tokens is None: max_tokens = MAX_TOKENS
    url = f"http://127.0.0.1:{port}/v1/completions"
    
    parts = [system_content.strip()]
    if history:
        for msg in history:
            role, content = msg["role"], msg["content"]
            parts.append(f"<|{role}|>\n{content}")
    
    parts.append(f"<|user|>\n{user_content}\n<|assistant|>\n")
    full_prompt = "\n".join(parts)

    payload = {
        "prompt": full_prompt,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": max_tokens,
        "stop": ["<|user|>", "<|assistant|>", "<|system|>", "###"],
    }

    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )

    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            out = json.loads(resp.read().decode())
            duration = time.time() - start_time
            content = out["choices"][0]["text"].strip()
            usage = out.get("usage", {})
            metrics = {
                "duration": duration,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "tokens_per_sec": usage.get("completion_tokens", 0) / duration if duration > 0 else 0
            }
            return content, metrics
    except Exception as e:
        raise RuntimeError(f"LLM request failed: {str(e)}") from e


def ask_once(port, prompt):
    return _chat(port, ASK_SYSTEM_PROMPT, prompt)


def run_edit_llm(port, file_text, instruction):
    user_prompt = f"FILE:\n{file_text}\n\nINSTRUCTION:\n{instruction}"
    return _chat(port, EDIT_SYSTEM_PROMPT, user_prompt)

def run_chat_llm(port, history, message):
    return _chat(port, CHAT_SYSTEM_PROMPT, message, history=history)

def run_search_llm(port, query, snippets):
    user_prompt = f"QUERY: {query}\n\nCODE SNIPPETS:\n{snippets}"
    return _chat(port, SEARCH_SYSTEM_PROMPT, user_prompt)

def run_plan_llm(port, goal, context=""):
    user_prompt = f"GOAL: {goal}\n\nCONTEXT:\n{context}"
    return _chat(port, PLAN_SYSTEM_PROMPT, user_prompt)

def run_fix_llm(port, file_text):
    return _chat(port, FIX_SYSTEM_PROMPT, f"FILE CONTENT:\n{file_text}")




def get_confidence_score(port, file_text, instruction, diff):
    verify_prompt = (
        f"ORIGINAL CODE:\n{file_text}\n\n"
        f"INSTRUCTION:\n{instruction}\n\n"
        f"GENERATED DIFF:\n{diff}"
    )
    try:
        content, _ = _chat(port, VERIFY_SYSTEM_PROMPT, verify_prompt, max_tokens=256)
        
        # Robust JSON extraction
        json_content = content
        if "{" in content and "}" in content:
            try:
                # Find the largest possible JSON object block
                start = content.find("{")
                end = content.rfind("}") + 1
                json_content = content[start:end]
            except Exception:
                pass
            
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError:
            # Try to see if there's any JSON-like part that works
            import re
            matches = re.findall(r"\{.*?\}", content, re.DOTALL)
            for m in matches:
                try:
                    data = json.loads(m)
                    if "score" in data:
                        return data.get("score", 0), data.get("reason", "No reason provided")
                except:
                    continue
            raise # Re-raise if no luck

        return data.get("score", 0), data.get("reason", "No reason provided")
    except Exception as e:
        return 0, f"Verification failed to parse JSON from response: {content[:100]}... Error: {str(e)}"
