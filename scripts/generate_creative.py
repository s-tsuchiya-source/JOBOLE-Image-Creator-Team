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
ALLOWED_MODES = {"premium_ai", "safe_python"}


def _load_creative_context(project_dir: Path) -> tuple[dict, Path]:
    path = project_dir / "00_request" / "normalized" / "creative-context.json"
    if not path.exists():
        raise SystemExit(
            "creative-context.json がありません。先に "
            "python scripts/prepare_creative_context.py --project-id <PJ-XXXX> を実行してください。"
        )
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
                f"expected={spec.get('aspect_ratio')} resolved={context_width}x{context_height}, "
                f"requested={width}x{height}"
            )
    return width, height, source


def _resolve_mode(explicit: str) -> str:
    mode = (explicit or os.getenv("CREATIVE_RENDER_MODE", "premium_ai")).strip().lower()
    if mode not in ALLOWED_MODES:
        raise SystemExit(f"unsupported mode={mode!r}; use premium_ai or safe_python")
    return mode


def _resolve_source(project_dir: Path, creative_id: str, explicit: str, *, mode: str) -> Path:
    if explicit.strip():
        path = Path(explicit).expanduser().resolve()
    elif mode == "premium_ai":
        path = project_dir / "02_direction" / f"{creative_id}-creative-spec.json"
    else:
        path = project_dir / "02_direction" / f"{creative_id}-design-spec.json"
    if not path.exists():
        raise SystemExit(f"approved spec not found: {path}")
    return path


def _generator_for_mode(mode: str):
    previous = os.environ.get("IMAGE_BACKEND")
    backend = (
        os.getenv("PREMIUM_IMAGE_BACKEND", "openai")
        if mode == "premium_ai"
        else os.getenv("SAFE_IMAGE_BACKEND", os.getenv("IMAGE_BACKEND", "openvino_ovms"))
    ).strip()
    os.environ["IMAGE_BACKEND"] = backend
    try:
        generator = create_image_generator()
    finally:
        if previous is None:
            os.environ.pop("IMAGE_BACKEND", None)
        else:
            os.environ["IMAGE_BACKEND"] = previous
    return generator, backend


