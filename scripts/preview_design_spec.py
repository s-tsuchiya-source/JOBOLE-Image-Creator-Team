from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from load_project import load_environment, resolve_project_dir
from services.design_spec import load_design_spec
from services.overlay_renderer import render_design_spec


def _load_context(project_dir: Path) -> dict:
    path = project_dir / "00_request" / "normalized" / "creative-context.json"
    if not path.exists():
        raise SystemExit(
            "creative-context.json がありません。先に prepare_creative_context.py を実行してください。"
        )
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _placeholder(path: Path, width: int, height: int, text_zone: str) -> None:
    image = Image.new("RGB", (width, height), (242, 242, 239))
    draw = ImageDraw.Draw(image)
    visual_left = round(width * 0.53) if text_zone == "left" else round(width * 0.04)
    visual_right = round(width * 0.96) if text_zone == "left" else round(width * 0.47)
    draw.rectangle((visual_left, 0, visual_right, height), fill=(226, 231, 225))
    person_x = (visual_left + visual_right) // 2
    head_r = max(30, round(height * 0.07))
    head_y = round(height * 0.28)
    draw.ellipse(
        (person_x - head_r, head_y - head_r, person_x + head_r, head_y + head_r),
        fill=(187, 196, 187),
    )
    body_w = max(100, round(width * 0.13))
    body_h = max(180, round(height * 0.34))
    draw.rounded_rectangle(
        (person_x - body_w // 2, head_y + head_r, person_x + body_w // 2, head_y + head_r + body_h),
        radius=max(20, body_w // 5),
        fill=(197, 205, 198),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render an approved Design Spec on a neutral placeholder before spending image-generation cost."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--creative-id", default="CR001")
    parser.add_argument("--design-spec-file", default="")
    args = parser.parse_args()

    projects_root = load_environment()
    project_dir = resolve_project_dir(projects_root, args.project_id)
    context = _load_context(project_dir)
    output_spec = context.get("resolved_output_spec", {})
    width = int(output_spec.get("width") or 1200)
    height = int(output_spec.get("height") or 628)

    spec_path = (
        Path(args.design_spec_file).expanduser().resolve()
        if args.design_spec_file.strip()
        else project_dir / "02_direction" / f"{args.creative_id}-design-spec.json"
    )
    if not spec_path.exists():
        raise SystemExit(f"Design Specがありません: {spec_path}")

    spec = load_design_spec(spec_path)
    preview_dir = project_dir / "02_direction" / "previews"
    placeholder = preview_dir / f"{args.creative_id}-placeholder.png"
    preview = preview_dir / f"{args.creative_id}-design-preview.png"
    _placeholder(placeholder, width, height, spec["text_zone"])
    render_design_spec(placeholder, spec, output_path=preview)

    print("DESIGN SPEC PREVIEW: PASS")
    print(f"DESIGN_SPEC={spec_path}")
    print(f"LAYOUT_FAMILY={spec['layout_family']}")
    print(f"PREVIEW={preview}")
    print("NOTE=This preview validates typography/layout only; it is not the final visual background.")


if __name__ == "__main__":
    main()
