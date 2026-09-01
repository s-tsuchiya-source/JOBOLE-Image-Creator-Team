from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env", override=True)

from services.image_generator import create_image_generator
from services.overlay_renderer import render_overlay


def _overlay_items(args: argparse.Namespace) -> list[dict]:
    items: list[dict] = [
        {
            "role": "main_copy",
            "text": args.headline,
            "placement": args.headline_placement,
        }
    ]
    if args.subcopy.strip():
        items.append(
            {
                "role": "sub_copy",
                "text": args.subcopy,
                "placement": args.subcopy_placement,
            }
        )
    for value in args.fact:
        if value.strip():
            items.append(
                {
                    "role": "fact",
                    "text": value.strip(),
                    "placement": args.fact_placement,
                }
            )
    if args.cta.strip():
        items.append(
            {
                "role": "cta",
                "text": args.cta,
                "placement": args.cta_placement,
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
            f"- image_provider: {provider}",
            "- required_text_rendering: deterministic_python_overlay",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a text-free advertising background with the selected image backend, "
            "then render exact Japanese copy with Python and save a companion copy.md."
        )
    )
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--negative-prompt", default="")
    parser.add_argument("--headline", required=True)
    parser.add_argument("--subcopy", default="")
    parser.add_argument("--fact", action="append", default=[])
    parser.add_argument("--cta", default="")
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--height", type=int, default=628)
    parser.add_argument("--output", required=True)
    parser.add_argument("--headline-placement", default="top_left")
    parser.add_argument("--subcopy-placement", default="top_left")
    parser.add_argument("--fact-placement", default="bottom_left")
    parser.add_argument("--cta-placement", default="bottom_left")
    args = parser.parse_args()

    if args.width < 256 or args.height < 256:
        raise SystemExit("width/height must both be at least 256 pixels")

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    copy_path = output.with_name(output.stem + "-copy.md")

    generator = create_image_generator()
    provider = getattr(generator, "provider_name", type(generator).__name__)

    # Required copy is intentionally excluded from the image-model prompt.
    # The model should create only the visual background/composition.
    background_prompt = (
        args.prompt.strip()
        + "\n\nDo not render any letters, words, captions, logos, watermarks, "
        "numbers, or readable text. Leave clean negative space for later typography."
    )
    negative_prompt = args.negative_prompt.strip()
    if negative_prompt:
        negative_prompt += ", text, letters, words, captions, watermark"
    else:
        negative_prompt = "text, letters, words, captions, watermark"

    with tempfile.TemporaryDirectory(prefix="jobole_creative_") as tmpdir:
        background = Path(tmpdir) / "background.png"
        generator.generate(
            prompt=background_prompt,
            negative_prompt=negative_prompt,
            width=args.width,
            height=args.height,
            output_path=background,
        )
        render_overlay(
            background,
            _overlay_items(args),
            output_path=output,
        )

    _write_copy_markdown(
        copy_path,
        headline=args.headline,
        subcopy=args.subcopy,
        facts=args.fact,
        cta=args.cta,
        width=args.width,
        height=args.height,
        provider=provider,
    )

    print("CREATIVE GENERATION: PASS")
    print(f"BACKEND={provider}")
    print(f"IMAGE={output}")
    print(f"COPY={copy_path}")
    print("TEXT_RENDERING=deterministic_python_overlay")


if __name__ == "__main__":
    main()
