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


REQUIRED_CLAUDE_AGENTS = ["recruitment_analyst", "creative_director", "creative_reviewer"]
REQUIRED_CODEX_AGENTS = ["integrated_creative_designer"]
EXPECTED_WORKFLOW = [
    "intake",
    "context_preparation",
    "recruitment_analysis",
    "codex_fact_check",
    "codex_benchmark_gate",
    "creative_direction",
    "codex_creative_spec_approval",
    "creative_spec_save",
    "codex_imagegen_capability_gate",
    "codex_integrated_candidate_generation",
    "codex_designer_self_check",
    "candidate_registration",
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

    if agents.get("architecture", {}).get("version") != "phase1_codex_native_imagegen_v5":
        errors.append("agents architecture version must be phase1_codex_native_imagegen_v5")

    chief = agents.get("chief", {}).get("codex_cco", {})
    cco_path = REPO_ROOT / str(chief.get("file") or "")
    if not chief or not cco_path.exists():
        errors.append("Codex CCO role is missing")

    configured_claude = agents.get("agents", {})
    for name in REQUIRED_CLAUDE_AGENTS:
        config = configured_claude.get(name)
        if not config:
            errors.append(f"Missing active Claude specialist: {name}")
            continue
        role_path = REPO_ROOT / str(config.get("file") or "")
        if not role_path.exists():
            errors.append(f"Missing Claude role file: {role_path}")
    extra_claude = sorted(set(configured_claude) - set(REQUIRED_CLAUDE_AGENTS))
    if extra_claude:
        errors.append("Unexpected active Claude specialists: " + ", ".join(extra_claude))

    configured_codex = agents.get("codex_agents", {})
    for name in REQUIRED_CODEX_AGENTS:
        config = configured_codex.get(name)
        if not config:
            errors.append(f"Missing active Codex production agent: {name}")
            continue
        role_path = REPO_ROOT / str(config.get("file") or "")
        skill_path = REPO_ROOT / str(config.get("skill") or "")
        if not role_path.exists():
            errors.append(f"Missing Codex role file: {role_path}")
        if not skill_path.exists():
            errors.append(f"Missing Codex ImageGen skill file: {skill_path}")
        if config.get("generation_capability") != "codex_imagegen":
            errors.append("Integrated Creative Designer must use codex_imagegen capability")

    steps = workflow.get("workflow", {}).get("steps", [])
    positions = {step: index for index, step in enumerate(steps)}
    for step in EXPECTED_WORKFLOW:
        if step not in positions:
            errors.append(f"Workflow missing v5 step: {step}")
    for previous, following in zip(EXPECTED_WORKFLOW, EXPECTED_WORKFLOW[1:]):
        if previous in positions and following in positions and positions[previous] >= positions[following]:
            errors.append(f"Workflow order invalid: {previous} must precede {following}")

    modes = render_modes.get("render_modes", {})
    for mode in ["codex_imagegen", "safe_python", "api_fallback"]:
        if mode not in modes:
            errors.append(f"render_modes.yaml missing {mode}")
    if not modes.get("codex_imagegen", {}).get("default"):
        errors.append("codex_imagegen must be the default render mode")
    if modes.get("codex_imagegen", {}).get("python_generates_image") is not False:
        errors.append("Python must not generate the primary Codex ImageGen candidate")
    if modes.get("codex_imagegen", {}).get("openai_api_key_required") is not False:
        errors.append("Primary Codex ImageGen route must not require OPENAI_API_KEY")
    if modes.get("codex_imagegen", {}).get("silent_api_fallback_allowed") is not False:
        errors.append("Silent API fallback must be disabled")

    required_files = [
        ".codex/agents/integrated-creative-designer.md",
        ".codex/skills/recruitment-imagegen/SKILL.md",
        "scripts/create_project_from_intake.py",
        "scripts/prepare_creative_context.py",
        "scripts/register_codex_candidate.py",
        "scripts/generate_creative.py",
        "scripts/verify_generated_text.py",
        "scripts/promote_creative.py",
        "scripts/test_codex_imagegen_contract.py",
        "services/creative_spec.py",
        "services/text_verifier.py",
        "services/design_spec.py",
        "services/overlay_renderer.py",
        "configs/render_modes.yaml",
        "configs/media.yaml",
        "configs/layouts.yaml",
    ]
    for relative in required_files:
        if not (REPO_ROOT / relative).exists():
            errors.append(f"Missing v5 component: {relative}")

    generate_text = (REPO_ROOT / "scripts" / "generate_creative.py").read_text(encoding="utf-8")
    register_text = (REPO_ROOT / "scripts" / "register_codex_candidate.py").read_text(encoding="utf-8")
    creative_spec_text = (REPO_ROOT / "services" / "creative_spec.py").read_text(encoding="utf-8")
    verifier_text = (REPO_ROOT / "services" / "text_verifier.py").read_text(encoding="utf-8")
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    skill_text = (REPO_ROOT / ".codex" / "skills" / "recruitment-imagegen" / "SKILL.md").read_text(encoding="utf-8")

    if "v5 primary generation is owned by Codex Integrated Creative Designer" not in generate_text:
        errors.append("generate_creative.py must reject primary codex_imagegen generation")
    if "API fallback is disabled" not in generate_text:
        errors.append("generate_creative.py must require explicit API fallback enablement")
    if "05_delivery" in generate_text:
        errors.append("fallback generator must not write directly to 05_delivery")
    for token in [
        "CODEX IMAGEGEN CANDIDATE REGISTRATION: PASS",
        '"generation_capability": "codex_imagegen"',
        '"api_key_required_for_primary_generation": False',
    ]:
        if token not in register_text:
            errors.append(f"register_codex_candidate.py missing behavior: {token}")
    if "codex_integrated" not in creative_spec_text or "codex_imagegen" not in creative_spec_text:
        errors.append("creative_spec.py must target Codex ImageGen execution")
    if "run_local_ocr" not in verifier_text or "compare_text_contract" not in verifier_text:
        errors.append("text_verifier.py must support OCR and deterministic text comparison")
    for token in [
        "CREATIVE_RENDER_MODE=codex_imagegen",
        "CODEX_IMAGEGEN_REQUIRED=true",
        "SILENT_API_FALLBACK_ALLOWED=false",
        "API_FALLBACK_ENABLED=false",
    ]:
        if token not in env_example:
            errors.append(f".env.example missing v5 configuration: {token}")
    if "IMAGEGEN_CAPABILITY_UNAVAILABLE" not in skill_text:
        errors.append("ImageGen skill must block rather than silently fall back to API")

    messages.extend(
        [
            "Architecture: Codex CCO + Codex Integrated Creative Designer + 3 Claude specialists",
            "Primary render mode: CODEX NATIVE IMAGEGEN",
            "Primary image owner: Codex Integrated Creative Designer",
            "Primary API key requirement: NO",
            "Python role: project/context/candidate registration/OCR/promotion; not primary image generator",
            "Safe Python typography: FALLBACK ONLY",
            "Direct OpenAI API: EXPLICIT USER-APPROVED FALLBACK ONLY",
            "Text verification: Designer self-check + optional OCR + Claude visual readback + Codex final check",
            "Candidate-first delivery: unreviewed images never go directly to 05_delivery",
            "Benchmark library: original_image -> Codex CCO shortlist max 3",
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

    mode = os.getenv("CREATIVE_RENDER_MODE", "codex_imagegen").strip().lower()
    messages.append(f"Render mode: {mode}")
    if mode == "codex_imagegen":
        if os.getenv("SILENT_API_FALLBACK_ALLOWED", "false").strip().lower() != "false":
            errors.append("SILENT_API_FALLBACK_ALLOWED must be false")
        messages.append("Codex ImageGen capability: runtime gate is performed by Codex CCO at production time")
        messages.append("OPENAI_API_KEY: not required for primary project route")
    elif mode == "api_fallback":
        if os.getenv("API_FALLBACK_ENABLED", "false").strip().lower() != "true":
            errors.append("api_fallback selected but API_FALLBACK_ENABLED is not true")
        if not os.getenv("OPENAI_API_KEY", "").strip():
            errors.append("OPENAI_API_KEY required only for selected api_fallback mode")
    elif mode != "safe_python":
        errors.append(f"unsupported CREATIVE_RENDER_MODE={mode!r}")

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


def verify_fallback_backend(errors: list[str], messages: list[str]) -> None:
    mode = os.getenv("CREATIVE_RENDER_MODE", "codex_imagegen").strip().lower()
    if mode == "codex_imagegen":
        messages.append(
            "Image backend verification: skipped for primary Codex ImageGen; capability is checked inside the Codex runtime"
        )
        return

    previous = os.environ.get("IMAGE_BACKEND")
    backend = (
        os.getenv("API_FALLBACK_IMAGE_BACKEND", "openai")
        if mode == "api_fallback"
        else os.getenv("SAFE_IMAGE_BACKEND", "openvino_ovms")
    ).strip()
    os.environ["IMAGE_BACKEND"] = backend
    try:
        info = check_image_backend()
        messages.append("Fallback image backend connection/config: OK " + json.dumps(info, ensure_ascii=False))
    except Exception as exc:
        errors.append(f"Fallback image backend check failed: {type(exc).__name__}: {exc}")
    finally:
        if previous is None:
            os.environ.pop("IMAGE_BACKEND", None)
        else:
            os.environ["IMAGE_BACKEND"] = previous


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Codex Native ImageGen v5 architecture.")
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
        verify_fallback_backend(errors, messages)

    if errors:
        print("SYSTEM VALIDATION: FAIL")
        for error in errors:
            print(f"[NG] {error}")
        raise SystemExit(2)

    print("SYSTEM VALIDATION: PASS")
    print("Claude specialists: 3")
    print("Codex CCO: VSCode highest authority")
    print("Codex production agents: 1 (Integrated Creative Designer)")
    print("Primary render mode: CODEX NATIVE IMAGEGEN")
    print("Primary API key required: NO")
    print("Safe Python typography: FALLBACK ONLY")
    for message in messages:
        print(message)
    if args.verify_login:
        print("Subscription login verification: PASS")
    if args.verify_image:
        print("Configured image route verification: PASS")


if __name__ == "__main__":
    main()
