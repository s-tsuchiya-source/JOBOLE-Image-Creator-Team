from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys

from PIL import Image
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env", override=True)

from scripts.load_project import load_environment, resolve_project_dir
from services.creative_spec import CreativeSpecError, load_creative_spec, write_creative_spec
from services.text_verifier import verify_image_text, write_verification


SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _load_context(project_dir: Path) -> tuple[dict, Path]:
    path = project_dir / "00_request" / "normalized" / "creative-context.json"
    if not path.exists():
        raise SystemExit(
            "creative-context.json がありません。先に prepare_creative_context.py を実行してください。"
        )
    return json.loads(path.read_text(encoding="utf-8-sig")), path


def _resolve_expected_size(context: dict) -> tuple[int, int, str]:
    output_spec = context.get("resolved_output_spec", {})
    width = int(output_spec.get("width") or 1200)
    height = int(output_spec.get("height") or 628)
    source = str(output_spec.get("source") or "phase1_default")
    return width, height, source


def _write_expected_copy(path: Path, spec: dict, *, width: int, height: int) -> None:
    lines = [
        "# Expected Creative Copy",
        "",
        "Codex Integrated Creative DesignerがImageGenで生成した画像を照合するための文字契約です。",
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
            "- generation_owner: codex_integrated_creative_designer",
            "- generation_capability: codex_imagegen",
            f"- size: {width}x{height}",
            f"- benchmark_refs: {', '.join(spec.get('benchmark_refs', [])) or 'none'}",
            "- text_rendering: integrated_by_codex_imagegen_then_verified",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def _canonical_candidate(
    project_dir: Path,
    creative_id: str,
    version: str,
    explicit_candidate: str,
) -> tuple[Path, Path]:
    batch_dir = project_dir / "03_batches" / creative_id / version
    batch_dir.mkdir(parents=True, exist_ok=True)
    canonical = batch_dir / "candidate.png"

    if explicit_candidate.strip():
        source = Path(explicit_candidate).expanduser().resolve()
        if not source.exists():
            raise SystemExit(f"candidate image not found: {source}")
        if source != canonical.resolve():
            shutil.copy2(source, canonical)
    elif not canonical.exists():
        raise SystemExit(
            f"Codex ImageGen candidateがありません: {canonical}\n"
            "Integrated Creative DesignerがImageGenで完成画像を生成し、このパスへ保存してから登録してください。"
        )
    return batch_dir, canonical


def _validate_dimensions(candidate: Path, *, expected_width: int, expected_height: int) -> tuple[int, int]:
    try:
        with Image.open(candidate) as image:
            width, height = image.size
    except Exception as exc:
        raise SystemExit(f"candidate image cannot be opened: {candidate}: {exc}") from exc

    expected_ratio = expected_width / expected_height
    actual_ratio = width / height
    if abs(expected_ratio - actual_ratio) > 0.01:
        raise SystemExit(
            "candidate aspect ratio does not match resolved output spec: "
            f"expected={expected_width}x{expected_height}, actual={width}x{height}"
        )
    return width, height


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Register a candidate created directly by Codex ImageGen. "
            "This script does not generate or redesign the image."
        )
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--creative-id", default="CR001")
    parser.add_argument("--version", default="v001")
    parser.add_argument("--candidate-file", default="")
    parser.add_argument("--spec-file", default="")
    parser.add_argument("--generation-note", default="")
    args = parser.parse_args()

    if not SAFE_ID_RE.match(args.creative_id) or not SAFE_ID_RE.match(args.version):
        raise SystemExit("creative-id/version must use only letters, numbers, hyphen, underscore")

    projects_root = load_environment()
    project_dir = resolve_project_dir(projects_root, args.project_id)
    if not (project_dir / "project.yaml").exists():
        raise SystemExit(f"project is incomplete: {project_dir}")

    context, context_path = _load_context(project_dir)
    expected_width, expected_height, output_spec_source = _resolve_expected_size(context)
    batch_dir, candidate = _canonical_candidate(
        project_dir, args.creative_id, args.version, args.candidate_file
    )
    actual_width, actual_height = _validate_dimensions(
        candidate, expected_width=expected_width, expected_height=expected_height
    )

    if args.spec_file.strip():
        spec_source = Path(args.spec_file).expanduser().resolve()
    else:
        spec_source = project_dir / "02_direction" / f"{args.creative_id}-creative-spec.json"
    if not spec_source.exists():
        raise SystemExit(f"approved creative spec not found: {spec_source}")

    try:
        spec = load_creative_spec(
            spec_source,
            benchmark_max=int(os.getenv("REFERENCE_SHORTLIST_MAX", "3")),
            text_block_max=int(os.getenv("PREMIUM_TEXT_BLOCK_MAX", "6")),
        )
    except CreativeSpecError as exc:
        raise SystemExit(f"Creative Spec validation failed: {exc}") from exc

    snapshot = batch_dir / "creative-spec.json"
    write_creative_spec(snapshot, spec)
    expected_copy = batch_dir / "expected-copy.md"
    _write_expected_copy(expected_copy, spec, width=actual_width, height=actual_height)

    review_dir = project_dir / "04_project_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    verification_path = review_dir / f"{args.creative_id}-{args.version}-text-verification.json"
    report = verify_image_text(spec, candidate)
    report.update(
        {
            "mode": "codex_imagegen",
            "generation_owner": "codex_integrated_creative_designer",
            "generation_capability": "codex_imagegen",
            "candidate": str(candidate),
            "local_ocr_is_advisory": True,
            "claude_visual_readback_required": True,
            "codex_final_visual_check_required": True,
        }
    )
    write_verification(verification_path, report)

    metadata = {
        "project_id": args.project_id,
        "creative_id": args.creative_id,
        "version": args.version,
        "mode": "codex_imagegen",
        "generation_owner": "codex_integrated_creative_designer",
        "generation_capability": "codex_imagegen",
        "api_key_required_for_primary_generation": False,
        "size": f"{actual_width}x{actual_height}",
        "resolved_output_spec": f"{expected_width}x{expected_height}",
        "output_spec_source": output_spec_source,
        "creative_context": str(context_path),
        "source_spec": str(spec_source),
        "candidate": str(candidate),
        "expected_copy": str(expected_copy),
        "verification": str(verification_path),
        "generation_note": args.generation_note,
        "formal_delivery": False,
        "next_gate": "creative_reviewer_then_codex_final_qa",
    }
    (batch_dir / "generation-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8-sig"
    )

    print("CODEX IMAGEGEN CANDIDATE REGISTRATION: PASS")
    for key, value in metadata.items():
        print(f"{key.upper()}={value}")
    print(f"TEXT_VERIFICATION_STATUS={report.get('status')}")
    print("NOTE=This script registered an existing Codex ImageGen candidate; it did not generate the image.")


if __name__ == "__main__":
    main()
