from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_schema(schema_path: str | Path) -> dict:
    path = Path(schema_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return json.loads(path.read_text(encoding="utf-8"))


def validate_data(data: Any, schema: dict) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if not errors:
        return

    lines = []
    for error in errors[:20]:
        location = ".".join(str(part) for part in error.path) or "<root>"
        lines.append(f"{location}: {error.message}")
    raise ValueError("Schema validation failed:\n" + "\n".join(lines))


def validate_file(data: Any, schema_path: str | Path) -> None:
    validate_data(data, load_schema(schema_path))
