from __future__ import annotations

import os
from pathlib import Path
import sys

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from services.image_generator import check_image_backend, create_image_generator


LOCAL_BACKENDS = {
    "local",
    "local_webui",
    "webui",
    "forge",
    "automatic1111",
    "openvino",
    "openvino_ovms",
    "ovms",
    "intel",
}


def main() -> None:
    backend = os.getenv("IMAGE_BACKEND", "openvino_ovms").strip().lower()
    if backend not in LOCAL_BACKENDS:
        raise SystemExit(
            "このテストはローカル画像AI専用です。"
            "IMAGE_BACKEND=openvino_ovms または local_webui にしてください。"
        )

    print("Checking selected local image backend...")
    info = check_image_backend()
    if not info.get("ok"):
        raise SystemExit(f"Local image backend is not ready: {info}")

    output = REPO_ROOT / "tmp" / "local-image-test.png"
    generator = create_image_generator()
    provider = getattr(generator, "provider_name", backend)
    model = getattr(generator, "model", "")
    base_url = getattr(generator, "base_url", "")

    print(f"Image backend: {provider}")
    if base_url:
        print(f"Endpoint: {base_url}")
    if model:
        print(f"Model: {model}")
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
    print(f"Backend: {provider}")
    print(f"Output: {output}")
    print("Incremental cloud image API cost: 0 JPY")


if __name__ == "__main__":
    main()
