from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.creative_spec import build_integrated_image_prompt, normalize_creative_spec
from services.text_verifier import compare_text_contract


def main() -> None:
    raw = {
        "version": "4.0",
        "mode": "premium_integrated",
        "benchmark_refs": ["R0001"],
        "text_contract": [
            {
                "id": "T001",
                "role": "headline",
                "text": "月給33万750円〜42万8,750円",
                "required": True,
                "fact_ids": ["F001"],
                "priority": 1,
            },
            {
                "id": "T002",
                "role": "subcopy",
                "text": "児童発達支援管理責任者",
                "required": True,
                "fact_ids": ["F002"],
                "priority": 2,
            },
        ],
        "design_direction": {
            "visual_style": "premium recruitment ad",
            "typography_style": "bold editorial Japanese typography",
            "composition": "text left, professional subject right",
            "text_zone": "left",
            "accent_color": "#1F95B4",
            "photo_direction": "realistic welfare workplace",
        },
        "image": {"prompt": "Create a polished welfare recruitment advertisement."},
        "forbidden_extra_text": ["アルバイト", "児童指導員"],
    }
    spec = normalize_creative_spec(raw)
    prompt = build_integrated_image_prompt(spec, width=1200, height=900)
    assert "月給33万750円〜42万8,750円" in prompt
    assert "児童発達支援管理責任者" in prompt
    assert "アルバイト" in prompt

    passed = compare_text_contract(spec, "月給33万750円〜42万8,750円 児童発達支援管理責任者")
    assert passed["status"] == "pass", passed

    failed = compare_text_contract(spec, "月給33万750円〜42万7,750円 児童発達支援管理責任者")
    assert failed["status"] == "fail", failed
    assert failed["numeric_fact_pass"] is False

    print("PREMIUM CONTRACT TEST: PASS")


if __name__ == "__main__":
    main()
