from pathlib import Path
from .utils import read_text_file


def validate_unified_diff(diff: str) -> str:
    original_lines = diff.splitlines()
    
    # 1. Find the start of the diff
    start_idx = -1
    for i, line in enumerate(original_lines):
        if line.startswith("--- ") or line.startswith("diff ") or line.startswith("@@ "):
            start_idx = i
            break
            
    if start_idx == -1:
        raise ValueError("No diff markers (---, diff, or @@) found in response.")

    # 2. Extract lines starting from start_idx
    lines = original_lines[start_idx:]
    
    # 3. Determine the actual end of the diff
    # A diff must start with headers (optional but preferred) then hunks
    # We skip headers and then collect hunks.
    
    cleaned_lines = []
    in_hunk = False
    last_valid_idx = 0
    
    for i, line in enumerate(lines):
        # Header lines
        if line.startswith("--- ") or line.startswith("+++ ") or line.startswith("diff "):
            cleaned_lines.append(line)
            last_valid_idx = i
            continue
            
        # Hunk start
        if line.startswith("@@ "):
            in_hunk = True
            cleaned_lines.append(line)
            last_valid_idx = i
            continue
            
        # Inside a hunk, lines must start with ' ', '+', or '-'
        if in_hunk:
            if line.startswith("+") or line.startswith("-") or line.startswith(" "):
                # Special check: If a line starts with "- " but looks like a conversational bullet point
                # (e.g. followed by a backtick or a common word), we might be careful, 
                # but standard practice is to trust the hunk until it stops matching.
                cleaned_lines.append(line)
                last_valid_idx = i
            else:
                # We hit something that isn't a diff line. The hunk (and likely diff) ends here.
                break
        else:
            # We haven't hit a hunk yet, and it's not a header? Stop.
            if not line.strip(): 
                cleaned_lines.append(line)
                continue
            break

    final_diff = "\n".join(cleaned_lines[:last_valid_idx+1]).strip()
    
    # 4. Safety checks
    check_text = final_diff.lower()
    placeholders = ["removed line", "added line", "context line", "old code", "new code"]
    if any(p in check_text for p in placeholders):
        raise ValueError("Model returned a placeholder template instead of actual code.")

    if "@@ " not in final_diff:
        raise ValueError("Missing unified diff hunks (@@).")

    # 5. Fix missing headers if necessary
    if "--- " not in final_diff:
        final_diff = "--- a/FILE\n+++ b/FILE\n" + final_diff
    elif "+++ " not in final_diff:
        parts = final_diff.split("\n")
        parts.insert(1, "+++ b/FILE")
        final_diff = "\n".join(parts)

    return final_diff


def apply_diff(diff_path: Path, target: Path):
    import re
    raw_diff = diff_path.read_text(encoding="utf-8")
    original_text = read_text_file(target)
    original_lines = original_text.splitlines()

    # Parse into hunks
    hunks = []
    current_hunk = None
    
    for line in raw_diff.splitlines():
        if line.startswith("@@"):
            if current_hunk:
                hunks.append(current_hunk)
            # @@ -start,len +start,len @@
            match = re.search(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
            if match:
                current_hunk = {
                    "old_start": int(match.group(1)),
                    "old_len": int(match.group(2) or 1),
                    "lines": []
                }
        elif current_hunk and (line.startswith("+") or line.startswith("-") or line.startswith(" ")):
            current_hunk["lines"].append(line)
            
    if current_hunk:
        hunks.append(current_hunk)

    if not hunks:
        # Fallback for diffs that might be missing @@ but have -/+
        # We use a very simplified version for this case
        removed = []
        added = []
        for line in raw_diff.splitlines():
            if line.startswith("-") and not line.startswith("---"):
                removed.append(line[1:])
            elif line.startswith("+") and not line.startswith("+++"):
                added.append(line[1:])
        
        if not removed: return # Nothing to do
        
        new_lines = []
        rem_ptr = 0
        for line in original_lines:
            if rem_ptr < len(removed) and line.strip() == removed[rem_ptr].strip():
                rem_ptr += 1
                if rem_ptr <= len(added):
                    new_lines.append(added[rem_ptr-1])
                continue
            new_lines.append(line)
        new_lines.extend(added[rem_ptr:])
        target.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return

    # Apply hunks from bottom to top
    new_content_lines = list(original_lines)
    
    for hunk in reversed(hunks):
        search_lines = [l[1:] for l in hunk["lines"] if not l.startswith("+")]
        replace_lines = [l[1:] for l in hunk["lines"] if not l.startswith("-")]
        
        found_idx = -1
        
        # Stage 1: Exact match in the whole file
        for i in range(len(new_content_lines) - len(search_lines) + 1):
            match = True
            for j in range(len(search_lines)):
                if search_lines[j].strip() != new_content_lines[i+j].strip():
                    match = False
                    break
            if match:
                found_idx = i
                break
        
        # Stage 2: Context-only matching (Ignore lines starting with - in search)
        if found_idx == -1:
            # We match only the lines starting with ' '
            context_indices = [idx for idx, l in enumerate(hunk["lines"]) if l.startswith(" ")]
            if context_indices:
                for i in range(len(new_content_lines) - len(hunk["lines"]) + 1):
                    match = True
                    for ci in context_indices:
                        if hunk["lines"][ci][1:].strip() != new_content_lines[i+ci].strip():
                            match = False
                            break
                    if match:
                        found_idx = i
                        # We must adjust search_lines length because we are matching against the full hunk length
                        # The replacement will happen for the slice [i : i + hunk_len]
                        search_len = len(hunk["lines"]) # This is wrong, hunk lines include +
                        # Let's just use the range logic
                        break
        
        if found_idx == -1:
             # Stage 3: Best effort match for just the subtracted lines
             subtracted = [l[1:] for l in hunk["lines"] if l.startswith("-")]
             if subtracted:
                 for i in range(len(new_content_lines)):
                     if new_content_lines[i].strip() == subtracted[0].strip():
                         new_content_lines[i:i+len(subtracted)] = [l[1:] for l in hunk["lines"] if l.startswith("+")]
                         found_idx = -2
                         break

        if found_idx == -1:
            raise ValueError(f"Could not find a place to apply hunk at line {hunk['old_start']}. The surrounding code might have changed or was described incorrectly.")
        
        elif found_idx >= 0:
            # The replace_lines needs to be derived from the ORIGINAL hunk lines sequence to preserve relative ordering
            # hunk['lines'] contains ' ' and '-' and '+'
            # We replace the range in the file with only the ' ' and '+' lines from the hunk
            final_lines = [l[1:] for l in hunk["lines"] if not l.startswith("-")]
            # The length to replace is the number of lines in the hunk that were NOT additions
            remove_count = len([l for l in hunk["lines"] if not l.startswith("+")])
            new_content_lines[found_idx : found_idx + remove_count] = final_lines

    target.write_text("\n".join(new_content_lines) + "\n", encoding="utf-8")
