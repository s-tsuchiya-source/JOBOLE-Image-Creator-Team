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
load_dotenv(REPO_ROOT / ".env", override=True)

from services.image_generator import check_image_backend
from services.text_verifier import _pytesseract_available

REQUIRED_AGENTS = ["recruitment_analyst", "creative_director", "creative_reviewer"]
EXPECTED_WORKFLOW = [
    "intake",
    "context_preparation",
    "recruitment_analysis",
    "codex_fact_check",
    "codex_benchmark_gate",
    "creative_direction",
    "codex_creative_spec_approval",
    "creative_spec_save",
    "candidate_generation",
    "local_text_verification_if_available",
    "creative_review_with_visual_text_readback",
    "codex_final_qa",
    "final_approval_file",
    "formal_promotion",
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
    agents = yaml.safe_load((REPO_ROOT / "configs" / "agents.yaml").read_text(encoding="utf-8")) or {}
    workflow = yaml.safe_load((REPO_ROOT / "configs" / "workflow.yaml").read_text(encoding="utf-8")) or {}
    render_modes = yaml.safe_load((REPO_ROOT / "configs" / "render_modes.yaml").read_text(encoding="utf-8")) or {}

    if agents.get("architecture", {}).get("version") != "phase1_premium_integrated_ai_v4":
        errors.append("agents architecture version must be phase1_premium_integrated_ai_v4")

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
    extra = sorted(set(configured_agents) - set(REQUIRED_AGENTS))
    if extra:
        errors.append("Unexpected active Claude specialists: " + ", ".join(extra))

    steps = workflow.get("workflow", {}).get("steps", [])
    positions = {step: index for index, step in enumerate(steps)}
    for step in EXPECTED_WORKFLOW:
        if step not in positions:
            errors.append(f"Workflow missing v4 step: {step}")
    for previous, following in zip(EXPECTED_WORKFLOW, EXPECTED_WORKFLOW[1:]):
        if previous in positions and following in positions and positions[previous] >= positions[following]:
            errors.append(f"Workflow order invalid: {previous} must precede {following}")

    modes = render_modes.get("render_modes", {})
    if "premium_ai" not in modes or "safe_python" not in modes:
        errors.append("render_modes.yaml must define premium_ai and safe_python")
    if not modes.get("premium_ai", {}).get("default"):
        errors.append("premium_ai must be the default render mode")

    required_files = [
        "scripts/create_project_from_intake.py",
        "scripts/prepare_creative_context.py",
        "scripts/generate_creative.py",
        "scripts/verify_generated_text.py",
        "scripts/promote_creative.py",
        "services/creative_spec.py",
        "services/text_verifier.py",
        "services/design_spec.py",
        "services/overlay_renderer.py",
        "configs/render_modes.yaml",
        "configs/media.yaml",
        "configs/layouts.yaml",
        "requirements-ocr.txt",
    ]
    for relative in required_files:
        if not (REPO_ROOT / relative).exists():
            errors.append(f"Missing v4 component: {relative}")

    generate_text = (REPO_ROOT / "scripts" / "generate_creative.py").read_text(encoding="utf-8")
    promote_text = (REPO_ROOT / "scripts" / "promote_creative.py").read_text(encoding="utf-8")
    creative_spec_text = (REPO_ROOT / "services" / "creative_spec.py").read_text(encoding="utf-8")
    verifier_text = (REPO_ROOT / "services" / "text_verifier.py").read_text(encoding="utf-8")
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

    for token in ["premium_ai", "safe_python", "candidate.png", "creative-spec.json", "verify_image_text"]:
        if token not in generate_text:
            errors.append(f"generate_creative.py missing v4 behavior: {token}")
    if "05_delivery" in generate_text:
        errors.append("generate_creative.py must not write directly to 05_delivery in candidate-first v4")
    for token in ["creative_reviewer_pass", "codex_final_qa_pass", "text_integrity_pass", "05_delivery"]:
        if token not in promote_text:
            errors.append(f"promote_creative.py missing approval behavior: {token}")
    if "text_contract" not in creative_spec_text or "build_integrated_image_prompt" not in creative_spec_text:
        errors.append("creative_spec.py must validate exact text contract and build integrated prompt")
    if "run_local_ocr" not in verifier_text or "compare_text_contract" not in verifier_text:
        errors.append("text_verifier.py must support OCR and deterministic text comparison")
    for token in ["CREATIVE_RENDER_MODE=premium_ai", "PREMIUM_IMAGE_BACKEND=openai", "OCR_LANG=jpn+eng"]:
        if token not in env_example:
            errors.append(f".env.example missing v4 configuration: {token}")

    messages.extend(
        [
            "Architecture: VSCode Codex CCO + 3 Claude specialists + Premium integrated image AI",
            "Premium Mode: image AI designs photo + decoration + Japanese typography together",
            "Python role: context / generation / OCR helper / candidate promotion; not primary designer",
            "Safe Mode: deterministic Python typography remains available as fallback",
            "Text verification: optional local OCR + mandatory Claude visual readback + mandatory Codex final check",
            "Candidate-first delivery: generate_creative never writes unreviewed output to 05_delivery",
            "Benchmark library: original_image -> Codex shortlist max 3",
        ]
    )


def _benchmark_root() -> tuple[Path | None, str]:
    configured = os.getenv("ORIGINAL_IMAGE_ROOT", "").strip()
    if configured:
        return Path(configured), "ORIGINAL_IMAGE_ROOT"
    projects_root = os.getenv("PROJECTS_ROOT", "").strip()
    if projects_root:
        return Path(projects_root).parent / "original_image", "derived_from_PROJECTS_ROOT"
    return None, "unresolved"


def validate_runtime_config(errors: list[str], messages: list[str]) -> None:
    root, source = _benchmark_root()
    if root is None:
        errors.append("Benchmark root cannot be resolved")
    elif not root.exists():
        errors.append(f"Benchmark root does not exist: {root} (source={source})")
    else:
        extensions = {".png", ".jpg", ".jpeg", ".webp"}
        count = sum(1 for path in root.rglob("*") if path.is_file() and path.suffix.lower() in extensions)
        messages.append(f"Benchmark library: OK ({root}, images={count}, source={source})")

    mode = os.getenv("CREATIVE_RENDER_MODE", "premium_ai").strip().lower()
    messages.append(f"Render mode: {mode}")
    if mode == "premium_ai":
        backend = os.getenv("PREMIUM_IMAGE_BACKEND", "openai").strip().lower()
        messages.append(f"Premium image backend: {backend}")
        if backend in {"openai", "openai_api"}:
            if not os.getenv("OPENAI_API_KEY", "").strip():
                errors.append("OPENAI_API_KEY is required for Premium Mode with openai backend")
            if not os.getenv("OPENAI_IMAGE_MODEL", "").strip():
                errors.append("OPENAI_IMAGE_MODEL is required for Premium Mode with openai backend")

    ocr_ok, ocr_detail = _pytesseract_available()
    if ocr_ok:
        messages.append(f"Optional local OCR: OK ({ocr_detail}, lang={os.getenv('OCR_LANG', 'jpn+eng')})")
    else:
        messages.append("Optional local OCR: unavailable; Claude/Codex visual verification remains mandatory")

    for label, command in (
        ("Claude Code", os.getenv("CLAUDE_CLI_COMMAND", "claude")),
        ("Codex", os.getenv("CODEX_CLI_COMMAND", "codex")),
    ):
        ok, detail = _run_version(command)
        if ok:
            messages.append(f"{label} CLI: OK ({detail})")
        else:
            errors.append(f"{label} CLI unavailable: {detail}")


def verify_logins(errors: list[str], messages: list[str]) -> None:
    claude_exe = _resolved(os.getenv("CLAUDE_CLI_COMMAND", "claude"))
    codex_exe = _resolved(os.getenv("CODEX_CLI_COMMAND", "codex"))
    if not claude_exe or not codex_exe:
        errors.append("Cannot verify login until Claude Code and Codex CLI are installed")
        return

    claude = subprocess.run(
        _windows_safe(claude_exe, ["-p", "--output-format", "json", "--max-turns", "1", "Return exactly OK."]),
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
            _windows_safe(codex_exe, ["exec", "--ephemeral", "--sandbox", "read-only", "--output-last-message", str(output_path), "-"]),
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


def verify_image_backend(errors: list[str], messages: list[str]) -> None:
    previous = os.environ.get("IMAGE_BACKEND")
    mode = os.getenv("CREATIVE_RENDER_MODE", "premium_ai").strip().lower()
    backend = (
        os.getenv("PREMIUM_IMAGE_BACKEND", "openai")
        if mode == "premium_ai"
        else os.getenv("SAFE_IMAGE_BACKEND", os.getenv("IMAGE_BACKEND", "openvino_ovms"))
    ).strip()
    os.environ["IMAGE_BACKEND"] = backend
    try:
        info = check_image_backend()
        messages.append("Image backend connection/config: OK " + json.dumps(info, ensure_ascii=False))
    except Exception as exc:
        errors.append(f"Image backend check failed: {type(exc).__name__}: {exc}")
    finally:
        if previous is None:
            os.environ.pop("IMAGE_BACKEND", None)
        else:
            os.environ["IMAGE_BACKEND"] = previous


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Premium Integrated AI v4 architecture.")
    parser.add_argument("--runtime-config", action="store_true")
    parser.add_argument("--verify-login", action="store_true")
    parser.add_argument("--verify-image", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    messages: list[str] = []
    validate_structure(errors, messages)

    if args.runtime_config or args.verify_login:
        validate_runtime_config(errors, messages)
    if args.verify_login and not errors:
        verify_logins(errors, messages)
    if args.verify_image and not errors:
        verify_image_backend(errors, messages)

    if errors:
        print("SYSTEM VALIDATION: FAIL")
        for error in errors:
            print(f"[NG] {error}")
        raise SystemExit(2)

    print("SYSTEM VALIDATION: PASS")
    print("Claude specialists: 3")
    print("Codex CCO: VSCode highest authority")
    print("Primary render mode: PREMIUM INTEGRATED AI")
    print("Safe Python typography: FALLBACK ONLY")
    print("Text API keys required: NO")
    for message in messages:
        print(message)
    if args.verify_login:
        print("Subscription login verification: PASS")
    if args.verify_image:
        print("Image backend verification: PASS")


if __name__ == "__main__":
    main()
