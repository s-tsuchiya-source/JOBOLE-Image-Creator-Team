"""Adobe material discovery and selection contract; never generates an image."""
from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path

import yaml
from PIL import Image


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif",
                    ".avif", ".heic", ".psd", ".eps", ".ai", ".svg"}


class AssetSelectionError(ValueError):
    pass


def resolve_adobe_root() -> Path:
    configured = os.getenv("ADOBE_IMAGE_ROOT", "").strip()
    if not configured:
        config_path = Path(__file__).resolve().parents[1] / "configs" / "workflow.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        configured = config["workflow"]["production_asset_library"]["default_path"]
    return Path(configured)


def adobe_catalog(root: Path) -> dict:
    """Do not confuse failed or partial discovery with an empty library."""
    items: list[dict] = []
    errors: list[str] = []
    try:
        if not root.is_dir():
            raise FileNotFoundError(f"Adobe image directory unavailable: {root}")
        paths: list[Path] = []
        for folder, _, names in os.walk(root, onerror=lambda exc: errors.append(str(exc))):
            paths.extend(Path(folder) / name for name in names if Path(name).suffix.lower() in IMAGE_EXTENSIONS)
        for index, path in enumerate(sorted(paths), start=1):
            item = {
                "asset_id": f"A{index:04d}",
                "relative_path": path.relative_to(root).as_posix(),
                "absolute_path": str(path),
            }
            try:
                with Image.open(path) as source:
                    source.load()
                    item.update(width=source.width, height=source.height, readable=True)
            except Exception as exc:
                item.update(readable=False, error=str(exc))
                errors.append(f"Could not inspect {path}: {exc}")
            items.append(item)
    except OSError as exc:
        errors.append(str(exc))
    return {
        "root": str(root),
        "policy": "adobe_first",
        "usage_authorized_by_user": True,
        "status": ("partial" if items else "unavailable") if errors else "available",
        "count": len(items),
        "items": items,
        "errors": errors,
    }


def normalize_asset_source(raw: object) -> dict:
    # Old specs remain readable for review, but cannot authorize new generation.
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise AssetSelectionError("asset_source must be an object")
    source = deepcopy(raw)
    source.setdefault("policy", "adobe_first")
    if "library_root" not in source:
        source["library_root"] = str(resolve_adobe_root())
    source.setdefault("search_status", "pending")
    source.setdefault("mode", "pending")
    source.setdefault("selected_assets", [])
    source.setdefault("search_summary", "")
    source.setdefault("fallback_reason", "")
    if source["policy"] != "adobe_first":
        raise AssetSelectionError("asset_source.policy must be adobe_first")
    if source["search_status"] not in ("pending", "completed", "unavailable"):
        raise AssetSelectionError("unsupported asset_source.search_status")
    if source["mode"] not in ("pending", "adobe_stock", "generated"):
        raise AssetSelectionError("unsupported asset_source.mode")
    for key in ("library_root", "search_summary", "fallback_reason"):
        if not isinstance(source[key], str):
            raise AssetSelectionError(f"asset_source.{key} must be text")
    if not isinstance(source["selected_assets"], list):
        raise AssetSelectionError("asset_source.selected_assets must be a list")
    for asset in source["selected_assets"]:
        if not isinstance(asset, dict) or not all(
            isinstance(asset.get(key), str) and asset[key].strip() for key in ("path", "reason")
        ):
            raise AssetSelectionError("Each selected asset requires path and reason")
    return source


def require_asset_selection(source: dict, *, library: dict | None = None) -> None:
    source = normalize_asset_source(source)
    if source["search_status"] == "unavailable":
        raise AssetSelectionError("ADOBE_ASSET_LIBRARY_UNAVAILABLE: restore access before selection")
    if source["search_status"] != "completed" or not source["search_summary"].strip():
        raise AssetSelectionError("ADOBE_ASSET_SELECTION_REQUIRED: inspect Adobe materials first")
    root = Path(source["library_root"])
    if not root.is_absolute():
        raise AssetSelectionError("asset_source.library_root must be absolute")
    if not root.is_dir():
        raise AssetSelectionError("ADOBE_ASSET_LIBRARY_UNAVAILABLE: restore library access")
    if library is not None:
        allowed_statuses = {"available", "partial"} if source["mode"] == "adobe_stock" else {"available"}
        if library.get("status") not in allowed_statuses:
            raise AssetSelectionError("ADOBE_ASSET_LIBRARY_UNAVAILABLE: refresh creative context")
        if root.resolve() != Path(library.get("root", "")).resolve():
            raise AssetSelectionError("asset_source library differs from creative context")
    selected = source["selected_assets"]
    if source["mode"] == "adobe_stock":
        if not selected or source["fallback_reason"].strip():
            raise AssetSelectionError("adobe_stock requires selected assets and no fallback reason")
        for asset in selected:
            path = Path(asset["path"])
            if not path.is_absolute() or not path.resolve().is_relative_to(root.resolve()):
                raise AssetSelectionError("Selected Adobe asset must be inside library_root")
            try:
                with Image.open(path) as image:
                    image.load()
            except Exception as exc:
                raise AssetSelectionError(f"Selected Adobe asset is unreadable: {path}") from exc
    elif source["mode"] == "generated":
        if selected or not source["fallback_reason"].strip():
            raise AssetSelectionError("generated requires no selected assets and a no-match reason")
    else:
        raise AssetSelectionError("ADOBE_ASSET_SELECTION_REQUIRED: choose adobe_stock or generated")


def asset_execution_brief(source: dict) -> str:
    require_asset_selection(source)
    if source["mode"] == "adobe_stock":
        paths = "\n".join(f"- {asset['path']} ({asset['reason']})" for asset in source["selected_assets"])
        return (
            "Use these authorized Adobe photos as actual input images, not style-only references.\n"
            f"{paths}\n"
            "Inspect and attach the originals to ImageGen. Preserve their people, faces, expressions, "
            "gaze, clothing and photographed scenes. Crop, scale proportionally and place them into the ad; "
            "do not generate replacement people or redraw the photos. Place multiple photos in separate regions. "
            "Use benchmark images only for design grammar. If editing again, retain the source photos."
        )
    return (
        "Adobe library inspection completed; no suitable material was found.\n"
        f"Search: {source['search_summary']}\nReason: {source['fallback_reason']}\n"
        "Generate job-relevant fictional people and workplace imagery using the existing ImageGen workflow."
    )
