"""Fail if hidden verifier material is visible to the agent."""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
MARKER = "HIDDEN_VERIFIER_ONLY"


def main() -> int:
    problems = []
    tasks = sorted(path for path in (BENCH / "tasks").iterdir() if path.is_dir())
    if len(tasks) < 10:
        problems.append(f"expected at least 10 tasks, found {len(tasks)}")
    for task in tasks:
        visible = [task / "instruction.md", task / "environment"]
        for root in visible:
            files = [root] if root.is_file() else list(root.rglob("*"))
            for path in files:
                if not path.is_file():
                    continue
                text = path.read_text(errors="replace")
                if MARKER in text:
                    problems.append(f"{path} contains {MARKER}")
        verifier = task / "verifier"
        if not any(MARKER in path.read_text(errors="replace") for path in verifier.rglob("*") if path.is_file()):
            problems.append(f"{task.name}: verifier has no hidden marker")
        if (task / "tests").exists() or (task / "solution").exists():
            problems.append(f"{task.name}: legacy tests/ or solution/ would duplicate verifier/ or oracle/")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"hidden-ok {len(tasks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
