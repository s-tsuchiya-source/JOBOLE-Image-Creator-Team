from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageColor, ImageDraw, ImageFont


BOLD_FONT_CANDIDATES = [
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
]
REGULAR_FONT_CANDIDATES = [
    "C:/Windows/Fonts/YuGothR.ttc",
    "C:/Windows/Fonts/YuGothM.ttc",
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
]
SUPPORTED_DESIGN_STYLES = {"benchmark_recruit", "modern_recruit", "clean_recruit"}
SUPPORTED_LAYOUT_FAMILIES = {
    "numeric_impact",
    "short_power_word",
    "concept_message",
    "work_scene",
    "benefit_stack",
    "emotional_message",
}


def _existing_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.exists() else None


def _first_existing(candidates: list[str]) -> Path | None:
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return path
    return None


def resolve_font_paths() -> tuple[Path, Path]:
    bold = (
        _existing_path(os.getenv("JAPANESE_BOLD_FONT_PATH"))
        or _existing_path(os.getenv("JAPANESE_FONT_PATH"))
        or _first_existing(BOLD_FONT_CANDIDATES)
    )
    regular = (
        _existing_path(os.getenv("JAPANESE_REGULAR_FONT_PATH"))
        or _first_existing(REGULAR_FONT_CANDIDATES)
        or _existing_path(os.getenv("JAPANESE_FONT_PATH"))
    )
    if not bold:
        raise FileNotFoundError("Japanese bold font was not found. Set JAPANESE_BOLD_FONT_PATH.")
    if not regular:
        raise FileNotFoundError("Japanese regular font was not found. Set JAPANESE_REGULAR_FONT_PATH.")
    return bold, regular


def _hex_rgb(value: str) -> tuple[int, int, int]:
    try:
        return ImageColor.getrgb(value)
    except ValueError as exc:
        raise ValueError(f"Invalid accent color: {value}") from exc


def _blend(rgb: tuple[int, int, int], target: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(channel + (target[index] - channel) * amount) for index, channel in enumerate(rgb))


def _darken(rgb: tuple[int, int, int], amount: float = 0.18) -> tuple[int, int, int]:
    return _blend(rgb, (0, 0, 0), amount)


