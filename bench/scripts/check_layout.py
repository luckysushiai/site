"""Check the on-disk task layout, and BenchFlow's reader when it is installed.

``bench tasks check`` is the structural reader. Loading ``task.toml`` through
``TaskConfig.model_validate_toml`` is the stricter config parse BenchFlow uses
when it actually loads a legacy Harbor task. Neither step calls a model or a
sandbox. If BenchFlow is not installed, the local layout check still runs and
this script says the BenchFlow check was skipped.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]


def _layout(task: Path) -> list[str]:
    required = [
        task / "instruction.md",
        task / "task.toml",
        task / "environment" / "Dockerfile",
        task / "oracle" / "solve.sh",
        task / "wrong" / "solve.sh",
        task / "verifier" / "test.sh",
    ]
    missing = [str(path.relative_to(BENCH)) for path in required if not path.is_file()]
    if (task / "instruction.md").is_file() and (task / "instruction.md").stat().st_size == 0:
        missing.append(f"{task.name}/instruction.md is empty")
    return missing


def _benchflow(tasks: list[Path]) -> tuple[int, str]:
    bench = shutil.which("bench")
    if importlib.util.find_spec("benchflow") is None or bench is None:
        return 0, "benchflow: skipped (not installed)"
    lines = []
    failed = 0
    from benchflow.task.config import TaskConfig

    for task in tasks:
        try:
            TaskConfig.model_validate_toml((task / "task.toml").read_text())
        except Exception as exc:  # noqa: BLE001 — surface the loader's message
            failed += 1
            lines.append(f"{task.name}: task.toml rejected by BenchFlow ({exc})")
            continue
        proc = subprocess.run(
            [bench, "tasks", "check", str(task)],
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            failed += 1
            lines.append(f"{task.name}: bench tasks check failed\n{proc.stdout}{proc.stderr}")
        else:
            lines.append(f"{task.name}: bench tasks check ok")
    status = "benchflow: ok" if failed == 0 else "benchflow: fail"
    return failed, status + "\n" + "\n".join(lines)


def main() -> int:
    tasks = sorted(path for path in (BENCH / "tasks").iterdir() if path.is_dir())
    problems = []
    for task in tasks:
        problems.extend(_layout(task))
    if problems:
        print("layout: fail", file=sys.stderr)
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"layout: ok ({len(tasks)} tasks)")
    failed, report = _benchflow(tasks)
    print(report)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
