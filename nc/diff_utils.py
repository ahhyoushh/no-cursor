from pathlib import Path
from .utils import read_text_file


def validate_unified_diff(diff: str):
    if not diff.startswith("--- a/FILE"):
        raise ValueError("invalid diff header")

    if "+++ b/FILE" not in diff:
        raise ValueError("invalid diff header")

    if not any(
        line.startswith("+") or line.startswith("-")
        for line in diff.splitlines()
        if not line.startswith("+++")
        and not line.startswith("---")
    ):
        raise ValueError("diff has no changes")


def apply_diff(diff_path: Path, target: Path):
    """
    Deterministic single-file apply.
    Ignores hunk headers and context.
    """

    raw_diff = diff_path.read_text(encoding="utf-8")
    original_text = read_text_file(target)
    original_lines = original_text.splitlines()

    removed = []
    added = []

    for line in raw_diff.splitlines():
        if line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])

    new_lines = []
    i = 0

    for line in original_lines:
        if removed and line == removed[0]:
            removed.pop(0)
            if added:
                new_lines.append(added.pop(0))
            continue
        new_lines.append(line)

    # remaining additions go at end
    new_lines.extend(added)

    # write file directly (this is the fix)
    target.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
