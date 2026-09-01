from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from services.manifest import load_rows


def _font(size: int):
    candidates = [
        "C:/Windows/Fonts/YuGothB.ttc",
        "C:/Windows/Fonts/meiryob.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def build_contact_sheet(
    project_dir: Path,
    *,
    columns: int = 4,
    thumb_width: int = 360,
    cell_padding: int = 18,
) -> Path | None:
    rows = [row for row in load_rows(project_dir / "creative-manifest.csv") if row.get("image_path")]
    rows = [row for row in rows if Path(row["image_path"]).exists()]
    if not rows:
        return None

    label_height = 72
    cells = []
    max_cell_height = 0
    for row in rows:
        with Image.open(row["image_path"]) as image:
            image = image.convert("RGB")
            ratio = thumb_width / image.width
            thumb_height = max(1, round(image.height * ratio))
            thumb = image.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        cell_height = thumb.height + label_height + cell_padding * 2
        max_cell_height = max(max_cell_height, cell_height)
        cells.append((row, thumb))

    rows_count = math.ceil(len(cells) / columns)
    sheet_width = columns * (thumb_width + cell_padding * 2)
    sheet_height = rows_count * max_cell_height
    sheet = Image.new("RGB", (sheet_width, sheet_height), "white")
    draw = ImageDraw.Draw(sheet)
    title_font = _font(22)
    score_font = _font(18)

    for index, (row, thumb) in enumerate(cells):
        col = index % columns
        row_index = index // columns
        x = col * (thumb_width + cell_padding * 2) + cell_padding
        y = row_index * max_cell_height + cell_padding
        sheet.paste(thumb, (x, y))
        label_y = y + thumb.height + 8
        draw.text((x, label_y), row.get("creative_id", ""), font=title_font, fill="black")
        score = (
            f"Claude {row.get('claude_score') or '-'} / "
            f"Codex {row.get('codex_score') or '-'} / "
            f"Final {row.get('final_score') or '-'}"
        )
        draw.text((x, label_y + 30), score, font=score_font, fill="black")

    output = project_dir / "04_project_review" / "contact-sheet.jpg"
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="JPEG", quality=90, optimize=True)
    return output
