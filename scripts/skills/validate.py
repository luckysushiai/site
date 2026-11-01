#!/usr/bin/env python3
"""Validate data/skills/skills.json against data/skills/schema.json.

Fails if any collected value lacks a url or fetched_at, if a null value
lacks a reason, or if a seed skill is missing. Prints a per-skill count
of null values.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "skills" / "skills.json"
SCHEMA_PATH = ROOT / "data" / "skills" / "schema.json"
SEED_PATH = ROOT / "scripts" / "skills" / "seed.json"

FETCHED_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
URL = re.compile(r"^https://\S+$")


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def walk(node, path: str, errors: list[str]) -> int:
    """Return the number of null values under this node. Record structural errors."""
    nulls = 0
    if isinstance(node, dict) and "value" in node and ("url" in node or "fetched_at" in node or "source" in node):
        url = node.get("url")
        fetched = node.get("fetched_at")
        if not isinstance(url, str) or not URL.match(url):
            errors.append(f"{path} lacks an https url")
        if not isinstance(fetched, str) or not FETCHED_AT.match(fetched):
            errors.append(f"{path} lacks an ISO 8601 fetched_at")
        if node.get("value") is None:
            nulls += 1
            reason = node.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append(f"{path} value is null without a reason")
        return nulls + _walk_children(node, path, errors)
    return _walk_children(node, path, errors)


def _walk_children(node, path: str, errors: list[str]) -> int:
    nulls = 0
    if isinstance(node, dict):
        for key, child in node.items():
            nulls += walk(child, f"{path}.{key}", errors)
    elif isinstance(node, list):
        for index, child in enumerate(node):
            nulls += walk(child, f"{path}[{index}]", errors)
    return nulls


def main() -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    data = json.loads(DATA_PATH.read_text())
    seed = json.loads(SEED_PATH.read_text())
    validator = Draft202012Validator(schema)
    schema_errors = sorted(validator.iter_errors(data), key=lambda err: list(err.path))
    if schema_errors:
        for err in schema_errors[:30]:
            where = "/".join(str(part) for part in err.path) or "(root)"
            print(f"schema: {where}: {err.message}", file=sys.stderr)
        fail(f"{len(schema_errors)} schema error(s)")

    errors: list[str] = []
    skills = data.get("skills") or []
    if len(skills) != 20:
        errors.append(f"expected 20 skills, found {len(skills)}")
    slugs = [item["slug"] for item in skills]
    if len(set(slugs)) != len(slugs):
        errors.append("duplicate skill slugs")
    seed_by_slug = {item["slug"]: item for item in seed}
    if set(seed_by_slug) != set(slugs):
        missing = sorted(set(seed_by_slug) - set(slugs))
        extra = sorted(set(slugs) - set(seed_by_slug))
        errors.append(f"slug set mismatch missing={missing} extra={extra}")
    for skill in skills:
        expected = seed_by_slug.get(skill["slug"])
        if expected and skill["job"] != expected["job"]:
            errors.append(f"{skill['slug']} job is {skill['job']}, seed says {expected['job']}")
        if skill.get("evidence_label") == "measured_by_us":
            errors.append(f"{skill['slug']} uses reserved evidence label measured_by_us")
        measured = False
        for rows in (skill.get("third_party") or {}).values():
            for row in rows:
                if row.get("value") is not None:
                    measured = True
        label = skill.get("evidence_label")
        if measured and label != "measured_by_third_party":
            errors.append(f"{skill['slug']} has a third-party value but evidence_label={label}")
        if not measured and label != "popular_but_unmeasured":
            errors.append(f"{skill['slug']} has no third-party value but evidence_label={label}")
        nulls = walk(skill, skill.get("id", skill.get("slug", "?")), errors)
        print(f"{skill.get('id')} null_fields={nulls}")

    if errors:
        for err in errors:
            print(f"check: {err}", file=sys.stderr)
        fail(f"{len(errors)} check(s) failed")
    print(f"ok skills={len(skills)} schema={SCHEMA_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