def _write_expected_copy_premium(path: Path, spec: dict, *, mode: str, width: int, height: int) -> None:
    lines = [
        "# Expected Creative Copy",
        "",
        "このファイルはPremium AI画像に入るべき正確な文字列の契約です。",
        "画像AIの出力文字を正しいものとみなさず、Reviewer/Codexがこの契約と照合します。",
        "",
    ]
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
    lines.extend(
        [
            "## Technical",
            f"- mode: {mode}",
            f"- size: {width}x{height}",
            f"- benchmark_refs: {', '.join(spec.get('benchmark_refs', [])) or 'none'}",
            "- text_rendering: integrated_by_image_ai_then_verified",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def _write_expected_copy_safe(path: Path, spec: dict, *, mode: str, width: int, height: int) -> None:
    lines = ["# Expected Creative Copy", "", f"- mode: {mode}", f"- size: {width}x{height}", ""]
    lines.extend(["## Headline", spec["headline"]["text"], ""])
    if spec["subcopy"]["text"]:
        lines.extend(["## Subcopy", spec["subcopy"]["text"], ""])
    if spec["facts"]:
        lines.append("## Facts")
        lines.extend([f"- {fact}" for fact in spec["facts"]])
        lines.append("")
    if spec["cta"]["text"]:
        lines.extend(["## CTA", spec["cta"]["text"], ""])
    lines.append("- text_rendering: deterministic_python_design_spec")
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def _generate_premium(
    *,
    project_dir: Path,
    source: Path,
    batch_dir: Path,
    candidate: Path,
    prompt_path: Path,
    expected_copy: Path,
    width: int,
    height: int,
    context_path: Path,
    output_spec_source: str,
) -> tuple[str, dict, dict]:
    try:
        spec = load_creative_spec(
            source,
            benchmark_max=int(os.getenv("REFERENCE_SHORTLIST_MAX", "3")),
            text_block_max=int(os.getenv("PREMIUM_TEXT_BLOCK_MAX", "6")),
        )
    except CreativeSpecError as exc:
        raise SystemExit(f"Creative Spec validation failed: {exc}") from exc

    snapshot = batch_dir / "creative-spec.json"
    write_creative_spec(snapshot, spec)
    prompt = build_integrated_image_prompt(spec, width=width, height=height)
    negative_prompt = spec["image"].get("negative_prompt", "")
    prompt_path.write_text(
        "# Premium Integrated Image Prompt\n\n"
        + prompt
        + "\n\n# Context\n\n"
        + f"creative_context: {context_path}\n"
        + f"creative_spec: {snapshot}\n"
        + f"resolved_size: {width}x{height}\n"
        + f"output_spec_source: {output_spec_source}\n",
        encoding="utf-8-sig",
    )

    generator, backend = _generator_for_mode("premium_ai")
    generator.generate(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        output_path=candidate,
    )
    _write_expected_copy_premium(expected_copy, spec, mode="premium_ai", width=width, height=height)

    report = verify_image_text(spec, candidate)
    report.update({"mode": "premium_ai", "backend": backend, "candidate": str(candidate)})
    return backend, spec, report


def _generate_safe(
    *,
    source: Path,
    batch_dir: Path,
    candidate: Path,
    prompt_path: Path,
    expected_copy: Path,
    width: int,
    height: int,
    context_path: Path,
    output_spec_source: str,
) -> tuple[str, dict, dict]:
    try:
        spec = load_design_spec(source, fact_max=int(os.getenv("FACT_CHIP_MAX", "3")))
    except DesignSpecError as exc:
        raise SystemExit(f"Design Spec validation failed: {exc}") from exc

    snapshot = batch_dir / "design-spec.json"
    write_design_spec(snapshot, spec)
    background = batch_dir / "background.png"
    prompt = (
        spec["image"]["prompt"].strip()
        + "\n\nDo not render any letters, words, captions, logos, watermarks, numbers, or readable text. "
        + f"Keep typography-safe space on the {spec['text_zone']} side."
    )
    negative = spec["image"].get("negative_prompt", "").strip()
    negative = f"{negative}, text, letters, words, watermark" if negative else "text, letters, words, watermark"
    prompt_path.write_text(
        "# Safe Background Prompt\n\n"
        + prompt
        + "\n\n# Context\n\n"
        + f"creative_context: {context_path}\n"
        + f"design_spec: {snapshot}\n"
        + f"resolved_size: {width}x{height}\n"
        + f"output_spec_source: {output_spec_source}\n",
        encoding="utf-8-sig",
    )

    generator, backend = _generator_for_mode("safe_python")
    generator.generate(prompt=prompt, negative_prompt=negative, width=width, height=height, output_path=background)
    render_design_spec(background, spec, output_path=candidate)
    _write_expected_copy_safe(expected_copy, spec, mode="safe_python", width=width, height=height)
    report = {
        "status": "pass",
        "verification_source": "deterministic_python_rendering",
        "mode": "safe_python",
        "backend": backend,
        "candidate": str(candidate),
        "required_text_pass": True,
        "numeric_fact_pass": True,
    }
    return backend, spec, report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a review candidate. Premium AI is default; formal delivery requires later promotion after QA."
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
    projects_root = load_environment()
    project_dir = resolve_project_dir(projects_root, args.project_id)
    if not (project_dir / "project.yaml").exists():
        raise SystemExit(f"project is incomplete: {project_dir}")

    context, context_path = _load_creative_context(project_dir)
    width, height, output_spec_source = _resolve_size(args, context)
    source = _resolve_source(project_dir, args.creative_id, args.spec_file, mode=mode)

    batch_dir = project_dir / "03_batches" / args.creative_id / args.version
    review_dir = project_dir / "04_project_review"
    batch_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    candidate = batch_dir / "candidate.png"
    prompt_path = batch_dir / "image-prompt.txt"
    expected_copy = batch_dir / "expected-copy.md"
    verification_path = review_dir / f"{args.creative_id}-{args.version}-text-verification.json"

    if mode == "premium_ai":
        backend, _spec, report = _generate_premium(
            project_dir=project_dir,
            source=source,
            batch_dir=batch_dir,
            candidate=candidate,
            prompt_path=prompt_path,
            expected_copy=expected_copy,
            width=width,
            height=height,
            context_path=context_path,
            output_spec_source=output_spec_source,
        )
    else:
        backend, _spec, report = _generate_safe(
            source=source,
            batch_dir=batch_dir,
            candidate=candidate,
            prompt_path=prompt_path,
            expected_copy=expected_copy,
            width=width,
            height=height,
            context_path=context_path,
            output_spec_source=output_spec_source,
        )

    write_verification(verification_path, report)
    metadata = {
        "project_id": args.project_id,
        "creative_id": args.creative_id,
        "version": args.version,
        "mode": mode,
        "backend": backend,
        "size": f"{width}x{height}",
        "source_spec": str(source),
        "candidate": str(candidate),
        "expected_copy": str(expected_copy),
        "verification": str(verification_path),
        "formal_delivery": False,
        "next_gate": "creative_reviewer_then_codex_final_qa",
    }
    (batch_dir / "generation-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8-sig"
    )

    print("CREATIVE CANDIDATE GENERATION: PASS")
    for key, value in metadata.items():
        print(f"{key.upper()}={value}")
    print(f"TEXT_VERIFICATION_STATUS={report.get('status')}")
    print("NOTE=Candidate is NOT formal delivery until promote_creative.py receives explicit QA approval.")


if __name__ == "__main__":
    main()
