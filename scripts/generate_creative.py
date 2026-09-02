from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import sys

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env", override=True)

from scripts.load_project import load_environment, resolve_project_dir
from services.creative_spec import (
    CreativeSpecError,
    build_integrated_image_prompt,
    load_creative_spec,
    write_creative_spec,
)
from services.design_spec import DesignSpecError, load_design_spec, write_design_spec
from services.image_generator import create_image_generator
from services.overlay_renderer import render_design_spec
from services.text_verifier import verify_image_text, write_verification


SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
ALLOWED_MODES = {"codex_imagegen", "safe_python", "api_fallback"}


def _load_context(project_dir: Path) -> tuple[dict, Path]:
    path = project_dir / "00_request" / "normalized" / "creative-context.json"
    if not path.exists():
        raise SystemExit("creative-context.json がありません。先に prepare_creative_context.py を実行してください。")
    return json.loads(path.read_text(encoding="utf-8-sig")), path


def _resolve_size(args: argparse.Namespace, context: dict) -> tuple[int, int, str]:
    spec = context.get("resolved_output_spec", {})
    context_width = int(spec.get("width") or 1200)
    context_height = int(spec.get("height") or 628)
    source = str(spec.get("source") or "phase1_default")
    if bool(args.width) != bool(args.height):
        raise SystemExit("--width / --height は両方指定するか、両方省略してください。")
    width = int(args.width or context_width)
    height = int(args.height or context_height)
    if width < 256 or height < 256:
        raise SystemExit("width/height must both be at least 256 pixels")
    if spec.get("enforce_aspect_ratio"):
        expected_ratio = context_width / context_height
        actual_ratio = width / height
        if abs(expected_ratio - actual_ratio) > 0.01:
            raise SystemExit(
                "ヒアリング指定の媒体比率と生成サイズが一致しません: "
                f"expected={context_width}x{context_height}, requested={width}x{height}"
            )
    return width, height, source


def _resolve_mode(explicit: str) -> str:
    mode = (explicit or os.getenv("CREATIVE_RENDER_MODE", "codex_imagegen")).strip().lower()
    if mode not in ALLOWED_MODES:
        raise SystemExit(f"unsupported mode={mode!r}; use codex_imagegen, safe_python, or api_fallback")
    return mode


def _write_expected_copy_premium(path: Path, spec: dict, *, width: int, height: int) -> None:
    lines = ["# Expected Creative Copy", "", "Direct API fallback candidate text contract.", ""]
    for block in spec["text_contract"]:
        lines.extend(
            [
                f"## {block['id']} / {block['role']}",
                block["text"],
                f"- required: {str(block.get('required', True)).lower()}",
                f"- fact_ids: {', '.join(block.get('fact_ids', [])) or 'none'}",
                "",
            ]
        )
    lines.extend(["## Technical", "- mode: api_fallback", f"- size: {width}x{height}", ""])
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def _write_expected_copy_safe(path: Path, spec: dict, *, width: int, height: int) -> None:
    lines = ["# Expected Creative Copy", "", "- mode: safe_python", f"- size: {width}x{height}", ""]
    lines.extend(["## Headline", spec["headline"]["text"], ""])
    if spec["subcopy"]["text"]:
        lines.extend(["## Subcopy", spec["subcopy"]["text"], ""])
    if spec["facts"]:
        lines.append("## Facts")
        lines.extend([f"- {fact}" for fact in spec["facts"]])
        lines.append("")
    if spec["cta"]["text"]:
        lines.extend(["## CTA", spec["cta"]["text"], ""])
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def _generator_for_backend(backend: str):
    previous = os.environ.get("IMAGE_BACKEND")
    os.environ["IMAGE_BACKEND"] = backend
    try:
        return create_image_generator()
    finally:
        if previous is None:
            os.environ.pop("IMAGE_BACKEND", None)
        else:
            os.environ["IMAGE_BACKEND"] = previous


def _run_api_fallback(
    *, project_dir: Path, creative_id: str, version: str, spec_file: str,
    width: int, height: int, context_path: Path, output_spec_source: str,
) -> dict:
    if os.getenv("API_FALLBACK_ENABLED", "false").strip().lower() != "true":
        raise SystemExit(
            "API fallback is disabled. v5 standard generation is Codex ImageGen. "
            "Enable API_FALLBACK_ENABLED=true only after explicit user approval."
        )
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise SystemExit("OPENAI_API_KEY is required only for explicit api_fallback mode")
    if not os.getenv("OPENAI_IMAGE_MODEL", "").strip():
        raise SystemExit("OPENAI_IMAGE_MODEL is required only for explicit api_fallback mode")

    source = Path(spec_file).expanduser().resolve() if spec_file.strip() else (
        project_dir / "02_direction" / f"{creative_id}-creative-spec.json"
    )
    try:
        spec = load_creative_spec(
            source,
            benchmark_max=int(os.getenv("REFERENCE_SHORTLIST_MAX", "3")),
            text_block_max=int(os.getenv("PREMIUM_TEXT_BLOCK_MAX", "6")),
        )
    except CreativeSpecError as exc:
        raise SystemExit(f"Creative Spec validation failed: {exc}") from exc

    batch_dir = project_dir / "03_batches" / creative_id / version
    review_dir = project_dir / "04_project_review"
    batch_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    candidate = batch_dir / "candidate.png"
    prompt_path = batch_dir / "image-prompt.txt"
    expected_copy = batch_dir / "expected-copy.md"
    snapshot = batch_dir / "creative-spec.json"
    write_creative_spec(snapshot, spec)

    prompt = build_integrated_image_prompt(spec, width=width, height=height)
    prompt_path.write_text(
        "# EXPLICIT API FALLBACK\n\n" + prompt + "\n\n"
        + f"creative_context: {context_path}\noutput_spec_source: {output_spec_source}\n",
        encoding="utf-8-sig",
    )
    backend = os.getenv("API_FALLBACK_IMAGE_BACKEND", "openai").strip()
    generator = _generator_for_backend(backend)
    generator.generate(
        prompt=prompt,
        negative_prompt=spec["image"].get("negative_prompt", ""),
        width=width,
        height=height,
        output_path=candidate,
    )
    _write_expected_copy_premium(expected_copy, spec, width=width, height=height)
    report = verify_image_text(spec, candidate)
    report.update({"mode": "api_fallback", "backend": backend, "candidate": str(candidate)})
    verification = review_dir / f"{creative_id}-{version}-text-verification.json"
    write_verification(verification, report)
    return {
        "mode": "api_fallback",
        "backend": backend,
        "candidate": str(candidate),
        "verification": str(verification),
        "formal_delivery": False,
    }


