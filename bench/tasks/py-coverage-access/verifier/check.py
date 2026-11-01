# HIDDEN_VERIFIER_ONLY
import ast
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

LINE_MIN = 0.90
BRANCH_MIN = 0.80
ROOT = Path(os.environ["WORKDIR"])
HERE = Path(os.environ["VERIFIER_DIR"])

HEADER = """
_LINES = set()
_BRANCHES = set()

def _hit_line(n):
    _LINES.add(n)

def _hit_branch(i, taken):
    _BRANCHES.add((i, bool(taken)))
"""


def ban(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] != "access":
                    raise SystemExit("import %s is not allowed" % alias.name)
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] != "access":
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


class Instrument(ast.NodeTransformer):
    def __init__(self):
        self.n = 0
        self.executable = set()

    def _probe_line(self, lineno):
        self.executable.add(lineno)
        return ast.Expr(
            value=ast.Call(
                func=ast.Name(id="_hit_line", ctx=ast.Load()),
                args=[ast.Constant(lineno)],
                keywords=[],
            )
        )

    def _probe_branch(self, index, taken):
        return ast.Expr(
            value=ast.Call(
                func=ast.Name(id="_hit_branch", ctx=ast.Load()),
                args=[ast.Constant(index), ast.Constant(taken)],
                keywords=[],
            )
        )

    def _inject(self, body):
        rewritten = []
        for stmt in body:
            rewritten.append(self._probe_line(stmt.lineno))
            rewritten.append(self.visit(stmt))
        return rewritten

    def visit_FunctionDef(self, node):
        node.body = self._inject(node.body)
        return node

    def visit_If(self, node):
        index = self.n
        self.n += 1
        node.test = self.visit(node.test)
        node.body = self._inject(node.body)
        node.body.insert(0, self._probe_branch(index, True))
        if node.orelse:
            node.orelse = self._inject(node.orelse)
        else:
            node.orelse = []
        node.orelse.insert(0, self._probe_branch(index, False))
        return node


def instrument(src):
    tree = ast.parse(src)
    tool = Instrument()
    tree.body = tool._inject(tree.body)
    ast.fix_missing_locations(tree)
    return HEADER + "\n" + ast.unparse(tree), tool.executable, tool.n


def run_tests(module_dir, test_path):
    sys.path.insert(0, str(module_dir))
    sys.modules.pop("access", None)
    sys.modules.pop("agent_tests", None)
    import access

    spec = importlib.util.spec_from_file_location("agent_tests", test_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    names = sorted(
        name for name in dir(module) if name.startswith("test_") and callable(getattr(module, name))
    )
    if not names:
        raise SystemExit("no test_ functions")
    for name in names:
        getattr(module, name)()
    return access


def main():
    original = (HERE / "access_original.py").read_text()
    if (ROOT / "access.py").read_text() != original:
        raise SystemExit("access.py was modified")
    test_path = ROOT / "tests" / "test_access.py"
    if not test_path.is_file():
        raise SystemExit("missing tests/test_access.py")
    ban(test_path)
    source, executable, branches = instrument(original)
    if not executable or branches == 0:
        raise SystemExit("nothing to measure")
    with tempfile.TemporaryDirectory() as tmp:
        module_dir = Path(tmp)
        (module_dir / "access.py").write_text(source)
        try:
            module = run_tests(module_dir, test_path)
        except Exception as exc:
            raise SystemExit("tests failed: %s" % exc) from exc
        hit_lines = set(module._LINES) & executable
        line_ratio = len(hit_lines) / len(executable)
        branch_ratio = len(module._BRANCHES) / (2 * branches)
        print("line %.3f branch %.3f" % (line_ratio, branch_ratio))
        if line_ratio < LINE_MIN or branch_ratio < BRANCH_MIN:
            raise SystemExit(
                "coverage below the threshold (line %.3f, branch %.3f)"
                % (line_ratio, branch_ratio)
            )


if __name__ == "__main__":
    main()