def _lighten(rgb: tuple[int, int, int], amount: float = 0.88) -> tuple[int, int, int]:
    return _blend(rgb, (255, 255, 255), amount)


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    if not text:
        return 0
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _wrap_line(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    if not text or _text_width(draw, text, font) <= max_width:
        return [text]
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and _text_width(draw, candidate, font) > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _fit_manual_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font_path: Path,
    max_width: int,
    *,
    max_size: int,
    min_size: int,
    max_lines: int = 3,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    lines = [line.strip() for line in lines if line.strip()]
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(str(font_path), size=size)
        if len(lines) <= max_lines and all(_text_width(draw, line, font) <= max_width for line in lines):
            return font, lines

    font = ImageFont.truetype(str(font_path), size=min_size)
    fallback: list[str] = []
    for line in lines:
        fallback.extend(_wrap_line(draw, line, font, max_width))
    if len(fallback) > max_lines:
        raise ValueError(
            "Headline does not fit the approved layout. Shorten the copy or provide better semantic line breaks."
        )
    return font, fallback


def _segments(line: str, emphasis: list[str]) -> list[tuple[str, bool]]:
    tokens = sorted([token for token in emphasis if token and token in line], key=len, reverse=True)
    if not tokens:
        return [(line, False)]
    pattern = "(" + "|".join(re.escape(token) for token in tokens) + ")"
    parts = [part for part in re.split(pattern, line) if part]
    return [(part, part in tokens) for part in parts]


def _draw_segmented_line(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    line: str,
    font: ImageFont.FreeTypeFont,
    *,
    emphasis: list[str],
    normal_fill: tuple[int, int, int, int],
    emphasis_fill: tuple[int, int, int, int],
    stroke_width: int = 0,
    stroke_fill: tuple[int, int, int, int] | None = None,
) -> None:
    x, y = xy
    for segment, strong in _segments(line, emphasis):
        fill = emphasis_fill if strong else normal_fill
        draw.text(
            (x, y),
            segment,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
        x += _text_width(draw, segment, font)


def _add_readability_gradient(
    image: Image.Image,
    *,
    side: str,
    width_ratio: float = 0.59,
    strength: int = 218,
) -> None:
    width, height = image.size
    panel_w = max(1, round(width * width_ratio))
    overlay = Image.new("RGBA", (panel_w, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    fade_start = 0.55
    for x in range(panel_w):
        ratio = x / max(1, panel_w - 1)
        alpha = strength if ratio <= fade_start else round(strength * (1 - (ratio - fade_start) / (1 - fade_start)))
        px = x if side == "left" else panel_w - 1 - x
        draw.line((px, 0, px, height), fill=(255, 255, 255, max(0, alpha)))
    image.alpha_composite(overlay, (0, 0) if side == "left" else (width - panel_w, 0))


def _zone_geometry(width: int, *, side: str, ratio: float = 0.49) -> tuple[int, int]:
    zone_w = round(width * ratio)
    margin = max(28, round(width * 0.035))
    x = margin if side == "left" else width - margin - zone_w
    return x, zone_w


def _draw_accent_bar(draw: ImageDraw.ImageDraw, x: int, y: int, height: int, accent: tuple[int, int, int]) -> None:
    bar_w = max(7, round(height * 0.012))
    draw.rounded_rectangle((x, y, x + bar_w, y + height), radius=max(2, bar_w // 2), fill=(*accent, 255))


def _draw_rays(draw: ImageDraw.ImageDraw, x: int, y: int, accent: tuple[int, int, int], scale: int) -> None:
    stroke = max(2, scale // 12)
    rays = [
        ((x, y + scale), (x - scale // 3, y + scale // 2)),
        ((x + scale // 3, y + scale * 3 // 4), (x + scale // 4, y + scale // 4)),
        ((x + scale * 2 // 3, y + scale * 3 // 4), (x + scale * 3 // 4, y + scale // 4)),
        ((x + scale, y + scale), (x + scale * 4 // 3, y + scale // 2)),
    ]
    for start, end in rays:
        draw.line((*start, *end), fill=(*accent, 210), width=stroke)


def _draw_soft_shape(image: Image.Image, *, side: str, accent: tuple[int, int, int]) -> None:
    width, height = image.size
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    shape_w = round(width * 0.27)
    shape_h = round(height * 0.32)
    x0 = -shape_w // 3 if side == "left" else width - shape_w * 2 // 3
    y0 = height - shape_h // 2
    draw.ellipse((x0, y0, x0 + shape_w, y0 + shape_h), fill=(*_lighten(accent, 0.62), 58))
    image.alpha_composite(overlay)


def _draw_subcopy(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    x: int,
    y: int,
    max_width: int,
    font_path: Path,
    height: int,
    fill: tuple[int, int, int, int],
    bold: bool = False,
) -> int:
    if not text:
        return y
    font = ImageFont.truetype(str(font_path), size=max(20, round(height * (0.042 if bold else 0.038))))
    lines = _wrap_line(draw, text, font, max_width)
    if len(lines) > 2:
        font = ImageFont.truetype(str(font_path), size=max(18, round(height * 0.031)))
        lines = _wrap_line(draw, text, font, max_width)
    spacing = max(3, round(font.size * 0.15))
    value = "\n".join(lines[:2])
    bbox = draw.multiline_textbbox((0, 0), value, font=font, spacing=spacing)
    draw.multiline_text((x, y - bbox[1]), value, font=font, fill=fill, spacing=spacing)
    return y + (bbox[3] - bbox[1]) + max(10, round(height * 0.018))


def _draw_facts_and_cta(
    draw: ImageDraw.ImageDraw,
    *,
    facts: list[str],
    cta: str,
    x: int,
    max_width: int,
    bottom_y: int,
    bold_font_path: Path,
    accent: tuple[int, int, int],
    height: int,
    family: str,
) -> None:
    dark = (29, 31, 34, 255)
    gap = max(7, round(height * 0.010))
    accent_light = _lighten(accent, 0.90)

    if cta:
        font = ImageFont.truetype(str(bold_font_path), size=max(20, round(height * 0.034)))
        bbox = draw.textbbox((0, 0), cta, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = max(18, round(font.size * 0.55)), max(8, round(font.size * 0.25))
        box_w, box_h = tw + pad_x * 2, th + pad_y * 2
        y = bottom_y - box_h
        draw.rounded_rectangle((x + 2, y + 4, x + box_w + 2, y + box_h + 4), radius=box_h // 3, fill=(0, 0, 0, 28))
        draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=box_h // 3, fill=(*accent, 255))
        draw.text((x + pad_x, y + pad_y - bbox[1]), cta, font=font, fill=(255, 255, 255, 255))
        bottom_y = y - gap

    if family == "work_scene" and facts:
        font = ImageFont.truetype(str(bold_font_path), size=max(18, round(height * 0.030)))
        text = "  /  ".join(facts[:2])
        lines = _wrap_line(draw, text, font, max_width - 30)
        value = "\n".join(lines[:2])
        bbox = draw.multiline_textbbox((0, 0), value, font=font, spacing=2)
        th = bbox[3] - bbox[1]
        band_h = th + max(18, round(font.size * 0.6))
        y = bottom_y - band_h
        draw.rounded_rectangle((x, y, x + max_width, y + band_h), radius=max(12, band_h // 4), fill=(255, 255, 255, 224))
        draw.multiline_text((x + 16, y + (band_h - th) // 2 - bbox[1]), value, font=font, fill=dark, spacing=2)
        return

    fact_font = ImageFont.truetype(str(bold_font_path), size=max(18, round(height * 0.031)))
    for fact in reversed(facts[:3]):
        lines = _wrap_line(draw, fact, fact_font, max_width - 30)
        value = "\n".join(lines[:2])
        bbox = draw.multiline_textbbox((0, 0), value, font=fact_font, spacing=2)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = max(13, round(fact_font.size * 0.42)), max(6, round(fact_font.size * 0.20))
        box_w, box_h = min(max_width, tw + pad_x * 2), th + pad_y * 2
        y = bottom_y - box_h
        if family == "benefit_stack":
            fill = (*_lighten(accent, 0.84), 238)
            outline = (*accent, 245)
            radius = max(8, box_h // 4)
        else:
            fill = (255, 255, 255, 226)
            outline = (*accent, 220)
            radius = max(8, box_h // 2)
        draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=radius, fill=fill, outline=outline, width=max(2, round(height * 0.0025)))
        draw.multiline_text((x + pad_x, y + pad_y - bbox[1]), value, font=fact_font, fill=dark, spacing=2)
        bottom_y = y - gap


def _render_design_spec(
    image: Image.Image,
    spec: dict,
    *,
    bold_font_path: Path,
    regular_font_path: Path,
) -> Image.Image:
    family = str(spec.get("layout_family") or "concept_message")
    if family not in SUPPORTED_LAYOUT_FAMILIES:
        raise ValueError(f"Unsupported layout family: {family}")
    side = str(spec.get("text_zone") or "left")
    accent = _hex_rgb(str(spec.get("accent_color") or "#E85A3D"))
    decorations = spec.get("decorations") or {}

    _add_readability_gradient(image, side=side, width_ratio=0.59 if family != "work_scene" else 0.52, strength=218 if family != "emotional_message" else 196)
    if decorations.get("soft_shape", True):
        _draw_soft_shape(image, side=side, accent=accent)

    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    x, zone_w = _zone_geometry(width, side=side, ratio=0.49 if family != "work_scene" else 0.43)
    margin_y = max(28, round(height * 0.05))
    dark = (24, 26, 29, 255)
    muted = (67, 71, 76, 255)
    accent_dark = _darken(accent, 0.16)

    headline = spec.get("headline") or {}
    lines = [str(line) for line in headline.get("lines", []) if str(line).strip()]
    emphasis = [str(value) for value in headline.get("emphasis", []) if str(value).strip()]
    subcopy = str((spec.get("subcopy") or {}).get("text") or "").strip()
    facts = [str(value).strip() for value in spec.get("facts", []) if str(value).strip()]
    cta = str((spec.get("cta") or {}).get("text") or "").strip()

    size_ratio = {
        "numeric_impact": 0.135,
        "short_power_word": 0.150,
        "concept_message": 0.115,
        "work_scene": 0.085,
        "benefit_stack": 0.108,
        "emotional_message": 0.105,
    }[family]
    min_ratio = {
        "numeric_impact": 0.068,
        "short_power_word": 0.072,
        "concept_message": 0.060,
        "work_scene": 0.050,
        "benefit_stack": 0.056,
        "emotional_message": 0.055,
    }[family]
    font, fitted_lines = _fit_manual_lines(
        draw,
        lines,
        bold_font_path,
        zone_w - 24,
        max_size=round(height * size_ratio),
        min_size=max(30, round(height * min_ratio)),
        max_lines=3,
    )

    line_gap = max(1, round(font.size * (0.00 if family in {"numeric_impact", "short_power_word"} else 0.05)))
    line_h = max(draw.textbbox((0, 0), "Hgあ", font=font)[3], font.size)
    headline_h = len(fitted_lines) * line_h + max(0, len(fitted_lines) - 1) * line_gap
    cursor_y = margin_y

    if decorations.get("accent_bar", True):
        _draw_accent_bar(draw, x, cursor_y + 2, max(headline_h, round(height * 0.09)), accent)
        text_x = x + max(22, round(width * 0.018))
    else:
        text_x = x

    if decorations.get("rays", False):
        _draw_rays(draw, text_x + max(30, font.size // 2), max(4, cursor_y - font.size // 3), accent, max(24, font.size // 2))

    if family == "emotional_message":
        quote_font = ImageFont.truetype(str(bold_font_path), size=max(40, round(height * 0.10)))
        draw.text((text_x - 2, cursor_y - round(quote_font.size * 0.28)), "“", font=quote_font, fill=(*accent, 118))
        cursor_y += max(8, round(height * 0.015))

    for line in fitted_lines:
        fill = (*accent_dark, 255) if family in {"concept_message", "emotional_message"} else dark
        emphasis_fill = (*accent, 255)
        stroke_width = max(0, round(font.size * 0.012)) if family == "short_power_word" else 0
        _draw_segmented_line(
            draw,
            (text_x, cursor_y),
            line,
            font,
            emphasis=emphasis,
            normal_fill=fill,
            emphasis_fill=emphasis_fill,
            stroke_width=stroke_width,
            stroke_fill=(255, 255, 255, 180) if stroke_width else None,
        )
        cursor_y += line_h + line_gap

    cursor_y += max(10, round(height * 0.018))
    cursor_y = _draw_subcopy(
        draw,
        subcopy,
        x=text_x if family != "work_scene" else x,
        y=cursor_y,
        max_width=zone_w,
        font_path=regular_font_path if family not in {"benefit_stack", "work_scene"} else bold_font_path,
        height=height,
        fill=muted,
        bold=family in {"benefit_stack", "work_scene"},
    )

    if family == "concept_message" and subcopy:
        band_y = cursor_y - max(5, round(height * 0.008))
        draw.line((text_x, band_y, text_x + round(zone_w * 0.55), band_y), fill=(*accent, 160), width=max(2, round(height * 0.004)))

    _draw_facts_and_cta(
        draw,
        facts=facts,
        cta=cta,
        x=x,
        max_width=zone_w,
        bottom_y=height - margin_y,
        bold_font_path=bold_font_path,
        accent=accent,
        height=height,
        family=family,
    )
    return image


def render_design_spec(image_path: Path, design_spec: dict, output_path: Path | None = None) -> Path:
    """Render exact Japanese copy using an AI-authored, validated design spec.

    Creative judgment lives in the design spec. Python only renders the approved
    hierarchy, semantic line breaks, emphasis, layout family, and decorations.
    """
    bold_font_path, regular_font_path = resolve_font_paths()
    output_path = output_path or image_path
    with Image.open(image_path) as source:
        image = source.convert("RGBA")
    image = _render_design_spec(
        image,
        design_spec,
        bold_font_path=bold_font_path,
        regular_font_path=regular_font_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, format="PNG", optimize=True)
    return output_path


def render_overlay(
    image_path: Path,
    overlay_text: Iterable[dict],
    output_path: Path | None = None,
    *,
    accent_color: str = "#E85A3D",
    design_style: str = "benchmark_recruit",
) -> Path:
    """Compatibility wrapper for older callers.

    New production flow should use render_design_spec(). This wrapper converts the
    old flat overlay items into a concept_message design spec.
    """
    style = (design_style or "benchmark_recruit").strip().lower()
    if style not in SUPPORTED_DESIGN_STYLES:
        raise ValueError(f"Unsupported design_style={design_style!r}")
    items = [dict(item) for item in overlay_text if str(item.get("text") or "").strip()]
    headline = next((item for item in items if item.get("role") == "main_copy"), {})
    subcopy = next((item for item in items if item.get("role") == "sub_copy"), {})
    facts = [str(item.get("text") or "").strip() for item in items if item.get("role") == "fact"]
    cta = next((item for item in items if item.get("role") == "cta"), {})
    text = str(headline.get("text") or "").strip()
    lines = headline.get("lines") or [line for line in text.splitlines() if line] or [text]
    spec = {
        "version": "compat",
        "layout_family": "concept_message",
        "accent_color": accent_color,
        "text_zone": "left",
        "headline": {
            "text": text,
            "lines": lines,
            "emphasis": headline.get("emphasis") or [],
        },
        "subcopy": {"text": str(subcopy.get("text") or "").strip()},
        "facts": facts[:3],
        "cta": {"text": str(cta.get("text") or "").strip()},
        "decorations": {"accent_bar": True, "rays": False, "soft_shape": True, "bottom_band": False},
    }
    return render_design_spec(image_path, spec, output_path)