def _run_safe(
    *, project_dir: Path, creative_id: str, version: str, spec_file: str,
    width: int, height: int,
) -> dict:
    source = Path(spec_file).expanduser().resolve() if spec_file.strip() else (
        project_dir / "02_direction" / f"{creative_id}-design-spec.json"
    )
    try:
        spec = load_design_spec(source, fact_max=int(os.getenv("FACT_CHIP_MAX", "3")))
    except DesignSpecError as exc:
        raise SystemExit(f"Design Spec validation failed: {exc}") from exc

    batch_dir = project_dir / "03_batches" / creative_id / version
    review_dir = project_dir / "04_project_review"
    batch_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    candidate = batch_dir / "candidate.png"
    background = batch_dir / "background.png"
    expected_copy = batch_dir / "expected-copy.md"
    snapshot = batch_dir / "design-spec.json"
    write_design_spec(snapshot, spec)

    prompt = spec["image"]["prompt"].strip() + "\nDo not render readable text."
    backend = os.getenv("SAFE_IMAGE_BACKEND", "openvino_ovms").strip()
    generator = _generator_for_backend(backend)
    generator.generate(
        prompt=prompt,
        negative_prompt="text, letters, words, watermark",
        width=width,
        height=height,
        output_path=background,
    )
    render_design_spec(background, spec, output_path=candidate)
    _write_expected_copy_safe(expected_copy, spec, width=width, height=height)
    report = {
        "status": "pass",
        "verification_source": "deterministic_python_rendering",
        "mode": "safe_python",
        "required_text_pass": True,
        "numeric_fact_pass": True,
    }
    verification = review_dir / f"{creative_id}-{version}-text-verification.json"
    write_verification(verification, report)
    return {
        "mode": "safe_python",
        "backend": backend,
        "candidate": str(candidate),
        "verification": str(verification),
        "formal_delivery": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "v5 fallback generation utility. Standard codex_imagegen production is performed directly by "
            "Codex Integrated Creative Designer, then registered with register_codex_candidate.py."
        )
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--creative-id", default="CR001")
    parser.add_argument("--version", default="v001")
    parser.add_argument("--mode", default="")
    parser.add_argument("--spec-file", default="")
    parser.add_argument("--width", type=int, default=0)
    parser.add_argument("--height", type=int, default=0)
    args = parser.parse_args()

    if not SAFE_ID_RE.match(args.creative_id) or not SAFE_ID_RE.match(args.version):
        raise SystemExit("creative-id/version must use only letters, numbers, hyphen, underscore")

    mode = _resolve_mode(args.mode)
    if mode == "codex_imagegen":
        raise SystemExit(
            "v5 primary generation is owned by Codex Integrated Creative Designer + ImageGen, not Python.\n"
            "Generate candidate.png with Codex ImageGen, then run:\n"
            "python scripts/register_codex_candidate.py --project-id <PJ-XXXX> --creative-id <CR001> --version <v001>"
        )

    projects_root = load_environment()
    project_dir = resolve_project_dir(projects_root, args.project_id)
    if not (project_dir / "project.yaml").exists():
        raise SystemExit(f"project is incomplete: {project_dir}")
    context, context_path = _load_context(project_dir)
    width, height, output_spec_source = _resolve_size(args, context)

    if mode == "api_fallback":
        result = _run_api_fallback(
            project_dir=project_dir,
            creative_id=args.creative_id,
            version=args.version,
            spec_file=args.spec_file,
            width=width,
            height=height,
            context_path=context_path,
            output_spec_source=output_spec_source,
        )
    else:
        result = _run_safe(
            project_dir=project_dir,
            creative_id=args.creative_id,
            version=args.version,
            spec_file=args.spec_file,
            width=width,
            height=height,
        )

    batch_dir = project_dir / "03_batches" / args.creative_id / args.version
    metadata = {
        "project_id": args.project_id,
        "creative_id": args.creative_id,
        "version": args.version,
        **result,
        "next_gate": "creative_reviewer_then_codex_final_qa",
    }
    (batch_dir / "generation-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8-sig"
    )
    print("FALLBACK CREATIVE CANDIDATE GENERATION: PASS")
    for key, value in metadata.items():
        print(f"{key.upper()}={value}")
    print("NOTE=Standard v5 generation remains Codex ImageGen; this command used an explicit fallback mode.")


if __name__ == "__main__":
    main()
