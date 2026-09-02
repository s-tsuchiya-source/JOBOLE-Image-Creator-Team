from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from pathlib import Path
import sys

import yaml
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageOps


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
load_dotenv(REPO_ROOT / ".env", override=True)

from input_loader import extract_source_text, list_files, normalize_project_inputs
from load_project import load_environment, resolve_project_dir


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

JOB_FIELDS = [
    "ID",
    "タイトル",
    "業種",
    "職種カテゴリ",
    "雇用形態",
    "店舗名",
    "給与",
    "給与(最低)",
    "給与(最高)",
    "給与詳細",
    "都道府県",
    "勤務先住所",
    "アクセス",
    "駅名",
    "仕事内容",
    "応募条件",
    "学歴",
    "勤務開始時間",
    "勤務終了時間",
    "休日・休暇",
    "求人の特徴",
    "PR・職場情報",
    "勤務時間・シフト詳細",
    "待遇・福利厚生",
    "通勤手当有無",
    "労働時間数",
    "固定残業代有無",
    "固定残業の時間数",
    "固定残業代の金額",
    "試用期間有無",
    "求人ポイント",
    "備考",
]

HEARING_FIELDS = [
    "会社名/媒体名",
    "希望納品日",
    "プラン",
    "職種/業種",
    "ターゲット",
    "最も伝えたいこと",
    "NGワード",
    "テイスト",
    "使用素材",
    "配信媒体",
    "その他サイズ",
    "制作枚数",
    "その他枚数",
    "参考イメージ",
    "その他要望",
    "パターン戦略",
    "訴求軸1",
    "訴求軸2",
    "訴求軸3",
    "ABテスト希望",
    "参考画像",
    "企業ID",
    "申込種別",
    "エンド企業名",
]


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return [
                    {str(key): "" if value is None else str(value).strip() for key, value in row.items()}
                    for row in csv.DictReader(handle)
                ]
        except UnicodeDecodeError:
            continue
    raise ValueError(f"CSV文字コードを判定できません: {path}")


def _compact_csv(path: Path, allowed_fields: list[str], max_rows: int = 10) -> list[dict]:
    rows = _read_csv_rows(path)
    compact: list[dict] = []
    for row in rows[:max_rows]:
        item = {key: row.get(key, "") for key in allowed_fields if row.get(key, "").strip()}
        if item:
            compact.append(item)
    return compact


def _compact_source(path: Path, category: str) -> dict:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        fields = JOB_FIELDS if category == "job_posting" else HEARING_FIELDS
        return {
            "source_file": path.name,
            "format": "csv",
            "rows": _compact_csv(path, fields),
        }

    text = extract_source_text(path).strip()
    max_chars = int(os.getenv("COMPACT_SOURCE_MAX_CHARS", "12000"))
    return {
        "source_file": path.name,
        "format": suffix.lstrip("."),
        "text_excerpt": text[:max_chars],
        "truncated": len(text) > max_chars,
        "raw_source_path": str(path),
    }


def _hearing_values(compact_hearings: list[dict]) -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for source in compact_hearings:
        for row in source.get("rows", []):
            if isinstance(row, dict):
                values.append({str(k): str(v) for k, v in row.items()})
    return values


def _load_media_config() -> dict:
    path = REPO_ROOT / "configs" / "media.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _resolve_output_spec(compact_hearings: list[dict]) -> dict:
    config = _load_media_config()
    presets = config.get("media_presets", {})
    default = dict(presets.get("default", {})) or {
        "width": 1200,
        "height": 628,
        "aspect_ratio": "1.91:1",
        "enforce_aspect_ratio": False,
    }

    media_value = ""
    for row in _hearing_values(compact_hearings):
        if row.get("配信媒体", "").strip():
            media_value = row["配信媒体"].strip()
            break

    if media_value:
        normalized = re.sub(r"\s+", "", media_value).lower()
        for name, preset in presets.items():
            if name == "default":
                continue
            aliases = [str(value) for value in preset.get("aliases", [])]
            if any(re.sub(r"\s+", "", alias).lower() == normalized for alias in aliases):
                resolved = dict(preset)
                resolved["preset"] = name
                resolved["source"] = "hearing_sheet_media"
                resolved["hearing_media"] = media_value
                return resolved

    default["preset"] = "default"
    default["source"] = "phase1_default"
    default["hearing_media"] = media_value or None
    return default


