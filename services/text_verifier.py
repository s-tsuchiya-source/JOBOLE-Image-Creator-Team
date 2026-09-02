from __future__ import annotations

import json
import os
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path


NUMBER_RE = re.compile(r"(?:\d[\d,]*(?:\.\d+)?)(?:円|万円|万|時間|日|分|歳|％|%)?")


def normalize_for_compare(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    replacements = {
        "〜": "~",
        "～": "~",
        "−": "-",
        "―": "-",
        "‐": "-",
        "　": " ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", "", text).strip()


def extract_number_tokens(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    return [normalize_for_compare(match.group(0)) for match in NUMBER_RE.finditer(normalized)]


def compare_text_contract(spec: dict, observed_text: str) -> dict:
    observed_norm = normalize_for_compare(observed_text)
    results: list[dict] = []
    required_ok = True
    numeric_ok = True

    for block in spec.get("text_contract", []):
        expected = str(block.get("text") or "")
        expected_norm = normalize_for_compare(expected)
        required = bool(block.get("required", True))
        found = bool(expected_norm and expected_norm in observed_norm)
        similarity = SequenceMatcher(None, expected_norm, observed_norm).ratio() if expected_norm else 0.0
        missing_numbers = [
            token for token in extract_number_tokens(expected)
            if token and token not in observed_norm
        ]
        if required and not found:
            required_ok = False
        if missing_numbers:
            numeric_ok = False
        results.append(
            {
                "id": block.get("id"),
                "role": block.get("role"),
                "expected": expected,
                "required": required,
                "exact_normalized_substring_match": found,
                "similarity_to_full_observed": round(similarity, 4),
                "missing_number_tokens": missing_numbers,
            }
        )

    status = "pass" if required_ok and numeric_ok else "fail"
    return {
        "status": status,
        "required_text_pass": required_ok,
        "numeric_fact_pass": numeric_ok,
        "observed_text": observed_text,
        "blocks": results,
    }


def _pytesseract_available() -> tuple[bool, str]:
    try:
        import pytesseract  # type: ignore
    except Exception as exc:
        return False, f"pytesseract import failed: {exc}"

    configured = os.getenv("TESSERACT_CMD", "").strip()
    if configured:
        pytesseract.pytesseract.tesseract_cmd = configured
    try:
        version = str(pytesseract.get_tesseract_version())
    except Exception as exc:
        return False, f"tesseract executable unavailable: {exc}"
    return True, version


def run_local_ocr(image_path: Path, *, lang: str | None = None) -> dict:
    ok, detail = _pytesseract_available()
    if not ok:
        return {
            "status": "not_available",
            "engine": "tesseract",
            "detail": detail,
            "observed_text": "",
        }

    import pytesseract  # type: ignore
    from PIL import Image

    configured = os.getenv("TESSERACT_CMD", "").strip()
    if configured:
        pytesseract.pytesseract.tesseract_cmd = configured
    ocr_lang = lang or os.getenv("OCR_LANG", "jpn+eng")
    try:
        with Image.open(image_path) as image:
            text = pytesseract.image_to_string(image.convert("RGB"), lang=ocr_lang)
    except Exception as exc:
        return {
            "status": "error",
            "engine": "tesseract",
            "detail": str(exc),
            "observed_text": "",
        }
    return {
        "status": "ok",
        "engine": "tesseract",
        "detail": detail,
        "lang": ocr_lang,
        "observed_text": text,
    }


def verify_image_text(spec: dict, image_path: Path, *, observed_text: str | None = None) -> dict:
    if observed_text is not None:
        comparison = compare_text_contract(spec, observed_text)
        return {
            "verification_source": "provided_observed_text",
            **comparison,
        }

    ocr = run_local_ocr(image_path)
    if ocr["status"] != "ok":
        return {
            "status": "needs_visual_verification",
            "verification_source": "local_ocr_unavailable",
            "ocr": ocr,
            "required_text_pass": None,
            "numeric_fact_pass": None,
            "blocks": [],
        }

    comparison = compare_text_contract(spec, str(ocr.get("observed_text") or ""))
    return {
        "verification_source": "local_ocr",
        "ocr": ocr,
        **comparison,
    }


def write_verification(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8-sig")
