import re
import difflib
from pathlib import Path

def generate_diff(old_text: str, new_text: str, filename: str = "FILE") -> str:
    """Generates a unified diff between old_text and new_text."""
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    return "".join(diff)


def validate_unified_diff(diff_text: str) -> str:
    """Extracts diff from markdown and validates structure."""
    # Extract from markdown block if the model used one
    match = re.search(r"```(?:diff)?\n(.*?)\n```", diff_text, re.DOTALL)
    if match:
        diff_text = match.group(1)

    lines = diff_text.splitlines()
    
    # Find where the actual diff content starts
    start_idx = next((i for i, l in enumerate(lines) if any(l.startswith(m) for m in ("--- ", "+++ ", "@@ "))), -1)
    if start_idx == -1: 
        raise ValueError("No diff markers found (---, +++, or @@).")

    final_diff = "\n".join(lines[start_idx:]).strip()
    
    # Check for lazy placeholders
    check_text = final_diff.lower()
    placeholders = [
        "removed line", "added line", "context line", 
        "old code", "new code", "snippet here", 
        "implementation here", "your code here"
    ]
    if any(p in check_text for p in placeholders):
        raise ValueError("Model returned a placeholder template instead of actual code.")

    if "@@ " not in final_diff: 
        raise ValueError("Missing unified diff hunks (@@).")

    # Ensure headers exist for the applier
    if "--- " not in final_diff: 
        final_diff = f"--- a/FILE\n+++ b/FILE\n{final_diff}"
    elif "+++ " not in final_diff:
        parts = final_diff.split("\n")
        parts.insert(1, "+++ b/FILE")
        final_diff = "\n".join(parts)
        
    return final_diff


def apply_diff(diff_content: str, target: Path):
    """Applies a unified diff to a target file."""
    if not target.exists():
        raise FileNotFoundError(f"Target file {target} does not exist.")

    target_text = target.read_text(encoding="utf-8")
    target_lines = target_text.splitlines()

    # Parse hunks
    hunks = []
    current_hunk = None
    
    for line in diff_content.splitlines():
        if line.startswith("@@"):
            if current_hunk:
                hunks.append(current_hunk)
            match = re.search(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
            if match:
                current_hunk = {
                    "old_start": int(match.group(1)),
                    "lines": [],
                }
        elif current_hunk:
            if line.startswith(("+", "-", " ")):
                current_hunk["lines"].append(line)
            elif line == "": 
                # Handle models omitting the space for empty context lines
                current_hunk["lines"].append(" ")
                
    if current_hunk:
        hunks.append(current_hunk)

    if not hunks:
        raise ValueError("No valid hunks found in diff.")

    new_content_lines = list(target_lines)
    
    # Apply hunks in reverse to keep line numbers valid
    for hunk in reversed(hunks):
        search_lines = [l[1:] for l in hunk["lines"] if not l.startswith("+")]
        replacement_lines = [l[1:] for l in hunk["lines"] if not l.startswith("-")]
        
        found_idx = -1
        
        # 1. Try exact match
        for i in range(len(new_content_lines) - len(search_lines) + 1):
            if all(new_content_lines[i+j] == search_lines[j] for j in range(len(search_lines))):
                found_idx = i
                break
        
        # 2. Try match with stripped whitespace (more lenient)
        if found_idx == -1:
            for i in range(len(new_content_lines) - len(search_lines) + 1):
                if all(new_content_lines[i+j].strip() == search_lines[j].strip() for j in range(len(search_lines))):
                    if any(search_lines[j].strip() for j in range(len(search_lines))):
                        found_idx = i
                        break

        if found_idx == -1:
            raise ValueError(f"Hunk starting at line {hunk['old_start']} failed to apply (content not found).")

        new_content_lines[found_idx : found_idx + len(search_lines)] = replacement_lines

    target.write_text("\n".join(new_content_lines) + "\n", encoding="utf-8")