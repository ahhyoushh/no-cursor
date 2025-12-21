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


def split_response(text: str):
    """Splits model response into preamble and code/diff blocks."""
    # Filter out repeated instructions/rules that some models echo back
    filtered_lines = []
    skip_keywords = ("RULES:", "INSTRUCTIONS:", "IMPORTANT:", "OUTPUT FORMAT:", "CRITICAL:", "FILE:")
    for line in text.splitlines():
        if any(kw in line.upper() for kw in skip_keywords):
            continue
        filtered_lines.append(line)
    
    lines = filtered_lines
    preamble, contents = [], []
    
    # 1. Check for raw diff without backticks
    diff_markers = ("--- a/", "+++ b/", "@@ -", "diff --git")
    text_processed = "\n".join(lines)
    if any(line.startswith(diff_markers) for line in lines) and "```" not in text_processed:
        diff_start = next((idx for idx, l in enumerate(lines) if any(l.startswith(m) for m in diff_markers)), -1)
        if diff_start > 0:
            return "\n".join(lines[:diff_start]).strip(), [('diff', "\n".join(lines[diff_start:]))]
        return "", [('diff', text_processed)]

    # 2. Standard triple-backtick block parsing
    i, in_block, current_block, block_type = 0, False, [], 'text'
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            if in_block:
                contents.append((block_type, "\n".join(current_block)))
                current_block, in_block = [], False
            else:
                in_block = True
                lang = line.strip()[3:].strip().lower()
                block_type = 'diff' if lang in ('diff', 'udiff', 'patch') else 'code'
            i += 1
            continue
        
        if in_block:
            current_block.append(line)
        else:
            if not contents:
                preamble.append(line)
            else:
                if contents[-1][0] == 'text':
                    contents[-1] = ('text', contents[-1][1] + "\n" + line)
                else:
                    contents.append(('text', line))
        i += 1
        
    if in_block and current_block:
        contents.append((block_type, "\n".join(current_block)))
        
    # 3. Fallback: If no blocks found, but preamble contains what looks like code
    if not contents and not any(ctype in ('code', 'diff') for ctype, _ in contents):
        code_markers = ("def ", "import ", "class ", "print(", "if __name__")
        code_start = -1
        for idx, line in enumerate(preamble):
            if any(line.startswith(m) for m in code_markers):
                code_start = idx
                break
        
        if code_start != -1:
            real_preamble = "\n".join(preamble[:code_start]).strip()
            code_content = "\n".join(preamble[code_start:]).strip()
            return real_preamble, [('code', code_content)]

    return "\n".join(preamble).strip(), contents
