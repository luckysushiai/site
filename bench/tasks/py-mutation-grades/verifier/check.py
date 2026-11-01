# HIDDEN_VERIFIER_ONLY
import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

NEED = 8
ROOT = Path(os.environ["WORKDIR"])
HERE = Path(os.environ["VERIFIER_DIR"])
MUTANTS = [
    ("zero_included", "if score < 0 or score > 100:", "if score <= 0 or score > 100:"),
    ("hundred_excluded", "if score < 0 or score > 100:", "if score < 0 or score >= 100:"),
    ("a_strict", "if score >= 90:", "if score > 90:"),
    ("b_strict", "if score >= 80:", "if score > 80:"),
    ("c_strict", "if score >= 70:", "if score > 70:"),
    ("d_strict", "if score >= 60:", "if score > 60:"),
    ("a_label", 'return "A"', 'return "B"'),
    ("f_label", 'return "F"', 'return "D"'),
    ("range_returns_f", 'raise ValueError("score out of range")', 'return "F"'),
    ("b_moved", "if score >= 80:", "if score >= 85:"),
]
RUNNER = """
import importlib.util
import sys
path, module_dir = sys.argv[1], sys.argv[2]
sys.path.insert(0, module_dir)
spec = importlib.util.spec_from_file_location("agent_tests", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
names = sorted(name for name in dir(mod) if name.startswith("test_") and callable(getattr(mod, name)))
if not names:
    raise SystemExit("no test_ functions")
for name in names:
    getattr(mod, name)()
"""


def ban(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] != "grade":
                    raise SystemExit("import %s is not allowed" % alias.name)
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] != "grade":
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


def passes(src, test_path):
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        (folder / "grade.py").write_text(src)
        proc = subprocess.run(
            [sys.executable, "-c", RUNNER, str(test_path), str(folder)],
            text=True,
            capture_output=True,
            check=False,
        )
        return proc.returncode == 0


def main():
    original = (HERE / "grade_original.py").read_text()
    if (ROOT / "grade.py").read_text() != original:
        raise SystemExit("grade.py was modified")
    test_path = ROOT / "tests" / "test_grade.py"
    if not test_path.is_file():
        raise SystemExit("missing tests/test_grade.py")
    ban(test_path)
    if not passes(original, test_path):
        raise SystemExit("tests do not pass on the original module")
    killed = 0
    for name, old, new in MUTANTS:
        if original.count(old) != 1:
            raise SystemExit("mutant %s is not unique" % name)
        if passes(original.replace(old, new, 1), test_path):
            continue
        killed += 1
    print("killed %d of %d" % (killed, len(MUTANTS)))
    if killed < NEED:
        raise SystemExit("killed %d mutants, need %d" % (killed, NEED))


if __name__ == "__main__":
    main()
