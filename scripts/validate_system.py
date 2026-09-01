from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


REQUIRED_AGENTS = [
    "recruitment_analyst",
    "production_director",
    "copy_director",
    "art_director",
    "prompt_designer",
    "creative_reviewer",
]


def main() -> None:
    errors = []
    agents_config = yaml.safe_load((REPO_ROOT / "configs" / "agents.yaml").read_text(encoding="utf-8"))
    workflow = yaml.safe_load((REPO_ROOT / "configs" / "workflow.yaml").read_text(encoding="utf-8"))
    quality = yaml.safe_load((REPO_ROOT / "configs" / "quality.yaml").read_text(encoding="utf-8"))

    cco_file = REPO_ROOT / agents_config["chief"]["codex_cco"]["file"]
    if not cco_file.exists():
        errors.append(f"Missing Codex CCO role: {cco_file}")

    for name in REQUIRED_AGENTS:
        config = agents_config.get("agents", {}).get(name)
        if not config:
            errors.append(f"Missing agent config: {name}")
            continue
        role_path = REPO_ROOT / config["file"]
        schema_path = REPO_ROOT / config["schema"]
        if not role_path.exists():
            errors.append(f"Missing role file: {role_path}")
        if not schema_path.exists():
            errors.append(f"Missing schema: {schema_path}")
            continue
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except Exception as exc:
            errors.append(f"Invalid schema {schema_path}: {exc}")

    quality_schema = REPO_ROOT / "schemas" / "quality-gate.schema.json"
    try:
        Draft202012Validator.check_schema(
            json.loads(quality_schema.read_text(encoding="utf-8"))
        )
    except Exception as exc:
        errors.append(f"Invalid quality gate schema: {exc}")

    steps = workflow.get("workflow", {}).get("steps", [])
    expected_order = [
        "recruitment_analysis",
        "codex_fact_gate",
        "production_strategy",
        "codex_strategy_gate",
        "copy_direction",
        "art_direction",
        "prompt_design",
        "codex_direction_gate",
        "image_generation",
        "creative_review",
        "codex_final_traceability_gate",
    ]
    positions = {step: index for index, step in enumerate(steps)}
    for previous, following in zip(expected_order, expected_order[1:]):
        if previous not in positions or following not in positions:
            errors.append(f"Workflow missing required step: {previous} or {following}")
        elif positions[previous] >= positions[following]:
            errors.append(f"Workflow order invalid: {previous} must precede {following}")

    q = quality.get("quality", {})
    if int(q.get("max_revision_count", -1)) != 3:
        errors.append("max_revision_count must currently be 3 for quality-first mode")
    budget = q.get("budget", {})
    if float(budget.get("target_max_yen_per_final_image", 0)) != 400:
        errors.append("target_max_yen_per_final_image must be 400")

    required_runtime_files = [
        "services/providers.py",
        "services/agent_runner.py",
        "services/quality_gate.py",
        "services/pipeline_stages.py",
        "services/image_generator.py",
        "services/image_review.py",
        "services/creative_pipeline.py",
        "services/manifest.py",
        "services/usage_tracker.py",
        "scripts/run_production.py",
    ]
    for relative in required_runtime_files:
        if not (REPO_ROOT / relative).exists():
            errors.append(f"Missing runtime file: {relative}")

    if errors:
        print("SYSTEM VALIDATION: FAIL")
        for error in errors:
            print(f"[NG] {error}")
        raise SystemExit(2)

    print("SYSTEM VALIDATION: PASS")
    print(f"Agents: {len(REQUIRED_AGENTS)} Claude specialists")
    print("Codex CCO: configured")
    print("Quality Gates: 4")
    print("Revision limit: 3")
    print("Target max cost: 400 JPY/final image")
    print("Runtime pipeline: configured")


if __name__ == "__main__":
    main()
