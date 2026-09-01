from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


WINDOWS_FONT_CANDIDATES = [
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
]


def resolve_font_path() -> Path:
    configured = os.getenv("JAPANESE_FONT_PATH")
    if configured and Path(configured).exists():
        return Path(configured)
    for candidate in WINDOWS_FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return path
    raise FileNotFoundError(
        "Japanese font was not found. Set JAPANESE_FONT_PATH in .env."
    )


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
    """Greedy character wrapping that works reliably for Japanese text.

    Visual line breaks may be inserted, but no characters are changed or removed.
    Explicit line breaks are handled by _wrap_text.
    """
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


def _position(
    name: str,
    canvas_w: int,
    canvas_h: int,
    box_w: int,
    box_h: int,
    margin: int,
) -> tuple[int, int]:
    normalized = (name or "").lower().replace("-", "_").replace(" ", "_")
    horizontal = "left"
    vertical = "center"
    if "right" in normalized:
        horizontal = "right"
    elif "center" in normalized or "centre" in normalized:
        horizontal = "center"
    if "top" in normalized or "upper" in normalized:
        vertical = "top"
    elif "bottom" in normalized or "lower" in normalized:
        vertical = "bottom"

    if horizontal == "left":
        x = margin
    elif horizontal == "right":
        x = canvas_w - box_w - margin
    else:
        x = (canvas_w - box_w) // 2

    if vertical == "top":
        y = margin
    elif vertical == "bottom":
        y = canvas_h - box_h - margin
    else:
        y = (canvas_h - box_h) // 2
    return max(margin, x), max(margin, y)


def render_overlay(
    image_path: Path,
    overlay_text: Iterable[dict],
    output_path: Path | None = None,
) -> Path:
    """Render exact Japanese copy after image generation.

    The image model is not trusted to render required Japanese text. This
    renderer uses an installed Japanese font, preserves every source character,
    adds visual wrapping where needed, and prioritizes deterministic readability.
    """
    font_path = resolve_font_path()
    output_path = output_path or image_path

    with Image.open(image_path) as source:
        image = source.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    margin = max(24, round(min(width, height) * 0.045))
    max_text_width = round(width * 0.58)

    role_sizes = {
        "main_copy": round(height * 0.095),
        "sub_copy": round(height * 0.050),
        "fact": round(height * 0.045),
        "cta": round(height * 0.042),
        "brand": round(height * 0.032),
    }
    role_max_lines = {
        "main_copy": 3,
        "sub_copy": 3,
        "fact": 2,
        "cta": 2,
        "brand": 2,
    }
    default_positions = {
        "main_copy": "top_left",
        "sub_copy": "top_left",
        "fact": "bottom_left",
        "cta": "bottom_left",
        "brand": "bottom_right",
    }

    top_cursor: dict[str, int] = {}
    bottom_cursor: dict[str, int] = {}

    for item in overlay_text:
        original_text = str(item.get("text") or "").strip()
        if not original_text:
            continue

        role = str(item.get("role") or "fact")
        placement = str(item.get("placement") or default_positions.get(role, "top_left"))
        max_size = max(22, role_sizes.get(role, round(height * 0.04)))
        font, display_text = _fit_font_and_text(
            draw,
            original_text,
            font_path,
            max_text_width,
            max_size,
            max_lines=role_max_lines.get(role, 3),
        )

        stroke = max(1, font.size // 28)
        spacing = max(4, font.size // 7)
        bbox = draw.multiline_textbbox(
            (0, 0),
            display_text,
            font=font,
            spacing=spacing,
            stroke_width=stroke,
        )
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pad_x = max(10, font.size // 4)
        pad_y = max(8, font.size // 5)
        box_w = text_w + pad_x * 2
        box_h = text_h + pad_y * 2
        x, y = _position(placement, width, height, box_w, box_h, margin)

        anchor_key = placement.lower()
        gap = max(8, font.size // 5)
        if "top" in anchor_key or "upper" in anchor_key:
            if anchor_key in top_cursor:
                y = top_cursor[anchor_key] + gap
            top_cursor[anchor_key] = y + box_h
        elif "bottom" in anchor_key or "lower" in anchor_key:
            if anchor_key in bottom_cursor:
                y = bottom_cursor[anchor_key] - box_h - gap
            bottom_cursor[anchor_key] = y

        y = max(margin, min(y, height - box_h - margin))
        x = max(margin, min(x, width - box_w - margin))

        draw.rounded_rectangle(
            (x, y, x + box_w, y + box_h),
            radius=max(6, font.size // 5),
            fill=(255, 255, 255, 218),
        )
        draw.multiline_text(
            (x + pad_x, y + pad_y - bbox[1]),
            display_text,
            font=font,
            fill=(30, 30, 30, 255),
            spacing=spacing,
            stroke_width=stroke,
            stroke_fill=(255, 255, 255, 200),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, format="PNG", optimize=True)
    return output_path
