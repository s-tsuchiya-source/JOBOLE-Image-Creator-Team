from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable


HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
ALLOWED_TEXT_ROLES = {"headline", "subcopy", "fact", "cta", "label"}
ALLOWED_TEXT_ZONES = {"left", "right", "center", "distributed", "dynamic"}
ALLOWED_MODES = {"codex_integrated", "premium_integrated"}  # v4 accepted for migration


class CreativeSpecError(ValueError):
    pass


def _text(value: object) -> str:
    return str(value or "").strip()


def _list(value: object, *, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = _text(item)
        if text and text not in result:
            result.append(text)
        if limit and len(result) >= limit:
            break
    return result


def normalize_creative_spec(data: dict, *, benchmark_max: int = 3, text_block_max: int = 6) -> dict:
    if not isinstance(data, dict):
        raise CreativeSpecError("creative spec must be a JSON object")

    source_mode = _text(data.get("mode")) or "codex_integrated"
    if source_mode not in ALLOWED_MODES:
        raise CreativeSpecError(
            f"creative spec mode must be one of {sorted(ALLOWED_MODES)}; got {source_mode!r}"
        )

    benchmark_refs = _list(data.get("benchmark_refs"), limit=benchmark_max)
    direction = data.get("design_direction") if isinstance(data.get("design_direction"), dict) else {}

    accent_color = _text(direction.get("accent_color")) or "#E85A3D"
    if not HEX_RE.match(accent_color):
        raise CreativeSpecError("design_direction.accent_color must be #RRGGBB")

    text_zone = _text(direction.get("text_zone")) or "dynamic"
    if text_zone not in ALLOWED_TEXT_ZONES:
        raise CreativeSpecError(f"unsupported text_zone={text_zone!r}")

    raw_blocks = data.get("text_contract")
    if not isinstance(raw_blocks, list) or not raw_blocks:
        raise CreativeSpecError("text_contract must contain at least one required text block")
    if len(raw_blocks) > text_block_max:
        raise CreativeSpecError(f"text_contract exceeds max={text_block_max}")

    blocks: list[dict] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_blocks, start=1):
        if not isinstance(raw, dict):
            raise CreativeSpecError("each text_contract item must be an object")
        block_id = _text(raw.get("id")) or f"T{index:03d}"
        if block_id in seen_ids:
            raise CreativeSpecError(f"duplicate text block id: {block_id}")
        seen_ids.add(block_id)

        role = _text(raw.get("role")) or "fact"
        if role not in ALLOWED_TEXT_ROLES:
            raise CreativeSpecError(f"unsupported text role={role!r}")

        text = _text(raw.get("text"))
        if not text:
            raise CreativeSpecError(f"text block {block_id} is empty")

        blocks.append(
            {
                "id": block_id,
                "role": role,
                "text": text,
                "required": bool(raw.get("required", True)),
                "fact_ids": _list(raw.get("fact_ids"), limit=6),
                "allow_visual_line_breaks": bool(raw.get("allow_visual_line_breaks", True)),
                "priority": int(raw.get("priority") or index),
            }
        )

    image = data.get("image") if isinstance(data.get("image"), dict) else {}
    prompt = _text(image.get("prompt"))
    if not prompt:
        raise CreativeSpecError("image.prompt is required")

    execution = data.get("execution") if isinstance(data.get("execution"), dict) else {}
    generation_owner = _text(execution.get("generation_owner")) or "codex_integrated_creative_designer"
    generation_capability = _text(execution.get("generation_capability")) or "codex_imagegen"
    if generation_owner != "codex_integrated_creative_designer":
        raise CreativeSpecError("execution.generation_owner must be codex_integrated_creative_designer")
    if generation_capability != "codex_imagegen":
        raise CreativeSpecError("execution.generation_capability must be codex_imagegen")

    return {
        "version": _text(data.get("version")) or "5.0",
        "mode": "codex_integrated",
        "benchmark_refs": benchmark_refs,
        "strategy": data.get("strategy") if isinstance(data.get("strategy"), dict) else {},
        "text_contract": sorted(blocks, key=lambda item: item["priority"]),
        "design_direction": {
            "visual_style": _text(direction.get("visual_style")),
            "typography_style": _text(direction.get("typography_style")),
            "composition": _text(direction.get("composition")),
            "text_zone": text_zone,
            "accent_color": accent_color.upper(),
            "color_system": _text(direction.get("color_system")),
            "decoration": _text(direction.get("decoration")),
            "photo_direction": _text(direction.get("photo_direction")),
            "diversity_from_siblings": _text(direction.get("diversity_from_siblings")),
        },
        "image": {
            "prompt": prompt,
            "negative_prompt": _text(image.get("negative_prompt")),
        },
        "execution": {
            "generation_owner": generation_owner,
            "generation_capability": generation_capability,
            "prefer_edit_before_regenerate": bool(execution.get("prefer_edit_before_regenerate", True)),
            "silent_api_fallback_allowed": False,
        },
        "forbidden_extra_text": _list(data.get("forbidden_extra_text"), limit=10),
        "notes": _text(data.get("notes")),
    }


