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
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
]


def _resolve_font(config_key: str, fallback_key: str, candidates: list[str]) -> Path:
    configured = os.getenv(config_key) or os.getenv(fallback_key)
    if configured and Path(configured).exists():
        return Path(configured)
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Japanese font was not found. Set {config_key} or {fallback_key} in .env."
    )


def resolve_font_paths() -> tuple[Path, Path]:
    bold = _resolve_font("JAPANESE_BOLD_FONT_PATH", "JAPANESE_FONT_PATH", BOLD_FONT_CANDIDATES)
    regular = _resolve_font("JAPANESE_REGULAR_FONT_PATH", "JAPANESE_FONT_PATH", REGULAR_FONT_CANDIDATES)
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


def _add_left_readability_gradient(image: Image.Image, strength: int = 225) -> None:
    """Add a soft editorial text zone instead of many independent white boxes."""
    width, height = image.size
    panel_w = max(1, round(width * 0.62))
    overlay = Image.new("RGBA", (panel_w, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    fade_start = 0.62
    for x in range(panel_w):
        ratio = x / max(1, panel_w - 1)
        if ratio <= fade_start:
            alpha = strength
        else:
            progress = (ratio - fade_start) / (1.0 - fade_start)
            alpha = round(strength * (1.0 - progress))
        draw.line((x, 0, x, height), fill=(255, 255, 255, max(0, alpha)))
    image.alpha_composite(overlay, (0, 0))


def render_overlay(
    image_path: Path,
    overlay_text: Iterable[dict],
    output_path: Path | None = None,
    *,
    accent_color: str = "#E84C4C",
    design_style: str = "modern_recruit",
) -> Path:
    """Render exact Japanese recruitment-ad copy with visual hierarchy.

    Required Japanese text is never delegated to the image model. The default
    design uses one coherent editorial text zone, a strong headline, restrained
    subcopy, benefit chips, and a distinct CTA instead of repeating identical
    white labels for every piece of text.
    """
    bold_font_path, regular_font_path = resolve_font_paths()
    output_path = output_path or image_path

    with Image.open(image_path) as source:
        image = source.convert("RGBA")

    style = (design_style or "modern_recruit").strip().lower()
    if style not in {"modern_recruit", "clean_recruit"}:
        raise ValueError(f"Unsupported design_style={design_style!r}")

    _add_left_readability_gradient(image)
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    margin_x = max(30, round(width * 0.035))
    margin_y = max(28, round(height * 0.055))
    content_w = round(width * 0.49)
    accent = _hex_rgb(accent_color)
    accent_light = _blend_with_white(accent, 0.90)
    dark = (27, 29, 32, 255)
    muted = (72, 76, 82, 255)

    items = [dict(item) for item in overlay_text if str(item.get("text") or "").strip()]
    headline = next((item for item in items if item.get("role") == "main_copy"), None)
    subcopy = next((item for item in items if item.get("role") == "sub_copy"), None)
    facts = [item for item in items if item.get("role") == "fact"]
    cta = next((item for item in items if item.get("role") == "cta"), None)

    # Headline zone ---------------------------------------------------------
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

    # Subcopy zone ----------------------------------------------------------
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

    # Bottom benefit / action zone -----------------------------------------
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
        # Subtle shadow gives the CTA a button-like, less mechanical finish.
        draw.rounded_rectangle(
            (margin_x + 2, y + 4, margin_x + box_w + 2, y + box_h + 4),
            radius=max(10, box_h // 3),
            fill=(0, 0, 0, 32),
        )
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

    # Facts become benefit chips, visually different from headline and CTA.
    for item in reversed(facts):
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, format="PNG", optimize=True)
    return output_path
