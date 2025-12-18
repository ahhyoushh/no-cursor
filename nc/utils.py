import sys
from pathlib import Path


def die(msg):
    print(f"nc: error: {msg}", file=sys.stderr)
    sys.exit(1)


def read_text_file(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-16")
