from __future__ import annotations

import base64
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import promote_creative


class PromotionTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp_root = REPO_ROOT / "tmp"
        tmp_root.mkdir(exist_ok=True)
        self.temporary = TemporaryDirectory(prefix="promotion-test-", dir=tmp_root)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "PJ-TEST_fixture"
        self.batch = self.project / "03_batches" / "CR001" / "v001"
        self.batch.mkdir(parents=True)
        self.image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jZ5kAAAAASUVORK5CYII="
        )
        (self.batch / "candidate.png").write_bytes(self.image)
        self.copy = "# 確定コピー\n承認済みの文字列\n"
        (self.batch / "expected-copy.md").write_text(self.copy, encoding="utf-8")
        self.metadata = {
            "creative_id": "CR001",
            "version": "v001",
            "formal_delivery": False,
            "mode": "codex_imagegen",
            "generation_owner": "codex_integrated_creative_designer",
            "generation_capability": "codex_imagegen",
        }
        self.write_json(self.batch / "generation-metadata.json", self.metadata)
        self.approval = dict(self.metadata)
        self.approval.update({flag: True for flag in promote_creative.REQUIRED_APPROVAL_FLAGS})
        self.approval_path = self.project / "04_project_review" / "CR001-v001-final-approval.json"
        self.approval_path.parent.mkdir()
        self.write_json(self.approval_path, self.approval)
        self.records = self.project / "04_project_review" / "delivery_records" / "CR001" / "v001"
        self.delivery = self.project / "05_delivery"

    @staticmethod
    def write_json(path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def promote(self, *extra: str, approval_path: Path | None = None, version: str = "v001") -> str:
        argv = [
            "promote_creative.py", "--project-id", "PJ-TEST", "--creative-id", "CR001",
            "--version", version, "--approval-file", str(approval_path or self.approval_path), *extra,
        ]
        output = StringIO()
        with patch.object(promote_creative, "load_environment", return_value=self.root), \
                patch.object(sys, "argv", argv), redirect_stdout(output):
            promote_creative.main()
        return output.getvalue()

    def test_delivery_contains_only_image_and_records_preserve_sources(self) -> None:
        output = self.promote()
        self.assertEqual([p.name for p in self.delivery.iterdir()], ["CR001.png"])
        self.assertEqual((self.delivery / "CR001.png").read_bytes(), self.image)
        expected_sources = {
            "CR001-copy.md": self.batch / "expected-copy.md",
            "CR001-approval.json": self.approval_path,
            "CR001-generation-metadata.json": self.batch / "generation-metadata.json",
        }
        self.assertEqual({p.name for p in self.records.iterdir()}, set(expected_sources))
        for filename, source in expected_sources.items():
            self.assertEqual((self.records / filename).read_bytes(), source.read_bytes())
        for key, path in {
            "IMAGE": self.delivery / "CR001.png",
            "COPY": self.records / "CR001-copy.md",
            "APPROVAL": self.records / "CR001-approval.json",
            "GENERATION_METADATA": self.records / "CR001-generation-metadata.json",
        }.items():
            self.assertIn(f"{key}={path}", output)

    def test_custom_image_name_keeps_supporting_records_outside_delivery(self) -> None:
        self.promote("--output-name", "農園_完成.jpg")
        self.assertEqual({p.name for p in self.delivery.iterdir()}, {"農園_完成.png"})
        self.assertEqual({p.name for p in self.records.iterdir()}, {
            "農園_完成-copy.md", "農園_完成-approval.json", "農園_完成-generation-metadata.json",
        })

    def test_each_missing_approval_still_blocks_all_outputs(self) -> None:
        for flag in promote_creative.REQUIRED_APPROVAL_FLAGS:
            with self.subTest(flag=flag):
                self.write_json(self.approval_path, {**self.approval, flag: False})
                with self.assertRaisesRegex(SystemExit, "delivery blocked"):
                    self.promote()
                self.assertFalse(self.delivery.exists())
                self.assertFalse(self.records.exists())

    def test_mismatched_approval_version_still_blocks_delivery(self) -> None:
        self.write_json(self.approval_path, {**self.approval, "version": "v002"})
        with self.assertRaisesRegex(SystemExit, "approval version does not match"):
            self.promote()
        self.assertFalse(self.delivery.exists())

    def test_copy_is_optional(self) -> None:
        (self.batch / "expected-copy.md").unlink()
        output = self.promote()
        self.assertNotIn("COPY=", output)
        self.assertEqual({p.name for p in self.records.iterdir()}, {
            "CR001-approval.json", "CR001-generation-metadata.json",
        })
        self.assertEqual({p.name for p in self.delivery.iterdir()}, {"CR001.png"})

    def test_repeat_promotion_can_use_archived_approval(self) -> None:
        self.promote()
        archived = self.records / "CR001-approval.json"
        original = archived.read_bytes()
        self.promote(approval_path=archived)
        self.assertEqual(archived.read_bytes(), original)
        self.assertEqual({p.name for p in self.delivery.iterdir()}, {"CR001.png"})

    def test_new_version_keeps_previous_delivery_records(self) -> None:
        self.promote()
        previous_approval = (self.records / "CR001-approval.json").read_bytes()
        batch_v2 = self.batch.parent / "v002"
        batch_v2.mkdir()
        (batch_v2 / "candidate.png").write_bytes(self.image)
        (batch_v2 / "expected-copy.md").write_text("更新したコピー", encoding="utf-8")
        self.write_json(batch_v2 / "generation-metadata.json", {**self.metadata, "version": "v002"})
        self.write_json(self.approval_path, {**self.approval, "version": "v002"})
        self.promote(version="v002")
        self.assertEqual((self.records / "CR001-approval.json").read_bytes(), previous_approval)
        self.assertEqual(
            (self.records.parent / "v002" / "CR001-copy.md").read_text(encoding="utf-8"),
            "更新したコピー",
        )
        self.assertEqual({p.name for p in self.delivery.iterdir()}, {"CR001.png"})


if __name__ == "__main__":
    unittest.main()
