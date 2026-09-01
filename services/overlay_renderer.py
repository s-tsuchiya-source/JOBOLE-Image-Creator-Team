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


def _font(draw: ImageDraw.ImageDraw, text: str, font_path: Path, max_width: int, max_size: int, min_size: int = 20):
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(str(font_path), size=size)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=0)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return ImageFont.truetype(str(font_path), size=min_size)


def _position(name: str, canvas_w: int, canvas_h: int, box_w: int, box_h: int, margin: int) -> tuple[int, int]:
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

    This is deliberately conservative. It preserves exact text and uses role-based
    hierarchy. Brand-specific typography can later replace this renderer without
    changing the upstream Prompt Package contract.
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
    default_positions = {
        "main_copy": "top_left",
        "sub_copy": "top_left",
        "fact": "bottom_left",
        "cta": "bottom_left",
        "brand": "bottom_right",
    }

    cursor_by_anchor: dict[str, int] = {}
    for item in overlay_text:
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        role = str(item.get("role") or "fact")
        placement = str(item.get("placement") or default_positions.get(role, "top_left"))
        max_size = max(22, role_sizes.get(role, round(height * 0.04)))
        font = _font(draw, text, font_path, max_text_width, max_size)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=max(1, font.size // 28))
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pad_x = max(10, font.size // 4)
        pad_y = max(8, font.size // 5)
        box_w = text_w + pad_x * 2
        box_h = text_h + pad_y * 2
        x, y = _position(placement, width, height, box_w, box_h, margin)

        anchor_key = placement.lower()
        prior_y = cursor_by_anchor.get(anchor_key)
        if prior_y is not None and ("top" in anchor_key or "upper" in anchor_key):
            y = prior_y + max(8, font.size // 5)
        cursor_by_anchor[anchor_key] = y + box_h

        # Subtle contrast plate for deterministic readability. Brand-specific rendering
        # can disable or replace this in a later template layer.
        draw.rounded_rectangle(
            (x, y, x + box_w, y + box_h),
            radius=max(6, font.size // 5),
            fill=(255, 255, 255, 218),
        )
        stroke = max(1, font.size // 28)
        draw.text(
            (x + pad_x, y + pad_y - bbox[1]),
            text,
            font=font,
            fill=(30, 30, 30, 255),
            stroke_width=stroke,
            stroke_fill=(255, 255, 255, 200),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, format="PNG", optimize=True)
    return output_path
