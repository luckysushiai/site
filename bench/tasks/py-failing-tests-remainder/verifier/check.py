# HIDDEN_VERIFIER_ONLY
import ast
import subprocess
import sys
import tempfile
from pathlib import Path
import os

ROOT = Path(os.environ['WORKDIR'])
HERE = Path(os.environ['VERIFIER_DIR'])

def ban(path, allowed):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in allowed:
                    raise SystemExit("import %s is not allowed" % alias.name)
        elif isinstance(node, ast.ImportFrom):
            root_name = (node.module or "").split(".")[0]
            if root_name not in allowed:
                raise SystemExit("import from %s is not allowed" % node.module)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"open", "exec", "eval", "compile", "__import__"}:
                raise SystemExit("call %s is not allowed" % node.func.id)
        elif isinstance(node, ast.Attribute) and node.attr in {
            "getsource",
            "getsourcefile",
            "read_text",
            "read_bytes",
        }:
            raise SystemExit("attribute %s is not allowed" % node.attr)

RUNNER = '\nimport importlib.util\nimport sys\npath, module_dir = sys.argv[1], sys.argv[2]\nsys.path.insert(0, module_dir)\nspec = importlib.util.spec_from_file_location("agent_tests", path)\nmod = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(mod)\nnames = sorted(name for name in dir(mod) if name.startswith("test_") and callable(getattr(mod, name)))\nif not names:\n    raise SystemExit("no test_ functions")\nfailed = 0\nfor name in names:\n    try:\n        getattr(mod, name)()\n    except Exception as exc:\n        failed += 1\n        print("FAIL %s: %s" % (name, exc))\nprint("failed %d of %d" % (failed, len(names)))\nraise SystemExit(1 if failed else 0)\n'

def outcome(src, tests):
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        (folder / "money.py").write_text(src)
        failed = False
        for test in tests:
            proc = subprocess.run(
                [sys.executable, "-c", RUNNER, str(test), str(folder)],
                text=True,
                capture_output=True,
                check=False,
            )
            if proc.returncode != 0:
                failed = True
                sys.stdout.write(proc.stdout)
                sys.stdout.write(proc.stderr)
        return "fail" if failed else "pass"

def main():
    tests = sorted((ROOT / "tests").glob("test_*.py"))
    if not tests:
        raise SystemExit("missing tests/test_*.py")
    for test in tests:
        ban(test, {"money"})
    buggy = (HERE / "buggy_money.py").read_text()
    if outcome(buggy, tests) != "fail":
        raise SystemExit("tests did not fail on the buggy module")
    for name in ("fixed_a.py", "fixed_b.py"):
        if outcome((HERE / name).read_text(), tests) != "pass":
            raise SystemExit("tests did not pass on " + name)

if __name__ == "__main__":
    main()
