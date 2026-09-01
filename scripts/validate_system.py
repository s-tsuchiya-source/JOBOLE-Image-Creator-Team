from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import yaml
from dotenv import load_dotenv
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

REQUIRED_AGENTS = [
    "recruitment_analyst",
    "production_director",
    "copy_director",
    "art_director",
    "prompt_designer",
    "creative_reviewer",
]

REQUIRED_LIVE_ENV = [
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_CCO_MODEL",
    "OPENAI_IMAGE_MODEL",
    "USDJPY_RATE",
    "ANTHROPIC_INPUT_USD_PER_M",
    "ANTHROPIC_OUTPUT_USD_PER_M",
    "OPENAI_CCO_INPUT_USD_PER_M",
    "OPENAI_CCO_OUTPUT_USD_PER_M",
    "OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION",
]

NUMERIC_LIVE_ENV = {
    "USDJPY_RATE",
    "ANTHROPIC_INPUT_USD_PER_M",
    "ANTHROPIC_OUTPUT_USD_PER_M",
    "OPENAI_CCO_INPUT_USD_PER_M",
    "OPENAI_CCO_OUTPUT_USD_PER_M",
    "OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION",
}

PLACEHOLDER_MARKERS = (
    "ここに",
    "your_api_key",
    "your-api-key",
    "replace_me",
    "changeme",
    "<api",
    "<your",
)


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def validate_live_config(errors: list[str]) -> None:
    for name in REQUIRED_LIVE_ENV:
        raw = os.getenv(name)
        if raw is None or not raw.strip():
            errors.append(f"Missing live setting: {name}")
            continue
        if _looks_like_placeholder(raw):
            errors.append(f"Live setting still looks like a placeholder: {name}")
            continue
        if name in NUMERIC_LIVE_ENV:
            try:
                value = float(raw)
            except ValueError:
                errors.append(f"Live setting must be numeric: {name}")
                continue
            if value <= 0:
                errors.append(f"Live setting must be > 0: {name}")

    quality = os.getenv("OPENAI_IMAGE_QUALITY", "high").strip().lower()
    if quality != "high":
        errors.append(
            f"OPENAI_IMAGE_QUALITY must be high for maximum-quality mode; got {quality!r}"
        )

    mode = os.getenv("PRODUCTION_MODE", "dry-run").strip().lower()
    if mode != "live":
        errors.append(
            "PRODUCTION_MODE is not live. Set PRODUCTION_MODE=live only after all live settings are ready."
        )


def verify_api_credentials(errors: list[str]) -> list[str]:
    """Verify credentials/model access without running text or image generation."""
    verified: list[str] = []

    anthropic_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    anthropic_model = (os.getenv("ANTHROPIC_MODEL") or "").strip()
    if anthropic_key and anthropic_model:
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=anthropic_key)
            model = client.models.retrieve(anthropic_model)
            verified.append(f"Anthropic auth/model: OK ({getattr(model, 'id', anthropic_model)})")
        except Exception as exc:
            errors.append(
                "Anthropic credential/model verification failed: "
                f"{type(exc).__name__}: {exc}"
            )

    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    cco_model = (os.getenv("OPENAI_CCO_MODEL") or "").strip()
    image_model = (os.getenv("OPENAI_IMAGE_MODEL") or "").strip()
    if openai_key and cco_model:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=openai_key)
            model = client.models.retrieve(cco_model)
            verified.append(f"OpenAI auth/CCO model: OK ({getattr(model, 'id', cco_model)})")
            if image_model:
                image = client.models.retrieve(image_model)
                verified.append(
                    f"OpenAI image model: OK ({getattr(image, 'id', image_model)})"
                )
        except Exception as exc:
            errors.append(
                "OpenAI credential/model verification failed: "
                f"{type(exc).__name__}: {exc}"
            )

    return verified


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live-config",
        action="store_true",
        help="Validate API/model/cost settings without making generation API calls.",
    )
    parser.add_argument(
        "--verify-api",
        action="store_true",
        help=(
            "Validate live settings and make metadata-only API calls to verify Anthropic/OpenAI "
            "credentials and configured model access. No text/image generation is performed."
        ),
    )
    args = parser.parse_args()

    errors = []
    verified_messages: list[str] = []
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
    if float(budget.get("stop_and_escalate_yen_per_final_image", 0)) != 400:
        errors.append("stop_and_escalate_yen_per_final_image must be 400")

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

    if args.live_config or args.verify_api:
        validate_live_config(errors)

    if args.verify_api and not errors:
        verified_messages = verify_api_credentials(errors)

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
    if args.live_config or args.verify_api:
        print("Live configuration: PASS")
    for message in verified_messages:
        print(message)
    if args.verify_api:
        print("API credential/model verification: PASS (no text/image generation was performed)")


if __name__ == "__main__":
    main()
