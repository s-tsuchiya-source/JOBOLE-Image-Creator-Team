from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from services.providers import OpenAIProvider, ProviderResult
from services.schema_validator import load_schema, validate_data


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_CONFIG = REPO_ROOT / "configs" / "agents.yaml"
QUALITY_SCHEMA = REPO_ROOT / "schemas" / "quality-gate.schema.json"


def load_cco_prompt() -> str:
    config = yaml.safe_load(AGENTS_CONFIG.read_text(encoding="utf-8")) or {}
    path_value = config["chief"]["codex_cco"]["file"]
    return (REPO_ROOT / path_value).read_text(encoding="utf-8")


def run_codex_gate(
    gate: str,
    *,
    original_request: dict[str, Any],
    upstream_outputs: dict[str, Any],
    provider: OpenAIProvider | None = None,
) -> ProviderResult:
    schema = load_schema(QUALITY_SCHEMA)
    provider = provider or OpenAIProvider()
    input_payload = {
        "gate_to_execute": gate,
        "original_request": original_request,
        "upstream_outputs": upstream_outputs,
        "instruction": (
            "Execute only the requested Quality Gate. Verify traceability, identify root "
            "cause for every issue, and return a decision matching the schema."
        ),
    }
    result = provider.generate_json(
        system_prompt=load_cco_prompt(),
        user_prompt=json.dumps(input_payload, ensure_ascii=False, indent=2),
        schema=schema,
    )
    validate_data(result.data, schema)
    if result.data.get("gate") != gate:
        raise ValueError(
            f"Codex returned gate={result.data.get('gate')!r}; expected {gate!r}."
        )
    return result
