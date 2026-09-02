from __future__ import annotations

import os
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
        raise FileNotFoundError(
            "Japanese bold font was not found. Set JAPANESE_BOLD_FONT_PATH or JAPANESE_FONT_PATH in .env."
        )
    if not regular:
        raise FileNotFoundError(
            "Japanese regular font was not found. Set JAPANESE_REGULAR_FONT_PATH or JAPANESE_FONT_PATH in .env."
        )
    return bold, regular


def _line_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    if not text:
        return 0
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _wrap_one_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    if not text:
        return [""]
    if _line_width(draw, text, font) <= max_width:
        return [text]
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and _line_width(draw, candidate, font) > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [text]


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> str:
    wrapped: list[str] = []
    for explicit_line in text.splitlines() or [text]:
        wrapped.extend(_wrap_one_line(draw, explicit_line, font, max_width))
    return "\n".join(wrapped)


def _fit_font_and_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Path,
    max_width: int,
    max_size: int,
    *,
    max_lines: int,
    min_size: int = 20,
) -> tuple[ImageFont.FreeTypeFont, str]:
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(str(font_path), size=size)
        wrapped = _wrap_text(draw, text, font, max_width)
        if len(wrapped.splitlines()) <= max_lines:
            return font, wrapped
    font = ImageFont.truetype(str(font_path), size=min_size)
    return font, _wrap_text(draw, text, font, max_width)


def _hex_rgb(value: str) -> tuple[int, int, int]:
    try:
        return ImageColor.getrgb(value)
    except ValueError as exc:
        raise ValueError(f"Invalid accent color: {value}") from exc


def _blend_with_white(rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(channel + (255 - channel) * amount) for channel in rgb)


