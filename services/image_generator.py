from __future__ import annotations

import base64
import io
import os
from pathlib import Path
import urllib.request

from PIL import Image, ImageOps


class OpenAIImageGenerator:
    def __init__(self, model: str | None = None, quality: str | None = None):
        from openai import OpenAI

        self.model = model or os.getenv("OPENAI_IMAGE_MODEL")
        self.quality = quality or os.getenv("OPENAI_IMAGE_QUALITY", "high")
        if not self.model:
            raise ValueError("OPENAI_IMAGE_MODEL is not configured.")
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is not configured.")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    @staticmethod
    def nearest_generation_size(width: int, height: int) -> str:
        ratio = width / height
        if ratio >= 1.2:
            return "1536x1024"
        if ratio <= 0.83:
            return "1024x1536"
        return "1024x1024"

    @staticmethod
    def _decode_image(item) -> bytes:
        b64_json = getattr(item, "b64_json", None)
        if b64_json:
            return base64.b64decode(b64_json)
        url = getattr(item, "url", None)
        if url:
            with urllib.request.urlopen(url, timeout=60) as response:
                return response.read()
        raise ValueError("Image API returned neither b64_json nor url.")

    def generate(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        generation_size = self.nearest_generation_size(width, height)
        response = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=generation_size,
            quality=self.quality,
            n=1,
        )
        raw = self._decode_image(response.data[0])
        with Image.open(io.BytesIO(raw)) as image:
            image = image.convert("RGB")
            final_image = ImageOps.fit(
                image,
                (width, height),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            final_image.save(output_path, format="PNG", optimize=True)
        return output_path


def parse_dimensions(format_value: str, width: str | int = "", height: str | int = "") -> tuple[int, int]:
    if str(width).isdigit() and str(height).isdigit():
        return int(width), int(height)
    normalized = (format_value or "").lower().replace("×", "x")
    if "x" not in normalized:
        raise ValueError(f"Cannot determine dimensions from format: {format_value!r}")
    left, right = normalized.split("x", 1)
    if not left.isdigit() or not right.isdigit():
        raise ValueError(f"Invalid dimensions: {format_value!r}")
    return int(left), int(right)
