from __future__ import annotations

import json
import re
from pathlib import Path


ALLOWED_LAYOUT_FAMILIES = {
    "numeric_impact",
    "short_power_word",
    "concept_message",
    "work_scene",
    "benefit_stack",
    "emotional_message",
}
ALLOWED_TEXT_ZONES = {"left", "right"}
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class DesignSpecError(ValueError):
    pass


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _clean_lines(value: object, fallback_text: str) -> list[str]:
    if isinstance(value, list):
        lines = [_clean_text(item) for item in value if _clean_text(item)]
    else:
        lines = []
    if not lines and fallback_text:
        lines = [line.strip() for line in fallback_text.splitlines() if line.strip()]
    return lines


def _clean_string_list(value: object, *, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = _clean_text(item)
        if text and text not in result:
            result.append(text)
        if limit and len(result) >= limit:
            break
    return result


def normalize_design_spec(data: dict, *, fact_max: int = 3) -> dict:
    if not isinstance(data, dict):
        raise DesignSpecError("design spec must be a JSON object")

    layout_family = _clean_text(data.get("layout_family")) or "concept_message"
    if layout_family not in ALLOWED_LAYOUT_FAMILIES:
        raise DesignSpecError(
            f"unsupported layout_family={layout_family!r}; allowed={sorted(ALLOWED_LAYOUT_FAMILIES)}"
        )

    accent_color = _clean_text(data.get("accent_color")) or "#E85A3D"
    if not HEX_RE.match(accent_color):
        raise DesignSpecError("accent_color must be #RRGGBB")

    text_zone = _clean_text(data.get("text_zone")) or "left"
    if text_zone not in ALLOWED_TEXT_ZONES:
        raise DesignSpecError("text_zone must be left or right")

    headline_data = data.get("headline") if isinstance(data.get("headline"), dict) else {}
    headline_text = _clean_text(headline_data.get("text") or data.get("headline_text"))
    headline_lines = _clean_lines(headline_data.get("lines"), headline_text)
    if not headline_lines:
        raise DesignSpecError("headline text/lines are required")
    if len(headline_lines) > 3:
        raise DesignSpecError("headline must be 3 lines or fewer")

    headline_text = "\n".join(headline_lines)
    emphasis = _clean_string_list(headline_data.get("emphasis"), limit=4)
    for token in emphasis:
        if token not in headline_text.replace("\n", ""):
            raise DesignSpecError(f"headline emphasis token is not present in headline: {token}")

    subcopy_data = data.get("subcopy") if isinstance(data.get("subcopy"), dict) else {}
    subcopy_text = _clean_text(subcopy_data.get("text") or data.get("subcopy_text"))

    raw_facts = data.get("facts", [])
    facts: list[str] = []
    if isinstance(raw_facts, list):
        for item in raw_facts:
            text = _clean_text(item.get("text") if isinstance(item, dict) else item)
            if text and text not in facts:
                facts.append(text)
    if len(facts) > fact_max:
        raise DesignSpecError(f"facts exceed fact_max={fact_max}")

    cta_data = data.get("cta") if isinstance(data.get("cta"), dict) else {}
    cta_text = _clean_text(cta_data.get("text") or data.get("cta_text"))

    decorations = data.get("decorations") if isinstance(data.get("decorations"), dict) else {}
    normalized = {
        "version": _clean_text(data.get("version")) or "1.0",
        "layout_family": layout_family,
        "accent_color": accent_color.upper(),
        "text_zone": text_zone,
        "headline": {
            "text": headline_text,
            "lines": headline_lines,
            "emphasis": emphasis,
            "tone": _clean_text(headline_data.get("tone")) or "strong",
        },
        "subcopy": {"text": subcopy_text},
        "facts": facts,
        "cta": {"text": cta_text},
        "decorations": {
            "accent_bar": bool(decorations.get("accent_bar", True)),
            "rays": bool(decorations.get("rays", False)),
            "soft_shape": bool(decorations.get("soft_shape", True)),
            "bottom_band": bool(decorations.get("bottom_band", False)),
        },
        "notes": _clean_text(data.get("notes")),
    }
    return normalized


def load_design_spec(path: Path, *, fact_max: int = 3) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise DesignSpecError(f"invalid design spec JSON: {exc}") from exc
    return normalize_design_spec(raw, fact_max=fact_max)


def write_design_spec(path: Path, spec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8-sig")


def overlay_items_from_design_spec(spec: dict) -> list[dict]:
    items: list[dict] = [
        {
            "role": "main_copy",
            "text": spec["headline"]["text"],
            "lines": spec["headline"]["lines"],
            "emphasis": spec["headline"].get("emphasis", []),
        }
    ]
    if spec["subcopy"]["text"]:
        items.append({"role": "sub_copy", "text": spec["subcopy"]["text"]})
    for fact in spec["facts"]:
        items.append({"role": "fact", "text": fact})
    if spec["cta"]["text"]:
        items.append({"role": "cta", "text": spec["cta"]["text"]})
    return items
