from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

LLAMA_SERVER_BIN = "C:/llama/llama-server.exe"
MODEL_PATH = str(BASE_DIR / "models" / "qwen2.5-coder-3b-instruct-q4_k_m.gguf")

TEMPERATURE = 0.0
TOP_P = 1.0
SEED = 42
MAX_TOKENS = 256
