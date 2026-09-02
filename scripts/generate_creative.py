from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import shutil
import sys

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
load_dotenv(REPO_ROOT / ".env", override=True)

from load_project import load_environment, resolve_project_dir
from services.design_spec import DesignSpecError, load_design_spec, write_design_spec
from services.image_generator import create_image_generator
from services.overlay_renderer import render_design_spec


SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _write_copy_markdown(
    path: Path,
    *,
    spec: dict,
    width: int,
    height: int,
    provider: str,
    output_spec_source: str,
    design_spec_path: Path,
) -> None:
    headline = spec["headline"]["text"]
    subcopy = spec["subcopy"]["text"]
    facts = spec["facts"]
    cta = spec["cta"]["text"]
    lines = [
        "# Creative Copy",
        "",
        "このファイルは完成画像へ実際に後載せした元文言を保持します。",
        "Headlineの改行はCreative DirectorがDesign Specで意味単位に指定したものです。",
        "",
        "## Headline",
        headline,
        "",
    ]
    if subcopy:
        lines.extend(["## Subcopy", subcopy, ""])
    if facts:
        lines.append("## Fact Text")
        for fact in facts:
            lines.append(f"- {fact}")
        lines.append("")
    if cta:
        lines.extend(["## CTA", cta, ""])
    lines.extend(
        [
            "## Design",
            f"- layout_family: {spec['layout_family']}",
            f"- text_zone: {spec['text_zone']}",
            f"- accent_color: {spec['accent_color']}",
            f"- emphasis: {', '.join(spec['headline'].get('emphasis', [])) or 'none'}",
            f"- benchmark_refs: {', '.join(spec.get('benchmark_refs', [])) or 'none'}",
            "",
            "## Technical",
            f"- size: {width}x{height}",
            f"- output_spec_source: {output_spec_source}",
            f"- image_provider: {provider}",
            f"- design_spec: {design_spec_path}",
            "- required_text_rendering: deterministic_python_design_spec",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def _safe_output_name(value: str, creative_id: str) -> str:
    name = value.strip() or f"{creative_id}.png"
    if Path(name).name != name:
        raise SystemExit("--output-name にはファイル名だけを指定してください。パスは指定できません。")
    if Path(name).suffix.lower() != ".png":
        name = Path(name).stem + ".png"
    return name


def _load_creative_context(project_dir: Path) -> tuple[dict, Path]:
    context_path = project_dir / "00_request" / "normalized" / "creative-context.json"
    if not context_path.exists():
        raise SystemExit(
            "creative-context.json がありません。画像生成前に必ず "
            "python scripts/prepare_creative_context.py --project-id <PJ-XXXX> を実行してください。"
        )
    data = json.loads(context_path.read_text(encoding="utf-8-sig"))
    return data, context_path


def _resolve_size(args: argparse.Namespace, context: dict) -> tuple[int, int, str]:
    output_spec = context.get("resolved_output_spec", {})
    context_width = int(output_spec.get("width") or 1200)
    context_height = int(output_spec.get("height") or 628)
    source = str(output_spec.get("source") or "phase1_default")

    if bool(args.width) != bool(args.height):
        raise SystemExit("--width / --height は両方指定するか、両方省略してください。")

    width = int(args.width or context_width)
    height = int(args.height or context_height)
    if width < 256 or height < 256:
        raise SystemExit("width/height must both be at least 256 pixels")

    if output_spec.get("enforce_aspect_ratio"):
        expected_ratio = context_width / context_height
        actual_ratio = width / height
        if abs(expected_ratio - actual_ratio) > 0.01:
            raise SystemExit(
                "ヒアリングで指定された媒体比率と生成サイズが一致しません: "
                f"expected={output_spec.get('aspect_ratio')} resolved={context_width}x{context_height}, "
                f"requested={width}x{height}"
            )
    return width, height, source


def _resolve_design_spec_path(project_dir: Path, creative_id: str, explicit: str) -> Path:
    if explicit.strip():
        path = Path(explicit).expanduser().resolve()
    else:
        path = project_dir / "02_direction" / f"{creative_id}-design-spec.json"
    if not path.exists():
        raise SystemExit(
            f"Design Specがありません: {path}\n"
            "Creative DirectorのDirection Approval後に、02_directionへDesign Spec JSONを保存してください。"
        )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate one project-scoped recruitment creative from an approved AI Design Spec. "
            "The image model creates text-free visual material; Python renders exact Japanese typography."
        )
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--creative-id", default="CR001")
    parser.add_argument("--design-spec-file", default="")
    parser.add_argument("--output-name", default="")
    parser.add_argument("--width", type=int, default=0)
    parser.add_argument("--height", type=int, default=0)
    args = parser.parse_args()

    if not SAFE_ID_RE.match(args.creative_id):
        raise SystemExit("--creative-id は英数字・ハイフン・アンダースコアのみ使用できます。")

    projects_root = load_environment()
    project_dir = resolve_project_dir(projects_root, args.project_id)
    project_yaml = project_dir / "project.yaml"
    if not project_yaml.exists():
        raise SystemExit(
            f"案件フォルダが不完全です: {project_dir}\n"
            "画像生成より先に create_project_from_intake.py で案件を作成してください。"
        )

    context, context_path = _load_creative_context(project_dir)
    width, height, output_spec_source = _resolve_size(args, context)
    fact_max = int(os.getenv("FACT_CHIP_MAX", "3"))
    design_spec_source = _resolve_design_spec_path(project_dir, args.creative_id, args.design_spec_file)
    try:
        spec = load_design_spec(design_spec_source, fact_max=fact_max)
    except DesignSpecError as exc:
        raise SystemExit(f"Design Spec validation failed: {exc}") from exc

    delivery_dir = project_dir / "05_delivery"
    batch_dir = project_dir / "03_batches" / args.creative_id / "v001"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    batch_dir.mkdir(parents=True, exist_ok=True)

    output_name = _safe_output_name(args.output_name, args.creative_id)
    output = delivery_dir / output_name
    copy_path = output.with_name(output.stem + "-copy.md")
    background = batch_dir / "background.png"
    prompt_path = batch_dir / "image-prompt.txt"
    design_spec_copy = batch_dir / "design-spec.json"
    write_design_spec(design_spec_copy, spec)

    generator = create_image_generator()
    provider = getattr(generator, "provider_name", type(generator).__name__)

    background_prompt = (
        spec["image"]["prompt"].strip()
        + "\n\nDo not render any letters, words, captions, logos, watermarks, numbers, or readable text. "
        + f"Keep the approved typography-safe area on the {spec['text_zone']} side. "
        + "The composition must remain visually complete after exact Japanese typography is added later."
    )
    negative_prompt = spec["image"].get("negative_prompt", "").strip()
    required_negative = "text, letters, words, captions, watermark, fake logo"
    negative_prompt = f"{negative_prompt}, {required_negative}" if negative_prompt else required_negative

    prompt_path.write_text(
        "# Image Prompt\n\n"
        + background_prompt
        + "\n\n# Negative Prompt\n\n"
        + negative_prompt
        + "\n\n# Context\n\n"
        + f"creative_context: {context_path}\n"
        + f"design_spec: {design_spec_copy}\n"
        + f"layout_family: {spec['layout_family']}\n"
        + f"resolved_size: {width}x{height}\n"
        + f"output_spec_source: {output_spec_source}\n",
        encoding="utf-8-sig",
    )

    generator.generate(
        prompt=background_prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        output_path=background,
    )
    render_design_spec(background, spec, output_path=output)

    _write_copy_markdown(
        copy_path,
        spec=spec,
        width=width,
        height=height,
        provider=provider,
        output_spec_source=output_spec_source,
        design_spec_path=design_spec_copy,
    )

    print("CREATIVE GENERATION: PASS")
    print(f"PROJECT_ID={args.project_id}")
    print(f"PROJECT_DIR={project_dir}")
    print(f"BACKEND={provider}")
    print(f"SIZE={width}x{height}")
    print(f"OUTPUT_SPEC_SOURCE={output_spec_source}")
    print(f"LAYOUT_FAMILY={spec['layout_family']}")
    print(f"DESIGN_SPEC={design_spec_copy}")
    print(f"BACKGROUND={background}")
    print(f"IMAGE={output}")
    print(f"COPY={copy_path}")
    print("TEXT_RENDERING=deterministic_python_design_spec")


if __name__ == "__main__":
    main()
