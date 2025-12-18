import subprocess
import time
import json
import urllib.request
import socket

from .config import (
    LLAMA_SERVER_BIN,
    MODEL_PATH,
    TEMPERATURE,
    TOP_P,
    SEED,
)
from .prompts import ASK_SYSTEM_PROMPT, EDIT_SYSTEM_PROMPT


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_server():
    port = _free_port()

    process = subprocess.Popen(
        [
            LLAMA_SERVER_BIN,
            "--model", MODEL_PATH,
            "--host", "127.0.0.1",
            "--port", str(port),
            "--ctx-size", "1024",
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


def _chat(port, messages, max_tokens):
    url = f"http://127.0.0.1:{port}/v1/chat/completions"

    payload = {
        "model": "local",
        "messages": messages,
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": max_tokens,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=300) as resp:
        out = json.loads(resp.read().decode())
        return out["choices"][0]["message"]["content"].strip()


def ask_once(port, prompt):
    return _chat(
        port,
        [
            {"role": "system", "content": ASK_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        256,
    )


def run_edit_llm(port, file_text, instruction):
    return _chat(
        port,
        [
            {"role": "system", "content": EDIT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"FILE:\n{file_text}\n\nINSTRUCTION:\n{instruction}",
            },
        ],
        256,
    )
