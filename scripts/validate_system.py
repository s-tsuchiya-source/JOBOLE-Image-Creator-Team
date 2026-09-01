from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import yaml
from dotenv import load_dotenv
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from services.image_generator import check_image_backend


REQUIRED_AGENTS = [
    "recruitment_analyst",
    "production_director",
    "copy_director",
    "art_director",
    "prompt_designer",
    "creative_reviewer",
]


def _resolved(command: str) -> str | None:
    return shutil.which(command)


def _windows_safe(executable: str, args: list[str]) -> list[str]:
    if os.name == "nt" and Path(executable).suffix.lower() in {".cmd", ".bat"}:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", executable, *args]
    return [executable, *args]


def _clean_env(*keys: str) -> dict[str, str]:
    env = dict(os.environ)
    for key in keys:
        env.pop(key, None)
    return env


def _run_version(command: str) -> tuple[bool, str]:
    executable = _resolved(command)
    if not executable:
        return False, f"command not found: {command}"
    completed = subprocess.run(
        _windows_safe(executable, ["--version"]),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    text = (completed.stdout or completed.stderr or "").strip()
    return completed.returncode == 0, text or executable


def validate_text_runtime(errors: list[str], messages: list[str]) -> None:
    """Validate only Claude Code / Codex CLI availability.

    This intentionally does not validate the image backend so --verify-login can
    be used before a local image server is installed.
    """
    claude_command = os.getenv("CLAUDE_CLI_COMMAND", "claude")
    codex_command = os.getenv("CODEX_CLI_COMMAND", "codex")

    ok, detail = _run_version(claude_command)
    if ok:
        messages.append(f"Claude Code CLI: OK ({detail})")
    else:
        errors.append(f"Claude Code CLI unavailable: {detail}")

    ok, detail = _run_version(codex_command)
    if ok:
        messages.append(f"Codex CLI: OK ({detail})")
    else:
        errors.append(f"Codex CLI unavailable: {detail}")

    mode = os.getenv("PRODUCTION_MODE", "dry-run").strip().lower()
    if mode not in {"dry-run", "live"}:
        errors.append("PRODUCTION_MODE must be dry-run or live")

    if (os.getenv("ANTHROPIC_API_KEY") or "").strip():
        messages.append(
            "NOTE: ANTHROPIC_API_KEY exists in parent .env but will be stripped from Claude Code child processes."
        )


def validate_image_runtime(errors: list[str], messages: list[str]) -> None:
    backend = os.getenv("IMAGE_BACKEND", "openvino_ovms").strip().lower()
    webui_names = {"local", "local_webui", "webui", "forge", "automatic1111"}
    openvino_names = {"openvino", "openvino_ovms", "ovms", "intel_openvino"}

    if backend in webui_names:
        url = (os.getenv("LOCAL_IMAGE_API_URL") or "").strip()
        if not url:
            errors.append("LOCAL_IMAGE_API_URL is required for local WebUI image mode")
        else:
            messages.append(f"Image backend: local_webui ({url})")
        return

    if backend in openvino_names:
        url = (os.getenv("OPENVINO_IMAGE_API_URL") or "").strip()
        model = (os.getenv("OPENVINO_IMAGE_MODEL") or "").strip()
        missing = []
        if not url:
            missing.append("OPENVINO_IMAGE_API_URL")
        if not model:
            missing.append("OPENVINO_IMAGE_MODEL")
        if missing:
            errors.append("OpenVINO image backend missing: " + ", ".join(missing))
        else:
            messages.append(f"Image backend: OpenVINO OVMS ({url}, model={model})")
        return

    if backend in {"openai", "openai_api"}:
        required = (
            "OPENAI_API_KEY",
            "OPENAI_IMAGE_MODEL",
            "USDJPY_RATE",
            "OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION",
        )
        missing = [name for name in required if not (os.getenv(name) or "").strip()]
        if missing:
            errors.append("OpenAI image backend missing: " + ", ".join(missing))
        if os.getenv("OPENAI_IMAGE_QUALITY", "high").strip().lower() != "high":
            errors.append("OPENAI_IMAGE_QUALITY must be high in maximum-quality mode")
        messages.append("Image backend: OpenAI Image API")
        return

    errors.append(
        f"Unsupported IMAGE_BACKEND={backend!r}. Use openvino_ovms, local_webui, or openai."
    )


def verify_logins(errors: list[str], messages: list[str]) -> None:
    claude_command = os.getenv("CLAUDE_CLI_COMMAND", "claude")
    codex_command = os.getenv("CODEX_CLI_COMMAND", "codex")
    claude_exe = _resolved(claude_command)
    codex_exe = _resolved(codex_command)
    if not claude_exe or not codex_exe:
        errors.append("Cannot verify login until both Claude Code and Codex CLI are installed.")
        return

    claude_args = [
        "-p",
        "--output-format",
        "json",
        "--max-turns",
        "1",
        "Return exactly the text OK and nothing else.",
    ]
    claude = subprocess.run(
        _windows_safe(claude_exe, claude_args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_clean_env("ANTHROPIC_API_KEY"),
        cwd=str(REPO_ROOT),
        timeout=120,
        check=False,
    )
    if claude.returncode == 0:
        messages.append("Claude Code subscription login: OK")
    else:
        errors.append("Claude Code login verification failed: " + (claude.stderr or claude.stdout).strip())

    with tempfile.TemporaryDirectory(prefix="jobole_login_") as tmpdir:
        output_path = Path(tmpdir) / "codex.txt"
        codex_args = [
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--output-last-message",
            str(output_path),
            "-",
        ]
        codex = subprocess.run(
            _windows_safe(codex_exe, codex_args),
            input="Return exactly the text OK and nothing else.",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_clean_env("OPENAI_API_KEY"),
            cwd=str(REPO_ROOT),
            timeout=180,
            check=False,
        )
        if codex.returncode == 0:
            messages.append("Codex ChatGPT login: OK")
        else:
            errors.append("Codex login verification failed: " + (codex.stderr or codex.stdout).strip())


def validate_structure(errors: list[str]) -> None:
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
            Draft202012Validator.check_schema(
                json.loads(schema_path.read_text(encoding="utf-8"))
            )
        except Exception as exc:
            errors.append(f"Invalid schema {schema_path}: {exc}")

    quality_schema = REPO_ROOT / "schemas" / "quality-gate.schema.json"
    try:
        Draft202012Validator.check_schema(
            json.loads(quality_schema.read_text(encoding="utf-8"))
        )
    except Exception as exc:
        errors.append(f"Invalid quality gate schema: {exc}")

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
    steps = workflow.get("workflow", {}).get("steps", [])
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runtime-config",
        action="store_true",
        help="Check Claude/Codex CLI executables and selected image backend configuration without generation.",
    )
    parser.add_argument(
        "--verify-login",
        action="store_true",
        help="Verify Claude/Codex subscription login independently of image backend configuration.",
    )
    parser.add_argument(
        "--verify-image",
        action="store_true",
        help="Check the selected image backend without generating an image.",
    )
    args = parser.parse_args()

    errors: list[str] = []
    messages: list[str] = []
    validate_structure(errors)

    if args.runtime_config:
        validate_text_runtime(errors, messages)
        validate_image_runtime(errors, messages)
    elif args.verify_login:
        validate_text_runtime(errors, messages)
    elif args.verify_image:
        validate_image_runtime(errors, messages)

    if args.verify_login and not errors:
        verify_logins(errors, messages)
    if args.verify_image and not errors:
        try:
            info = check_image_backend()
            messages.append("Image backend connection: OK " + json.dumps(info, ensure_ascii=False))
        except Exception as exc:
            errors.append(f"Image backend check failed: {type(exc).__name__}: {exc}")

    if errors:
        print("SYSTEM VALIDATION: FAIL")
        for error in errors:
            print(f"[NG] {error}")
        raise SystemExit(2)

    print("SYSTEM VALIDATION: PASS")
    print(f"Agents: {len(REQUIRED_AGENTS)} Claude specialists")
    print("Codex CCO: ChatGPT-login CLI")
    print("Quality Gates: 4")
    print("Revision limit: 3")
    print("Target max cost: 400 JPY/final image")
    print("Text API keys required: NO")
    for message in messages:
        print(message)
    if args.verify_login:
        print("Subscription login verification: PASS")
    if args.verify_image:
        print("Image backend verification: PASS (no image was generated)")


if __name__ == "__main__":
    main()