def _resolve_reference_root() -> Path:
    configured = os.getenv("ORIGINAL_IMAGE_ROOT", "").strip()
    if configured:
        return Path(configured)
    projects_root = Path(os.getenv("PROJECTS_ROOT", ""))
    if str(projects_root):
        return projects_root.parent / "original_image"
    return REPO_ROOT / "original_image"


def _load_reference_index(root: Path) -> dict[str, dict]:
    index_path = root / "_index.csv"
    if not index_path.exists():
        return {}
    rows = _read_csv_rows(index_path)
    result: dict[str, dict] = {}
    for row in rows:
        key = row.get("file_path", "").replace("\\", "/").lstrip("./")
        if key:
            result[key.lower()] = {k: v for k, v in row.items() if v}
    return result


def _reference_catalog(root: Path) -> list[dict]:
    if not root.exists():
        return []
    metadata = _load_reference_index(root)
    catalog: list[dict] = []
    for index, path in enumerate(
        sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS),
        start=1,
    ):
        relative = path.relative_to(root).as_posix()
        try:
            with Image.open(path) as image:
                width, height = image.size
        except Exception:
            width, height = 0, 0
        item = {
            "reference_id": f"R{index:04d}",
            "relative_path": relative,
            "absolute_path": str(path),
            "folder": path.parent.relative_to(root).as_posix() if path.parent != root else ".",
            "width": width,
            "height": height,
            "aspect_ratio": round(width / height, 4) if width and height else None,
        }
        meta = metadata.get(relative.lower())
        if meta:
            item["metadata"] = meta
        catalog.append(item)
    return catalog


def _extract_keywords(job_sources: list[dict], hearing_sources: list[dict]) -> list[str]:
    values: list[str] = []
    preferred_keys = {
        "タイトル",
        "業種",
        "職種カテゴリ",
        "店舗名",
        "職種/業種",
        "ターゲット",
        "最も伝えたいこと",
        "テイスト",
        "配信媒体",
    }
    for source in [*job_sources, *hearing_sources]:
        for row in source.get("rows", []):
            for key, value in row.items():
                if key in preferred_keys and str(value).strip():
                    values.append(str(value).strip())

    keywords: list[str] = []
    for value in values:
        for token in re.split(r"[\s/／,，、・|｜:：()（）\[\]【】]+", value):
            token = token.strip().lower()
            if len(token) >= 2 and token not in keywords:
                keywords.append(token)
    return keywords[:40]


def _benchmark_shortlist(catalog: list[dict], keywords: list[str]) -> list[dict]:
    limit = max(1, int(os.getenv("REFERENCE_SHORTLIST_MAX", "3")))
    scored: list[tuple[int, dict]] = []
    for item in catalog:
        metadata = item.get("metadata", {})
        haystack = " ".join(
            [
                item.get("relative_path", ""),
                item.get("folder", ""),
                *[str(value) for value in metadata.values()],
            ]
        ).lower()
        score = sum(1 for keyword in keywords if keyword in haystack)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["relative_path"]))
    return [
        {
            "reference_id": item["reference_id"],
            "relative_path": item["relative_path"],
            "absolute_path": item["absolute_path"],
            "metadata": item.get("metadata", {}),
            "deterministic_match_score": score,
        }
        for score, item in scored[:limit]
    ]


def _build_contact_sheets(catalog: list[dict], output_dir: Path) -> list[str]:
    if not catalog:
        return []
    per_page = max(4, int(os.getenv("REFERENCE_CONTACT_SHEET_MAX", "24")))
    cell_w, cell_h = 260, 190
    thumb_w, thumb_h = 240, 145
    columns = 4
    pages: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for page_index in range(math.ceil(len(catalog) / per_page)):
        items = catalog[page_index * per_page : (page_index + 1) * per_page]
        rows = math.ceil(len(items) / columns)
        canvas = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
        draw = ImageDraw.Draw(canvas)
        for offset, item in enumerate(items):
            col = offset % columns
            row = offset // columns
            x = col * cell_w
            y = row * cell_h
            try:
                with Image.open(item["absolute_path"]) as source:
                    thumb = ImageOps.contain(source.convert("RGB"), (thumb_w, thumb_h))
                    px = x + (cell_w - thumb.width) // 2
                    py = y + 8 + (thumb_h - thumb.height) // 2
                    canvas.paste(thumb, (px, py))
            except Exception:
                draw.rectangle((x + 10, y + 10, x + cell_w - 10, y + thumb_h), outline="black")
            draw.text((x + 10, y + 160), item["reference_id"], fill="black")

        path = output_dir / f"reference-contact-sheet-{page_index + 1:02d}.jpg"
        canvas.save(path, quality=88)
        pages.append(str(path))
    return pages