def load_creative_spec(path: Path, *, benchmark_max: int = 3, text_block_max: int = 6) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise CreativeSpecError(f"invalid creative spec JSON: {exc}") from exc
    return normalize_creative_spec(raw, benchmark_max=benchmark_max, text_block_max=text_block_max)


def write_creative_spec(path: Path, spec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8-sig")


def expected_text_blocks(spec: dict) -> list[dict]:
    return [dict(item) for item in spec.get("text_contract", []) if item.get("required", True)]


def expected_text_plain(spec: dict) -> str:
    return "\n".join(item["text"] for item in expected_text_blocks(spec))


def build_integrated_image_prompt(spec: dict, *, width: int, height: int) -> str:
    """Build the approved execution brief for Codex ImageGen.

    This function only assembles text. It does not call an image API.
    """
    direction = spec["design_direction"]
    text_lines: list[str] = []
    for item in spec["text_contract"]:
        required = "REQUIRED" if item.get("required", True) else "OPTIONAL"
        text_lines.append(f"- [{required}][{item['role']}][{item['id']}] {item['text']}")

    benchmark_text = ", ".join(spec.get("benchmark_refs", [])) or "none"
    forbidden = ", ".join(spec.get("forbidden_extra_text", [])) or "none"

    return f"""You are the Codex Integrated Creative Designer using the available ImageGen capability.
Create a finished Japanese recruitment advertising banner, not a mockup, not a background asset, and not a template preview.

EXECUTION OWNERSHIP
- Generation owner: codex_integrated_creative_designer.
- Generation capability: codex_imagegen.
- Do not route the standard generation through Python or a direct OpenAI Images API call.
- If ImageGen capability is unavailable, stop with IMAGEGEN_CAPABILITY_UNAVAILABLE rather than silently changing backend.

OUTPUT
- Final aspect/canvas target: {width}x{height}.
- Integrate photography, layout, decorative graphics, typography and Japanese copy as one composition.
- The result must look like a high-end Japanese recruitment ad designed by a human art director.

BENCHMARK
- Reference IDs selected by the CCO: {benchmark_text}.
- Follow their quality level and visual grammar without copying a specific sample literally.

VISUAL DIRECTION
- visual style: {direction.get('visual_style') or 'premium Japanese recruitment advertising'}
- photo direction: {direction.get('photo_direction') or 'realistic job-relevant human photography'}
- composition: {direction.get('composition') or 'dynamic, intentional recruitment-ad composition'}
- text zone concept: {direction.get('text_zone')}
- typography style: {direction.get('typography_style') or 'expressive professional Japanese advertising typography'}
- accent color: {direction.get('accent_color')}
- color system: {direction.get('color_system') or 'one dominant accent with restrained supporting colors'}
- decoration: {direction.get('decoration') or 'intentional decorative accents that reinforce the message'}
- difference from sibling creatives: {direction.get('diversity_from_siblings') or 'avoid repeating the same layout grammar'}

CREATIVE DIRECTION
{spec['image']['prompt']}

EXACT JAPANESE TEXT CONTRACT
Render the following text exactly. Do not paraphrase, translate, add, omit, substitute, or change any digit, punctuation mark, currency expression, employment type, job title, or condition. Visual line breaks may change only when allowed; characters must remain exact.
{chr(10).join(text_lines)}

TEXT RULES
- No additional readable text, fake logo, random letters, signage, watermark, or invented copy.
- Every REQUIRED block must be clearly legible at normal banner viewing size.
- Do not merge blocks in a way that changes meaning.
- Typography must feel designed into the image, never pasted on as a generic overlay.
- Use deliberate scale, weight, spacing, color, outlines, ribbons, shapes, diagonal rhythm, or controlled overlap only where it improves the ad.

FORBIDDEN / DO NOT INVENT
{forbidden}

FINAL QUALITY BAR
The final image must be delivery-ready for Japanese recruitment advertising. Reject generic AI-poster aesthetics, dashboard/card layouts, repeated chip templates, weak text hierarchy, and stock-photo-plus-caption compositions.
""".strip()


def all_required_text(spec: dict) -> Iterable[str]:
    for block in expected_text_blocks(spec):
        yield block["text"]
