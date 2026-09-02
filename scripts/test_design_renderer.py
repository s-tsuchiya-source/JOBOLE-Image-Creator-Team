from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.design_spec import normalize_design_spec
from services.overlay_renderer import render_design_spec


SPECS = [
    {
        "layout_family": "numeric_impact",
        "accent_color": "#1E86A5",
        "text_zone": "left",
        "headline": {
            "lines": ["月給33万750円〜", "42万8,750円"],
            "emphasis": ["33万750円", "42万8,750円"],
        },
        "subcopy": {"text": "児童発達支援管理責任者"},
        "facts": ["駅徒歩4分", "交通費全額支給"],
        "cta": {"text": "詳しく見る"},
        "image": {"prompt": "test", "negative_prompt": ""},
        "decorations": {"accent_bar": True, "rays": False, "soft_shape": True},
    },
    {
        "layout_family": "short_power_word",
        "accent_color": "#C9684E",
        "text_zone": "left",
        "headline": {"lines": ["ブランクOK"], "emphasis": ["OK"]},
        "subcopy": {"text": "児発管研修修了者"},
        "facts": ["年齢不問・学歴不問"],
        "cta": {"text": "詳しく見る"},
        "image": {"prompt": "test", "negative_prompt": ""},
        "decorations": {"accent_bar": True, "rays": True, "soft_shape": True},
    },
    {
        "layout_family": "concept_message",
        "accent_color": "#F26A42",
        "text_zone": "left",
        "headline": {"lines": ["スポーツ×", "福祉"], "emphasis": ["スポーツ", "福祉"]},
        "subcopy": {"text": "児童発達支援管理責任者"},
        "facts": ["地域のスポーツ施設と連携"],
        "cta": {"text": "詳しく見る"},
        "image": {"prompt": "test", "negative_prompt": ""},
        "decorations": {"accent_bar": True, "rays": False, "soft_shape": True},
    },
    {
        "layout_family": "work_scene",
        "accent_color": "#3B8F76",
        "text_zone": "left",
        "headline": {"lines": ["子どもの成長を", "支援する仕事"], "emphasis": ["成長"]},
        "subcopy": {"text": "児童発達支援管理責任者"},
        "facts": ["個別支援計画の作成", "スタッフ連携"],
        "cta": {"text": "詳しく見る"},
        "image": {"prompt": "test", "negative_prompt": ""},
        "decorations": {"accent_bar": False, "rays": False, "soft_shape": False},
    },
    {
        "layout_family": "benefit_stack",
        "accent_color": "#D68432",
        "text_zone": "left",
        "headline": {"lines": ["働く条件も", "しっかり確認"], "emphasis": ["条件"]},
        "subcopy": {"text": "児童発達支援管理責任者"},
        "facts": ["月給33万750円〜", "駅徒歩4分", "交通費全額支給"],
        "cta": {"text": "詳しく見る"},
        "image": {"prompt": "test", "negative_prompt": ""},
        "decorations": {"accent_bar": True, "rays": False, "soft_shape": True},
    },
    {
        "layout_family": "emotional_message",
        "accent_color": "#A65B78",
        "text_zone": "left",
        "headline": {"lines": ["一人ひとりの", "成長に寄り添う"], "emphasis": ["成長"]},
        "subcopy": {"text": "スポーツを通じた発達支援"},
        "facts": ["児童発達支援管理責任者"],
        "cta": {"text": "詳しく見る"},
        "image": {"prompt": "test", "negative_prompt": ""},
        "decorations": {"accent_bar": False, "rays": False, "soft_shape": True},
    },
]


def _background(path: Path, width: int = 1200, height: int = 900) -> None:
    image = Image.new("RGB", (width, height), (239, 241, 239))
    draw = ImageDraw.Draw(image)
    draw.rectangle((650, 0, width, height), fill=(219, 227, 220))
    draw.ellipse((760, 130, 1080, 500), fill=(183, 198, 187))
    draw.rectangle((720, 520, 1120, 760), fill=(199, 210, 201))
    image.save(path)


def main() -> None:
    output_dir = REPO_ROOT / "tmp" / "layout-smoke"
    output_dir.mkdir(parents=True, exist_ok=True)
    background = output_dir / "background.png"
    _background(background)

    for raw in SPECS:
        spec = normalize_design_spec(raw)
        output = output_dir / f"{spec['layout_family']}.png"
        render_design_spec(background, spec, output_path=output)
        print(f"PASS {spec['layout_family']}: {output}")

    print("DESIGN RENDERER SMOKE TEST: PASS")


if __name__ == "__main__":
    main()
