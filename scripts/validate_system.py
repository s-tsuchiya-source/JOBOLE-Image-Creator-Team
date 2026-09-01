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


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# For local project operation, .env is the source of truth.
load_dotenv(REPO_ROOT / ".env", override=True)

from services.image_generator import check_image_backend


REQUIRED_AGENTS = [
    "recruitment_analyst",
    "creative_director",
    "creative_reviewer",
]

EXPECTED_WORKFLOW = [
    "intake",
    "recruitment_analysis",
    "codex_fact_check",
    "creative_direction",
    "codex_direction_approval",
    "image_generation",
    "creative_review",
    "codex_final_qa",
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


def validate_structure(errors: list[str], messages: list[str]) -> None:
    agents_path = REPO_ROOT / "configs" / "agents.yaml"
    workflow_path = REPO_ROOT / "configs" / "workflow.yaml"
    agents = yaml.safe_load(agents_path.read_text(encoding="utf-8")) or {}
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}

    chief = agents.get("chief", {}).get("codex_cco", {})
    cco_path = REPO_ROOT / str(chief.get("file") or "")
    if not chief or not cco_path.exists():
        errors.append("Codex CCO role is missing")

    configured_agents = agents.get("agents", {})
    for name in REQUIRED_AGENTS:
        config = configured_agents.get(name)
        if not config:
            errors.append(f"Missing active Claude specialist: {name}")
            continue
        role_path = REPO_ROOT / str(config.get("file") or "")
        if not role_path.exists():
            errors.append(f"Missing role file: {role_path}")

    extra_active = sorted(set(configured_agents) - set(REQUIRED_AGENTS))
    if extra_active:
        errors.append("Unexpected active Claude specialists: " + ", ".join(extra_active))

    steps = workflow.get("workflow", {}).get("steps", [])
    positions = {step: index for index, step in enumerate(steps)}
    for step in EXPECTED_WORKFLOW:
        if step not in positions:
            errors.append(f"Workflow missing Phase 1 step: {step}")
    for previous, following in zip(EXPECTED_WORKFLOW, EXPECTED_WORKFLOW[1:]):
        if previous in positions and following in positions and positions[previous] >= positions[following]:
            errors.append(f"Workflow order invalid: {previous} must precede {following}")

    deprecated_run = REPO_ROOT / "scripts" / "run_production.py"
    if not deprecated_run.exists():
        errors.append("Deprecated run_production shim is missing")

    required_python_utilities = [
        "scripts/create_project_from_intake.py",
        "scripts/input_loader.py",
        "services/image_generator.py",
        "services/overlay_renderer.py",
    ]
    for relative in required_python_utilities:
        if not (REPO_ROOT / relative).exists():
            errors.append(f"Missing Phase 1 utility: {relative}")

    messages.append("Architecture: VSCode Codex CCO + 3 Claude specialists + Python file/image utilities")


def validate_cli_runtime(errors: list[str], messages: list[str]) -> None:
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


def verify_logins(errors: list[str], messages: list[str]) -> None:
    claude_exe = _resolved(os.getenv("CLAUDE_CLI_COMMAND", "claude"))
    codex_exe = _resolved(os.getenv("CODEX_CLI_COMMAND", "codex"))
    if not claude_exe or not codex_exe:
        errors.append("Cannot verify login until Claude Code and Codex CLI are installed")
        return

    claude = subprocess.run(
        _windows_safe(
            claude_exe,
            ["-p", "--output-format", "json", "--max-turns", "1", "Return exactly OK."],
        ),
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
        codex = subprocess.run(
            _windows_safe(
                codex_exe,
                [
                    "exec",
                    "--ephemeral",
                    "--sandbox",
                    "read-only",
                    "--output-last-message",
                    str(output_path),
                    "-",
                ],
            ),
            input="Return exactly OK.",
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the simplified Phase 1 architecture.")
    parser.add_argument("--runtime-config", action="store_true")
    parser.add_argument("--verify-login", action="store_true")
    parser.add_argument("--verify-image", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    messages: list[str] = []
    validate_structure(errors, messages)

    if args.runtime_config or args.verify_login:
        validate_cli_runtime(errors, messages)
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
    print("Claude specialists: 3")
    print("Codex CCO: VSCode highest authority")
    print("Python AI orchestration: DISABLED")
    print("Text API keys required: NO")
    for message in messages:
        print(message)
    if args.verify_login:
        print("Subscription login verification: PASS")
    if args.verify_image:
        print("Image backend verification: PASS")


if __name__ == "__main__":
    main()
