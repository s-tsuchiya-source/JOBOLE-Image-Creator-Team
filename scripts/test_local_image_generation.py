from __future__ import annotations

import os
from pathlib import Path
import sys

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from services.image_generator import LocalWebUIImageGenerator


def main() -> None:
    backend = os.getenv("IMAGE_BACKEND", "local_webui").strip().lower()
    if backend not in {"local", "local_webui", "webui", "forge", "automatic1111"}:
        raise SystemExit(
            "このテストはローカル画像AI専用です。.env を IMAGE_BACKEND=local_webui にしてください。"
        )

    output = REPO_ROOT / "tmp" / "local-image-test.png"
    generator = LocalWebUIImageGenerator()
    print(f"Local WebUI: {generator.base_url}")
    print("512x512 のローカル画像を1枚生成します。クラウド画像API料金は発生しません。")
    generator.generate(
        prompt=(
            "clean professional Japanese recruitment advertising background, "
            "bright modern office, friendly young professional, natural realistic photo, "
            "clear empty space on the left for Japanese headline, commercial advertising composition"
        ),
        negative_prompt=(
            "text, letters, logo, watermark, distorted hands, extra fingers, low quality, blurry"
        ),
        width=512,
        height=512,
        output_path=output,
    )
    print("LOCAL IMAGE GENERATION: PASS")
    print(f"Output: {output}")
    print("Incremental cloud image API cost: 0 JPY")


if __name__ == "__main__":
    main()
