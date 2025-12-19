import sys
from pathlib import Path


from rich.console import Console

console = Console()

def die(msg):
    console.print(f"[bold red]nc: error:[/bold red] {msg}", style="red")
    sys.exit(1)


def read_text_file(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-16")