def _add_left_readability_gradient(image: Image.Image, strength: int = 220, width_ratio: float = 0.60) -> None:
    width, height = image.size
    panel_w = max(1, round(width * width_ratio))
    overlay = Image.new("RGBA", (panel_w, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    fade_start = 0.58
    for x in range(panel_w):
        ratio = x / max(1, panel_w - 1)
        if ratio <= fade_start:
            alpha = strength
        else:
            progress = (ratio - fade_start) / (1.0 - fade_start)
            alpha = round(strength * (1.0 - progress))
        draw.line((x, 0, x, height), fill=(255, 255, 255, max(0, alpha)))
    image.alpha_composite(overlay, (0, 0))


def _split_items(overlay_text: Iterable[dict]) -> tuple[dict | None, dict | None, list[dict], dict | None]:
    items = [dict(item) for item in overlay_text if str(item.get("text") or "").strip()]
    headline = next((item for item in items if item.get("role") == "main_copy"), None)
    subcopy = next((item for item in items if item.get("role") == "sub_copy"), None)
    facts = [item for item in items if item.get("role") == "fact"]
    cta = next((item for item in items if item.get("role") == "cta"), None)
    return headline, subcopy, facts, cta


def _draw_benchmark_rays(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    accent: tuple[int, int, int],
    scale: int,
) -> None:
    stroke = max(2, scale // 12)
    rays = [
        ((x, y + scale), (x - scale // 3, y + scale // 2)),
        ((x + scale // 3, y + scale * 3 // 4), (x + scale // 4, y + scale // 4)),
        ((x + scale * 2 // 3, y + scale * 3 // 4), (x + scale * 3 // 4, y + scale // 4)),
        ((x + scale, y + scale), (x + scale * 4 // 3, y + scale // 2)),
    ]
    for start, end in rays:
        draw.line((*start, *end), fill=(*accent, 220), width=stroke)


def _render_benchmark_recruit(
    image: Image.Image,
    overlay_text: Iterable[dict],
    *,
    bold_font_path: Path,
    regular_font_path: Path,
    accent_color: str,
) -> Image.Image:
    """Photo-led recruitment-ad typography inspired by the benchmark sample grammar.

    This renderer intentionally avoids dashboard-like cards. It uses a large display
    headline, one dominant accent color, restrained decorative rays, an optional
    supporting ribbon, and only a few secondary facts.
    """
    _add_left_readability_gradient(image, strength=208, width_ratio=0.59)
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    accent = _hex_rgb(accent_color)
    accent_dark = tuple(max(0, c - 30) for c in accent)
    accent_light = _blend_with_white(accent, 0.90)
    dark = (30, 30, 32, 255)

    headline, subcopy, facts, cta = _split_items(overlay_text)
    margin_x = max(30, round(width * 0.035))
    margin_y = max(28, round(height * 0.05))
    content_w = round(width * 0.51)
    cursor_y = margin_y

    if headline:
        text = str(headline.get("text") or "").strip()
        font, display_text = _fit_font_and_text(
            draw,
            text,
            bold_font_path,
            content_w,
            max_size=round(height * 0.145),
            max_lines=3,
            min_size=max(34, round(height * 0.070)),
        )
        spacing = max(2, round(font.size * 0.03))
        bbox = draw.multiline_textbbox((0, 0), display_text, font=font, spacing=spacing, stroke_width=1)
        text_h = bbox[3] - bbox[1]

        _draw_benchmark_rays(
            draw,
            margin_x + max(35, round(font.size * 0.55)),
            max(4, cursor_y - round(font.size * 0.25)),
            accent,
            max(24, round(font.size * 0.50)),
        )
        draw.multiline_text(
            (margin_x, cursor_y - bbox[1]),
            display_text,
            font=font,
            fill=(*accent_dark, 255),
            spacing=spacing,
            stroke_width=max(1, round(font.size * 0.025)),
            stroke_fill=(255, 255, 255, 215),
        )
        cursor_y += text_h + max(14, round(font.size * 0.13))

    if subcopy:
        text = str(subcopy.get("text") or "").strip()
        font, display_text = _fit_font_and_text(
            draw,
            text,
            bold_font_path,
            content_w - 18,
            max_size=round(height * 0.050),
            max_lines=2,
            min_size=max(20, round(height * 0.032)),
        )
        spacing = max(2, round(font.size * 0.08))
        bbox = draw.multiline_textbbox((0, 0), display_text, font=font, spacing=spacing)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x = max(18, round(font.size * 0.55))
        pad_y = max(7, round(font.size * 0.20))
        band_w = min(content_w, tw + pad_x * 2)
        band_h = th + pad_y * 2
        skew = max(8, round(band_h * 0.18))
        polygon = [
            (margin_x + skew, cursor_y),
            (margin_x + band_w, cursor_y),
            (margin_x + band_w - skew, cursor_y + band_h),
            (margin_x, cursor_y + band_h),
        ]
        draw.polygon(polygon, fill=(*accent, 238))
        draw.multiline_text(
            (margin_x + pad_x, cursor_y + pad_y - bbox[1]),
            display_text,
            font=font,
            fill=(255, 255, 255, 255),
            spacing=spacing,
        )
        cursor_y += band_h + max(10, round(height * 0.014))

    bottom_y = height - margin_y
    fact_font = ImageFont.truetype(str(bold_font_path), size=max(18, round(height * 0.032)))
    fact_gap = max(7, round(height * 0.010))

    if cta:
        text = str(cta.get("text") or "").strip()
        cta_font = ImageFont.truetype(str(bold_font_path), size=max(20, round(height * 0.034)))
        bbox = draw.textbbox((0, 0), text, font=cta_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x = max(18, round(cta_font.size * 0.55))
        pad_y = max(8, round(cta_font.size * 0.24))
        box_w = tw + pad_x * 2
        box_h = th + pad_y * 2
        y = bottom_y - box_h
        draw.rounded_rectangle(
            (margin_x, y, margin_x + box_w, y + box_h),
            radius=max(8, box_h // 3),
            fill=(*accent, 255),
        )
        draw.text(
            (margin_x + pad_x, y + pad_y - bbox[1]),
            text,
            font=cta_font,
            fill=(255, 255, 255, 255),
        )
        bottom_y = y - fact_gap

    for item in reversed(facts[:3]):
        text = str(item.get("text") or "").strip()
        wrapped = _wrap_text(draw, text, fact_font, content_w - 32)
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=fact_font, spacing=2)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x = max(13, round(fact_font.size * 0.42))
        pad_y = max(6, round(fact_font.size * 0.20))
        box_w = min(content_w, tw + pad_x * 2)
        box_h = th + pad_y * 2
        y = bottom_y - box_h
        draw.rounded_rectangle(
            (margin_x, y, margin_x + box_w, y + box_h),
            radius=max(7, box_h // 2),
            fill=(255, 255, 255, 225),
            outline=(*accent, 225),
            width=max(2, round(height * 0.0025)),
        )
        draw.multiline_text(
            (margin_x + pad_x, y + pad_y - bbox[1]),
            wrapped,
            font=fact_font,
            fill=dark,
            spacing=2,
        )
        bottom_y = y - fact_gap

    return image


def _render_modern_recruit(
    image: Image.Image,
    overlay_text: Iterable[dict],
    *,
    bold_font_path: Path,
    regular_font_path: Path,
    accent_color: str,
) -> Image.Image:
    _add_left_readability_gradient(image, strength=225, width_ratio=0.62)
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    margin_x = max(30, round(width * 0.035))
    margin_y = max(28, round(height * 0.055))
    content_w = round(width * 0.49)
    accent = _hex_rgb(accent_color)
    accent_light = _blend_with_white(accent, 0.90)
    dark = (27, 29, 32, 255)
    muted = (72, 76, 82, 255)

    headline, subcopy, facts, cta = _split_items(overlay_text)
    cursor_y = margin_y

    if headline:
        text = str(headline.get("text") or "").strip()
        font, display_text = _fit_font_and_text(
            draw,
            text,
            bold_font_path,
            content_w - 30,
            max_size=round(height * 0.105),
            max_lines=3,
            min_size=max(26, round(height * 0.052)),
        )
        spacing = max(4, round(font.size * 0.12))
        bbox = draw.multiline_textbbox((0, 0), display_text, font=font, spacing=spacing)
        text_h = bbox[3] - bbox[1]
        bar_w = max(7, round(font.size * 0.10))
        bar_gap = max(14, round(font.size * 0.22))
        draw.rounded_rectangle(
            (margin_x, cursor_y + 3, margin_x + bar_w, cursor_y + text_h - 2),
            radius=max(2, bar_w // 2),
            fill=(*accent, 255),
        )
        tx = margin_x + bar_w + bar_gap
        draw.multiline_text(
            (tx, cursor_y - bbox[1]),
            display_text,
            font=font,
            fill=dark,
            spacing=spacing,
        )
        cursor_y += text_h + max(16, round(font.size * 0.24))

    if subcopy:
        text = str(subcopy.get("text") or "").strip()
        font, display_text = _fit_font_and_text(
            draw,
            text,
            regular_font_path,
            content_w,
            max_size=round(height * 0.047),
            max_lines=3,
            min_size=max(20, round(height * 0.032)),
        )
        spacing = max(3, round(font.size * 0.18))
        bbox = draw.multiline_textbbox((0, 0), display_text, font=font, spacing=spacing)
        draw.multiline_text(
            (margin_x, cursor_y - bbox[1]),
            display_text,
            font=font,
            fill=muted,
            spacing=spacing,
        )

    bottom_y = height - margin_y
    if cta:
        text = str(cta.get("text") or "").strip()
        font = ImageFont.truetype(str(bold_font_path), size=max(22, round(height * 0.038)))
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x = max(18, round(font.size * 0.62))
        pad_y = max(10, round(font.size * 0.34))
        box_w = tw + pad_x * 2
        box_h = th + pad_y * 2
        y = bottom_y - box_h
        draw.rounded_rectangle(
            (margin_x, y, margin_x + box_w, y + box_h),
            radius=max(10, box_h // 3),
            fill=(*accent, 255),
        )
        draw.text(
            (margin_x + pad_x, y + pad_y - bbox[1]),
            text,
            font=font,
            fill=(255, 255, 255, 255),
        )
        bottom_y = y - max(12, round(height * 0.018))

    for item in reversed(facts[:3]):
        text = str(item.get("text") or "").strip()
        font, display_text = _fit_font_and_text(
            draw,
            text,
            bold_font_path,
            content_w - 30,
            max_size=round(height * 0.037),
            max_lines=2,
            min_size=max(18, round(height * 0.028)),
        )
        spacing = max(3, round(font.size * 0.10))
        bbox = draw.multiline_textbbox((0, 0), display_text, font=font, spacing=spacing)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x = max(14, round(font.size * 0.48))
        pad_y = max(8, round(font.size * 0.27))
        box_w = min(content_w, tw + pad_x * 2)
        box_h = th + pad_y * 2
        y = bottom_y - box_h
        draw.rounded_rectangle(
            (margin_x, y, margin_x + box_w, y + box_h),
            radius=max(8, box_h // 3),
            fill=(*accent_light, 238),
            outline=(*accent, 210),
            width=max(2, round(height * 0.003)),
        )
        draw.multiline_text(
            (margin_x + pad_x, y + pad_y - bbox[1]),
            display_text,
            font=font,
            fill=dark,
            spacing=spacing,
        )
        bottom_y = y - max(8, round(height * 0.012))

    return image


def render_overlay(
    image_path: Path,
    overlay_text: Iterable[dict],
    output_path: Path | None = None,
    *,
    accent_color: str = "#E84C4C",
    design_style: str = "benchmark_recruit",
) -> Path:
    """Render exact Japanese recruitment-ad copy with deterministic typography."""
    bold_font_path, regular_font_path = resolve_font_paths()
    output_path = output_path or image_path

    with Image.open(image_path) as source:
        image = source.convert("RGBA")

    style = (design_style or "benchmark_recruit").strip().lower()
    if style == "benchmark_recruit":
        image = _render_benchmark_recruit(
            image,
            overlay_text,
            bold_font_path=bold_font_path,
            regular_font_path=regular_font_path,
            accent_color=accent_color,
        )
    elif style in {"modern_recruit", "clean_recruit"}:
        image = _render_modern_recruit(
            image,
            overlay_text,
            bold_font_path=bold_font_path,
            regular_font_path=regular_font_path,
            accent_color=accent_color,
        )
    else:
        raise ValueError(f"Unsupported design_style={design_style!r}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, format="PNG", optimize=True)
    return output_path
