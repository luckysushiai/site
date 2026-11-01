"""Write a dry-run record from the oracle and nop agents. No model calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_trial import HARNESS_NAME, HARNESS_VERSION, TASKS, execute

RUN_ID = "dry-run-2026-11-01"
OUT = Path(__file__).resolve().parents[1] / "runs" / RUN_ID / "run.json"


def build() -> dict:
    trials = []
    tasks = sorted(path.name for path in TASKS.iterdir() if path.is_dir())
    for task in tasks:
        for agent in ("oracle", "nop"):
            outcome = execute(task, agent)
            trials.append(
                {
                    "run_id": RUN_ID,
                    "task": task,
                    "arm": "no_skill",
                    "skill_id": None,
                    "model_name": None,
                    "model_version": None,
                    "harness_name": HARNESS_NAME,
                    "harness_version": HARNESS_VERSION,
                    "try_number": 1,
                    "verifier_result": outcome["verifier_result"],
                    "started_at": outcome["started_at"],
                    "finished_at": outcome["finished_at"],
                    "usage": None,
                    "recorded_cuts": [],
                    "agent": agent,
                }
            )
    return {
        "schema_version": "1.0.0",
        "run_id": RUN_ID,
        "job": "code-review-testing-debugging",
        "model": {"name": None, "version": None, "called": False},
        "harness": {"name": HARNESS_NAME, "version": HARNESS_VERSION},
        "recorded_cuts": [],
        "trials": trials,
    }


def main() -> int:
    record = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    print(OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