def _supplementary_text(project_dir: Path) -> list[dict]:
    folder = project_dir / "00_request" / "inbox" / "request_text"
    max_chars = int(os.getenv("SUPPLEMENTARY_TEXT_MAX_CHARS", "4000"))
    result = []
    for path in list_files(folder):
        try:
            text = extract_source_text(path).strip()
        except Exception as exc:
            result.append({"source_file": path.name, "error": str(exc)})
            continue
        result.append(
            {
                "source_file": path.name,
                "text": text[:max_chars],
                "truncated": len(text) > max_chars,
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare compact AI context and benchmark contact sheets before any Claude analysis. "
            "This script performs deterministic extraction only; creative judgment remains with Codex/Claude."
        )
    )
    parser.add_argument("--project-id", required=True)
    args = parser.parse_args()

    projects_root = load_environment()
    project_dir = resolve_project_dir(projects_root, args.project_id)
    normalized_dir = project_dir / "00_request" / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    normalized = normalize_project_inputs(project_dir)
    if not normalized.get("ready"):
        raise SystemExit(
            "求人ファイルを正常に読み込めません。creative context作成前に入力を確認してください。"
        )

    job_dir = project_dir / "00_request" / "inbox" / "job_posting"
    hearing_dir = project_dir / "00_request" / "inbox" / "hearing"
    job_sources = [_compact_source(path, "job_posting") for path in list_files(job_dir)]
    hearing_sources = [_compact_source(path, "hearing") for path in list_files(hearing_dir)]

    reference_root = _resolve_reference_root()
    catalog = _reference_catalog(reference_root)
    keywords = _extract_keywords(job_sources, hearing_sources)
    deterministic_shortlist = _benchmark_shortlist(catalog, keywords)
    reference_dir = normalized_dir / "reference_library"
    contact_sheets = _build_contact_sheets(catalog, reference_dir)

    catalog_path = reference_dir / "reference-catalog.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "reference_root": str(reference_root),
                "count": len(catalog),
                "items": catalog,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8-sig",
    )

    output_spec = _resolve_output_spec(hearing_sources)
    context = {
        "project": {
            "project_id": args.project_id,
            "project_dir": str(project_dir),
        },
        "token_efficiency": {
            "rule": "Use this compact context first. Read raw source only to resolve ambiguity or verify a claim.",
            "raw_source_bundle": normalized.get("source_bundle"),
            "reference_shortlist_max": int(os.getenv("REFERENCE_SHORTLIST_MAX", "3")),
            "creative_route_max": int(os.getenv("CREATIVE_ROUTE_MAX", "2")),
            "fact_chip_max": int(os.getenv("FACT_CHIP_MAX", "3")),
            "revision_max": int(os.getenv("REVISION_MAX", "2")),
        },
        "job_postings": job_sources,
        "hearings": hearing_sources,
        "supplementary_text": _supplementary_text(project_dir),
        "resolved_output_spec": output_spec,
        "reference_library": {
            "root": str(reference_root),
            "count": len(catalog),
            "catalog": str(catalog_path),
            "contact_sheets": contact_sheets,
            "deterministic_shortlist": deterministic_shortlist,
            "shortlist_status": "metadata_match" if deterministic_shortlist else "cco_visual_selection_required",
            "selection_rule": (
                "Codex CCO must choose up to REFERENCE_SHORTLIST_MAX relevant samples. "
                "The deterministic shortlist is only a token-saving hint, never an automatic creative decision."
            ),
        },
    }

    context_path = normalized_dir / "creative-context.json"
    context_path.write_text(
        json.dumps(context, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )

    print("CREATIVE CONTEXT: PASS")
    print(f"PROJECT_ID={args.project_id}")
    print(f"CONTEXT={context_path}")
    print(f"OUTPUT_SPEC={output_spec.get('width')}x{output_spec.get('height')} ({output_spec.get('aspect_ratio')})")
    print(f"OUTPUT_SPEC_SOURCE={output_spec.get('source')}")
    print(f"REFERENCE_ROOT={reference_root}")
    print(f"REFERENCE_COUNT={len(catalog)}")
    print(f"REFERENCE_CONTACT_SHEETS={len(contact_sheets)}")
    print(f"REFERENCE_DETERMINISTIC_SHORTLIST={len(deterministic_shortlist)}")
    print("NEXT=Codex CCO benchmark selection -> Recruitment Analyst")


if __name__ == "__main__":
    main()
