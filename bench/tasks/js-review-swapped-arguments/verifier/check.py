# HIDDEN_VERIFIER_ONLY
import json
import os
from pathlib import Path

root = Path(os.environ["WORKDIR"])
expected = json.loads((Path(os.environ["VERIFIER_DIR"]) / "expected.json").read_text())
answer_path = root / "answer.json"
if not answer_path.is_file():
    raise SystemExit("missing answer.json")
try:
    got = json.loads(answer_path.read_text())
except json.JSONDecodeError as exc:
    raise SystemExit(f"answer.json is not JSON: {exc}") from exc
if not isinstance(got, dict):
    raise SystemExit("answer.json must be an object")
if type(got.get("line")) is not int:
    raise SystemExit("line must be an integer")
if got.get("file") != expected["file"]:
    raise SystemExit("file does not match")
if got.get("line") != expected["line"]:
    raise SystemExit("line does not match")
if got.get("category") != expected["category"]:
    raise SystemExit("category does not match")
