from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from PIL import Image, ImageOps


def _fit_and_save(raw: bytes, *, width: int, height: int, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
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


def _multiple_of_8(value: int) -> int:
    return max(64, int(round(value / 8.0) * 8))


def _scaled_local_dimensions(width: int, height: int, max_side: int) -> tuple[int, int]:
    if max(width, height) <= max_side:
        return _multiple_of_8(width), _multiple_of_8(height)
    scale = max_side / max(width, height)
    return (
        _multiple_of_8(max(64, int(width * scale))),
        _multiple_of_8(max(64, int(height * scale))),
    )


def _http_json(
    url: str,
    *,
    payload: dict | None = None,
    timeout: int = 600,
) -> dict | list:
    data = None
    method = "GET"
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Local image endpoint is not reachable: {url}. Error: {exc}") from exc


class OpenAIImageGenerator:
    provider_name = "openai_image_api"

    def __init__(self, model: str | None = None, quality: str | None = None):
        from openai import OpenAI

        self.model = model or os.getenv("OPENAI_IMAGE_MODEL")
        self.quality = quality or os.getenv("OPENAI_IMAGE_QUALITY", "high")
        if not self.model:
            raise ValueError("OPENAI_IMAGE_MODEL is not configured.")
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is required only when IMAGE_BACKEND=openai.")
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
        negative_prompt: str = "",
    ) -> Path:
        del negative_prompt
        generation_size = self.nearest_generation_size(width, height)
        response = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=generation_size,
            quality=self.quality,
            n=1,
        )
        raw = self._decode_image(response.data[0])
        return _fit_and_save(raw, width=width, height=height, output_path=output_path)


class LocalWebUIImageGenerator:
    """AUTOMATIC1111 / Forge compatible local txt2img backend."""

    provider_name = "local_webui"

    def __init__(self):
        self.base_url = os.getenv("LOCAL_IMAGE_API_URL", "http://127.0.0.1:7860").rstrip("/")
        self.model = os.getenv("LOCAL_IMAGE_MODEL", "local-loaded-checkpoint")
        self.steps = int(os.getenv("LOCAL_IMAGE_STEPS", "28"))
        self.cfg_scale = float(os.getenv("LOCAL_IMAGE_CFG_SCALE", "6.5"))
        self.sampler_name = os.getenv("LOCAL_IMAGE_SAMPLER", "DPM++ 2M")
        self.timeout_seconds = int(os.getenv("LOCAL_IMAGE_TIMEOUT_SEC", "600"))
        self.max_side = int(os.getenv("LOCAL_IMAGE_MAX_SIDE", "1024"))
        if self.max_side < 512:
            raise ValueError("LOCAL_IMAGE_MAX_SIDE must be at least 512.")

    def healthcheck(self) -> dict:
        options = _http_json(
            self.base_url + "/sdapi/v1/options",
            timeout=self.timeout_seconds,
        )
        models = _http_json(
            self.base_url + "/sdapi/v1/sd-models",
            timeout=self.timeout_seconds,
        )
        current_model = ""
        if isinstance(options, dict):
            current_model = str(options.get("sd_model_checkpoint") or "")
        return {
            "ok": True,
            "base_url": self.base_url,
            "current_model": current_model,
            "available_models": len(models) if isinstance(models, list) else None,
            "max_generation_side": self.max_side,
        }

    def generate(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        output_path: Path,
        negative_prompt: str = "",
    ) -> Path:
        gen_width, gen_height = _scaled_local_dimensions(width, height, self.max_side)
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": gen_width,
            "height": gen_height,
            "steps": self.steps,
            "cfg_scale": self.cfg_scale,
            "sampler_name": self.sampler_name,
            "batch_size": 1,
            "n_iter": 1,
            "send_images": True,
            "save_images": False,
        }
        result = _http_json(
            self.base_url + "/sdapi/v1/txt2img",
            payload=payload,
            timeout=self.timeout_seconds,
        )
        if not isinstance(result, dict) or not result.get("images"):
            raise RuntimeError("Local WebUI returned no generated image.")
        encoded = str(result["images"][0])
        if "," in encoded:
            encoded = encoded.split(",", 1)[1]
        raw = base64.b64decode(encoded)
        return _fit_and_save(raw, width=width, height=height, output_path=output_path)


