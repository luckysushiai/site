"""Run one task under the oracle, nop, or wrong agent.

The agent workspace is a copy of ``environment/`` with the Dockerfile left
out. ``oracle/`` and ``verifier/`` are not copied. The verifier then runs
with ``WORKDIR`` pointing at that copy, which is the same split BenchFlow
uses between the image and ``verifier/test.sh``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
TASKS = BENCH / "tasks"
HARNESS_NAME = "local-harbor-style"
HARNESS_VERSION = "0.1.0"
AGENTS = ("oracle", "nop", "wrong")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _copy_workspace(environment: Path, dest: Path) -> None:
    if not environment.is_dir():
        raise FileNotFoundError(f"missing environment/: {environment}")
    for path in environment.rglob("*"):
        relative = path.relative_to(environment)
        if relative == Path("Dockerfile"):
            continue
        target = dest / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def execute(task: str, agent: str, timeout_sec: float = 60.0) -> dict:
    if agent not in AGENTS:
        raise ValueError(f"agent must be one of {AGENTS}")
    task_dir = TASKS / task
    if not task_dir.is_dir():
        raise FileNotFoundError(f"no such task: {task}")
    verifier = task_dir / "verifier" / "test.sh"
    if not verifier.is_file():
        raise FileNotFoundError(f"missing verifier: {verifier}")
    started = utc_now()
    logs: list[str] = []
    with tempfile.TemporaryDirectory(prefix=f"bench-{task}-") as tmp:
        workdir = Path(tmp) / "work"
        workdir.mkdir()
        _copy_workspace(task_dir / "environment", workdir)
        _reject_hidden_marker(workdir)
        if agent != "nop":
            script = task_dir / agent / "solve.sh"
            if not script.is_file():
                raise FileNotFoundError(f"missing {agent}/solve.sh")
            env = dict(**_base_env(), WORKDIR=str(workdir))
            proc = subprocess.run(
                ["bash", str(script)],
                cwd=workdir,
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout_sec,
                check=False,
            )
            logs.append(f"--- {agent} solve.sh exit {proc.returncode} ---\n{proc.stdout}{proc.stderr}")
            if proc.returncode != 0:
                finished = utc_now()
                return _result(task, agent, "fail", started, finished, "\n".join(logs))
        reward_path = Path(tmp) / "reward.txt"
        env = dict(
            **_base_env(),
            WORKDIR=str(workdir),
            VERIFIER_DIR=str(task_dir / "verifier"),
            REWARD_PATH=str(reward_path),
        )
        proc = subprocess.run(
            ["bash", str(verifier)],
            cwd=workdir,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
            check=False,
        )
        logs.append(f"--- verifier exit {proc.returncode} ---\n{proc.stdout}{proc.stderr}")
        reward = reward_path.read_text().strip() if reward_path.is_file() else ""
        passed = proc.returncode == 0 and reward == "1"
        if proc.returncode == 0 and reward != "1":
            logs.append(f"reward file was {reward!r}, expected 1")
            passed = False
        if proc.returncode != 0 and reward == "1":
            logs.append("verifier failed but reward was 1")
            passed = False
        finished = utc_now()
        return _result(
            task,
            agent,
            "pass" if passed else "fail",
            started,
            finished,
            "\n".join(logs),
        )


def _base_env() -> dict[str, str]:
    """Pass a normal PATH through, and drop credentials.

    Verifiers are local programs. They must not see provider keys even if the
    host shell has them.
    """
    drop_fragments = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(part in key.upper() for part in drop_fragments)
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.setdefault("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
    return env


def _reject_hidden_marker(workdir: Path) -> None:
    for path in workdir.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if "HIDDEN_VERIFIER_ONLY" in text:
            raise RuntimeError(f"hidden verifier marker leaked into {path}")


def _result(task: str, agent: str, verdict: str, started: str, finished: str, log: str) -> dict:
    return {
        "task": task,
        "agent": agent,
        "verifier_result": verdict,
        "started_at": started,
        "finished_at": finished,
        "log": log,
        "harness_name": HARNESS_NAME,
        "harness_version": HARNESS_VERSION,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one bench task agent")
    parser.add_argument("task")
    parser.add_argument("agent", choices=AGENTS)
    parser.add_argument("--log", action="store_true", help="print verifier logs to stderr")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)
    try:
        outcome = execute(args.task, args.agent, timeout_sec=args.timeout)
    except (OSError, subprocess.TimeoutExpired, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.log or outcome["verifier_result"] == "fail" and args.log:
        print(outcome["log"], file=sys.stderr)
    print(outcome["verifier_result"])
    return 0 if outcome["verifier_result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
