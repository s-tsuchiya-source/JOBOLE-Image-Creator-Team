from __future__ import annotations

import argparse
import json
import re
import os
from pathlib import Path
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
from services.image_generator import create_image_generator
from services.overlay_renderer import render_overlay


SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _overlay_items(args: argparse.Namespace) -> list[dict]:
    items: list[dict] = [
        {
            "role": "main_copy",
            "text": args.headline,
        }
    ]
    if args.subcopy.strip():
        items.append(
            {
                "role": "sub_copy",
                "text": args.subcopy,
            }
        )
    for value in args.fact:
        if value.strip():
            items.append(
                {
                    "role": "fact",
                    "text": value.strip(),
                }
            )
    if args.cta.strip():
        items.append(
            {
                "role": "cta",
                "text": args.cta,
            }
        )
    return items


def _write_copy_markdown(
    path: Path,
    *,
    headline: str,
    subcopy: str,
    facts: list[str],
    cta: str,
    width: int,
    height: int,
    provider: str,
    accent_color: str,
    design_style: str,
    output_spec_source: str,
) -> None:
    lines = [
        "# Creative Copy",
        "",
        "このファイルは完成画像へ実際に後載せした元文言を保持します。",
        "画像上の自動折り返しは表示上の改行であり、文字列自体は変更していません。",
        "",
        "## Headline",
        headline,
        "",
    ]
    if subcopy.strip():
        lines.extend(["## Subcopy", subcopy, ""])
    if facts:
        lines.append("## Fact Text")
        for fact in facts:
            if fact.strip():
                lines.append(f"- {fact.strip()}")
        lines.append("")
    if cta.strip():
        lines.extend(["## CTA", cta, ""])
    lines.extend(
        [
            "## Technical",
            f"- size: {width}x{height}",
            f"- output_spec_source: {output_spec_source}",
            f"- image_provider: {provider}",
            f"- design_style: {design_style}",
            f"- accent_color: {accent_color}",
            "- required_text_rendering: deterministic_python_overlay",
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
                "ヒアリングで指定された媒体比率と生成サイズが一致しません: "
                f"expected={spec.get('aspect_ratio')} resolved={context_width}x{context_height}, "
                f"requested={width}x{height}"
            )
    return width, height, source


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate one project-scoped recruitment creative. The project and compact creative context "
            "must already exist; final files are always saved in its 05_delivery folder."
        )
    )
    parser.add_argument(
        "--project-id",
        required=True,
        help="Project id/folder prefix created by create_project_from_intake.py, e.g. PJ-0003",
    )
    parser.add_argument("--creative-id", default="CR001")
    parser.add_argument("--output-name", default="")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--negative-prompt", default="")
    parser.add_argument("--headline", required=True)
    parser.add_argument("--subcopy", default="")
    parser.add_argument("--fact", action="append", default=[])
    parser.add_argument("--cta", default="")
    parser.add_argument(
        "--width",
        type=int,
        default=0,
        help="Optional. If omitted, use the hearing-resolved size from creative-context.json.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=0,
        help="Optional. If omitted, use the hearing-resolved size from creative-context.json.",
    )
    parser.add_argument("--design-style", default="benchmark_recruit")
    parser.add_argument("--accent-color", default="#E84C4C")
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

    fact_chip_max = int(os.getenv("FACT_CHIP_MAX", "3"))
    facts = [value.strip() for value in args.fact if value.strip()]
    if len(facts) > fact_chip_max:
        raise SystemExit(
            f"Fact表示が多すぎます。FACT_CHIP_MAX={fact_chip_max} のため、強いFactだけに絞ってください。"
        )

    delivery_dir = project_dir / "05_delivery"
    batch_dir = project_dir / "03_batches" / args.creative_id / "v001"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    batch_dir.mkdir(parents=True, exist_ok=True)

    output_name = _safe_output_name(args.output_name, args.creative_id)
    output = delivery_dir / output_name
    copy_path = output.with_name(output.stem + "-copy.md")
    background = batch_dir / "background.png"
    prompt_path = batch_dir / "image-prompt.txt"

    generator = create_image_generator()
    provider = getattr(generator, "provider_name", type(generator).__name__)

    background_prompt = (
        args.prompt.strip()
        + "\n\nDo not render any letters, words, captions, logos, watermarks, numbers, or readable text. "
        "Preserve the approved composition and intentional typography-safe negative space from the art direction."
    )
    negative_prompt = args.negative_prompt.strip()
    if negative_prompt:
        negative_prompt += ", text, letters, words, captions, watermark"
    else:
        negative_prompt = "text, letters, words, captions, watermark"

    prompt_path.write_text(
        "# Image Prompt\n\n"
        + background_prompt
        + "\n\n# Negative Prompt\n\n"
        + negative_prompt
        + "\n\n# Context\n\n"
        + f"creative_context: {context_path}\n"
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
    render_overlay(
        background,
        _overlay_items(args),
        output_path=output,
        accent_color=args.accent_color,
        design_style=args.design_style,
    )

    _write_copy_markdown(
        copy_path,
        headline=args.headline,
        subcopy=args.subcopy,
        facts=facts,
        cta=args.cta,
        width=width,
        height=height,
        provider=provider,
        accent_color=args.accent_color,
        design_style=args.design_style,
        output_spec_source=output_spec_source,
    )

    print("CREATIVE GENERATION: PASS")
    print(f"PROJECT_ID={args.project_id}")
    print(f"PROJECT_DIR={project_dir}")
    print(f"BACKEND={provider}")
    print(f"SIZE={width}x{height}")
    print(f"OUTPUT_SPEC_SOURCE={output_spec_source}")
    print(f"BACKGROUND={background}")
    print(f"IMAGE={output}")
    print(f"COPY={copy_path}")
    print("TEXT_RENDERING=deterministic_python_overlay")


if __name__ == "__main__":
    main()
