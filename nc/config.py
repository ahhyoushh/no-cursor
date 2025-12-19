from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

LLAMA_SERVER_BIN = "C:/llama/llama-server.exe"
MODEL_PATH = str(BASE_DIR / "models" / "deepseek-coder-1.3b-instruct.Q4_0.gguf")

TEMPERATURE = 0.0
TOP_P = 1.0
SEED = 42
MAX_TOKENS = 4096
CONTEXT_SIZE = 8192
