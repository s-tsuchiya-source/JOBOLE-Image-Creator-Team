from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.creative_spec import build_integrated_image_prompt, normalize_creative_spec


def main() -> None:
    raw = {
        "version": "5.0",
        "mode": "codex_integrated",
        "benchmark_refs": ["R0001", "R0002"],
        "strategy": {"message_axis": "access", "fact_ids": ["F001"]},
        "text_contract": [
            {
                "id": "T001",
                "role": "headline",
                "text": "天王洲アイル駅から徒歩4分",
                "required": True,
                "fact_ids": ["F001"],
                "allow_visual_line_breaks": True,
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
            "visual_style": "premium Japanese recruitment advertising",
            "typography_style": "bold integrated Japanese typography",
            "composition": "human-led dynamic composition",
            "text_zone": "dynamic",
            "accent_color": "#E85A3D",
            "diversity_from_siblings": "avoid previous left-copy/right-person split",
        },
        "image": {"prompt": "Create a realistic child-development support work scene."},
        "execution": {
            "generation_owner": "codex_integrated_creative_designer",
            "generation_capability": "codex_imagegen",
            "prefer_edit_before_regenerate": True,
        },
        "forbidden_extra_text": ["アルバイト募集"],
    }

    spec = normalize_creative_spec(raw)
    assert spec["mode"] == "codex_integrated"
    assert spec["execution"]["generation_owner"] == "codex_integrated_creative_designer"
    assert spec["execution"]["generation_capability"] == "codex_imagegen"
    assert spec["execution"]["silent_api_fallback_allowed"] is False

    prompt = build_integrated_image_prompt(spec, width=1200, height=900)
    assert "Codex Integrated Creative Designer" in prompt
    assert "codex_imagegen" in prompt
    assert "Do not route the standard generation through Python" in prompt
    assert "天王洲アイル駅から徒歩4分" in prompt
    assert "児童発達支援管理責任者" in prompt
    assert "アルバイト募集" in prompt

    env_text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "CREATIVE_RENDER_MODE=codex_imagegen" in env_text
    assert "SILENT_API_FALLBACK_ALLOWED=false" in env_text
    assert "API_FALLBACK_ENABLED=false" in env_text

    generate_text = (REPO_ROOT / "scripts" / "generate_creative.py").read_text(encoding="utf-8")
    assert "v5 primary generation is owned by Codex Integrated Creative Designer" in generate_text
    assert "API fallback is disabled" in generate_text

    register_text = (REPO_ROOT / "scripts" / "register_codex_candidate.py").read_text(encoding="utf-8")
    assert "CODEX IMAGEGEN CANDIDATE REGISTRATION: PASS" in register_text
    assert '"generation_capability": "codex_imagegen"' in register_text
    assert '"api_key_required_for_primary_generation": False' in register_text

    print("CODEX IMAGEGEN CONTRACT TEST: PASS")


if __name__ == "__main__":
    main()