class OpenVINOOVMSImageGenerator:
    """Intel-friendly local image backend through OpenVINO Model Server.

    OVMS exposes an OpenAI-compatible image-generation endpoint locally. The
    model is served on the user's own Intel CPU/GPU, so there is no per-image API
    charge. For low-memory integrated GPUs the first-test default is 512x512.
    """

    provider_name = "openvino_ovms"

    def __init__(self):
        self.base_url = os.getenv("OPENVINO_IMAGE_API_URL", "http://127.0.0.1:8000").rstrip("/")
        self.model = os.getenv(
            "OPENVINO_IMAGE_MODEL",
            "OpenVINO/stable-diffusion-v1-5-int8-ov",
        )
        self.steps = int(os.getenv("OPENVINO_IMAGE_STEPS", "10"))
        self.timeout_seconds = int(os.getenv("OPENVINO_IMAGE_TIMEOUT_SEC", "1200"))
        self.generation_size = os.getenv("OPENVINO_IMAGE_GENERATION_SIZE", "512x512")
        if "x" not in self.generation_size.lower():
            raise ValueError("OPENVINO_IMAGE_GENERATION_SIZE must look like 512x512.")

    def healthcheck(self) -> dict:
        result = _http_json(
            self.base_url + "/v3/models",
            timeout=min(self.timeout_seconds, 30),
        )
        model_ids: list[str] = []
        if isinstance(result, dict):
            for item in result.get("data") or []:
                if isinstance(item, dict) and item.get("id"):
                    model_ids.append(str(item["id"]))
        return {
            "ok": True,
            "base_url": self.base_url,
            "configured_model": self.model,
            "available_models": model_ids,
            "model_visible": self.model in model_ids if model_ids else None,
            "generation_size": self.generation_size,
        }

    def generate(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        output_path: Path,
        negative_prompt: str = "",
    ) -> Path:
        full_prompt = prompt
        if negative_prompt.strip():
            full_prompt += "\n\nAvoid: " + negative_prompt.strip()
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "num_inference_steps": self.steps,
            "size": self.generation_size,
        }
        result = _http_json(
            self.base_url + "/v3/images/generations",
            payload=payload,
            timeout=self.timeout_seconds,
        )
        if not isinstance(result, dict) or not result.get("data"):
            raise RuntimeError("OpenVINO Model Server returned no generated image.")
        item = result["data"][0]
        if not isinstance(item, dict) or not item.get("b64_json"):
            raise RuntimeError("OpenVINO Model Server response did not include b64_json.")
        raw = base64.b64decode(str(item["b64_json"]))
        return _fit_and_save(raw, width=width, height=height, output_path=output_path)


def create_image_generator():
    backend = os.getenv("IMAGE_BACKEND", "openvino_ovms").strip().lower()
    if backend in {"local", "local_webui", "webui", "forge", "automatic1111"}:
        return LocalWebUIImageGenerator()
    if backend in {"openvino", "openvino_ovms", "ovms", "intel_openvino"}:
        return OpenVINOOVMSImageGenerator()
    if backend in {"openai", "openai_api"}:
        return OpenAIImageGenerator()
    raise ValueError(
        f"Unsupported IMAGE_BACKEND={backend!r}. Use openvino_ovms, local_webui, or openai."
    )


def check_image_backend() -> dict:
    generator = create_image_generator()
    if isinstance(generator, LocalWebUIImageGenerator):
        return {
            "backend": "local_webui",
            **generator.healthcheck(),
            "incremental_cost_yen": 0.0,
        }
    if isinstance(generator, OpenVINOOVMSImageGenerator):
        return {
            "backend": "openvino_ovms",
            **generator.healthcheck(),
            "incremental_cost_yen": 0.0,
        }
    return {
        "backend": "openai",
        "ok": bool(os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_IMAGE_MODEL")),
        "model": generator.model,
        "incremental_cost_yen": "usage_based",
    }


def parse_dimensions(
    format_value: str,
    width: str | int = "",
    height: str | int = "",
) -> tuple[int, int]:
    if str(width).isdigit() and str(height).isdigit():
        return int(width), int(height)
    normalized = (format_value or "").lower().replace("×", "x")
    if "x" not in normalized:
        raise ValueError(f"Cannot determine dimensions from format: {format_value!r}")
    left, right = normalized.split("x", 1)
    if not left.isdigit() or not right.isdigit():
        raise ValueError(f"Invalid dimensions: {format_value!r}")
    return int(left), int(right)
