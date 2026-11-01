"""Validate a run record against bench/runs/schema.json.

The checker covers the subset of JSON Schema this file uses (type, const,
enum, required, additionalProperties, properties, items, minItems, minimum,
minLength, pattern, anyOf, $ref). It does not depend on the jsonschema package.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.json"
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# Tasks the dry run must cover. Keep this aligned with bench/tasks/.
DRY_RUN_TASKS = (
    "py-review-off-by-one",
    "js-review-swapped-arguments",
    "py-failing-tests-remainder",
    "js-failing-tests-normalize",
    "py-fix-form-encoding",
    "js-fix-coupon-rounding",
    "py-coverage-access",
    "py-mutation-grades",
    "py-tdd-semver",
    "js-tdd-retry-delay",
)


class ValidationError(Exception):
    pass


def _matches_type(instance: object, kind: str) -> bool:
    if kind == "null":
        return instance is None
    if kind == "string":
        return isinstance(instance, str)
    if kind == "boolean":
        return isinstance(instance, bool)
    if kind == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if kind == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if kind == "array":
        return isinstance(instance, list)
    if kind == "object":
        return isinstance(instance, dict)
    raise ValidationError(f"unsupported schema type {kind}")


def _validate(instance: object, schema: dict, defs: dict, path: str) -> None:
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        if name not in defs:
            raise ValidationError(f"{path}: unknown $ref {schema['$ref']}")
        _validate(instance, defs[name], defs, path)
        return
    if "anyOf" in schema:
        errors = []
        for index, option in enumerate(schema["anyOf"]):
            try:
                _validate(instance, option, defs, path)
                return
            except ValidationError as exc:
                errors.append(f"option {index}: {exc}")
        raise ValidationError(f"{path}: anyOf failed ({'; '.join(errors)})")
    if "const" in schema and instance != schema["const"]:
        raise ValidationError(f"{path}: expected {schema['const']!r}, got {instance!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise ValidationError(f"{path}: {instance!r} is not one of {schema['enum']}")
    if "type" in schema:
        kinds = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_matches_type(instance, kind) for kind in kinds):
            raise ValidationError(f"{path}: expected type {schema['type']}, got {type(instance).__name__}")
    if instance is None:
        return
    if "minLength" in schema and isinstance(instance, str) and len(instance) < schema["minLength"]:
        raise ValidationError(f"{path}: shorter than {schema['minLength']}")
    if "pattern" in schema and isinstance(instance, str):
        if re.search(schema["pattern"], instance) is None:
            raise ValidationError(f"{path}: does not match {schema['pattern']}")
    if "minimum" in schema and isinstance(instance, int) and not isinstance(instance, bool):
        if instance < schema["minimum"]:
            raise ValidationError(f"{path}: {instance} < {schema['minimum']}")
    if "minItems" in schema and isinstance(instance, list) and len(instance) < schema["minItems"]:
        raise ValidationError(f"{path}: fewer than {schema['minItems']} items")
    if isinstance(instance, dict) and ("properties" in schema or schema.get("additionalProperties") is False):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                raise ValidationError(f"{path}: missing required field {key}")
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(props))
            if extra:
                raise ValidationError(f"{path}: unexpected fields {extra}")
        for key, value in instance.items():
            if key in props:
                _validate(value, props[key], defs, f"{path}.{key}")
    if isinstance(instance, list) and "items" in schema:
        for index, item in enumerate(instance):
            _validate(item, schema["items"], defs, f"{path}[{index}]")


def validate_record(record: object, schema: dict | None = None) -> None:
    if schema is None:
        schema = json.loads(SCHEMA_PATH.read_text())
    defs = schema.get("$defs", {})
    _validate(record, schema, defs, "$")


def expect_dry_run(record: dict) -> None:
    """Semantic checks for the oracle/nop dry run. No model was called."""
    if record.get("model", {}).get("called") is not False:
        raise ValidationError("dry run must set model.called to false")
    if record.get("model", {}).get("name") is not None or record.get("model", {}).get("version") is not None:
        raise ValidationError("dry run must not name a model that was not called")
    if record.get("recorded_cuts"):
        raise ValidationError("dry run must not apply cuts")
    trials = record.get("trials")
    if not isinstance(trials, list):
        raise ValidationError("trials must be a list")
    seen: dict[tuple[str, str], str] = {}
    for trial in trials:
        if trial.get("run_id") != record.get("run_id"):
            raise ValidationError("trial run_id does not match the record")
        if trial.get("arm") != "no_skill":
            raise ValidationError("dry run trials are the no_skill arm")
        if trial.get("skill_id") is not None:
            raise ValidationError("dry run trials have no skill_id")
        if trial.get("usage") is not None:
            raise ValidationError("dry run must not invent token usage")
        if trial.get("recorded_cuts"):
            raise ValidationError("dry run trial recorded a cut")
        if trial.get("try_number") != 1:
            raise ValidationError("dry run uses try_number 1")
        if trial.get("model_name") is not None or trial.get("model_version") is not None:
            raise ValidationError("dry run trial must not name a model")
        started, finished = trial.get("started_at", ""), trial.get("finished_at", "")
        if not (isinstance(started, str) and isinstance(finished, str) and TIMESTAMP.match(started) and TIMESTAMP.match(finished)):
            raise ValidationError("trial timestamps must be UTC seconds")
        if finished < started:
            raise ValidationError(f"{trial.get('task')} finished before it started")
        agent = trial.get("agent")
        if agent not in {"oracle", "nop"}:
            raise ValidationError(f"dry run agent must be oracle or nop, got {agent}")
        expected = "pass" if agent == "oracle" else "fail"
        if trial.get("verifier_result") != expected:
            raise ValidationError(
                f"{trial.get('task')} {agent} verifier_result is {trial.get('verifier_result')}, expected {expected}"
            )
        seen[(trial.get("task"), agent)] = trial.get("verifier_result")
    for task in DRY_RUN_TASKS:
        for agent in ("oracle", "nop"):
            if (task, agent) not in seen:
                raise ValidationError(f"dry run is missing {task} {agent}")
    extra = sorted({task for task, _agent in seen} - set(DRY_RUN_TASKS))
    if extra:
        raise ValidationError(f"dry run has tasks that are not in the set: {extra}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a skill-ranker run record")
    parser.add_argument("record")
    parser.add_argument(
        "--expect-dry-run",
        action="store_true",
        help="also require the oracle-pass / nop-fail dry-run shape",
    )
    args = parser.parse_args(argv)
    try:
        record = json.loads(Path(args.record).read_text())
        validate_record(record)
        if args.expect_dry_run:
            expect_dry_run(record)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1
    print("valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
