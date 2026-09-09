from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import prepare_creative_context as context_script
from scripts import register_codex_candidate as register
from scripts import generate_creative as generate
from services.creative_spec import (
    CreativeSpecError, build_integrated_image_prompt, load_creative_spec,
    normalize_creative_spec, write_creative_spec,
)
from services.production_assets import adobe_catalog, normalize_asset_source, resolve_adobe_root


class AdobeAssetsTest(unittest.TestCase):
    def setUp(self) -> None:
        fixture_root = REPO_ROOT / "tmp"
        fixture_root.mkdir(exist_ok=True)
        self.project = fixture_root / f"adobe-assets-test-{uuid4().hex}"
        self.project.mkdir()
        if not self.project.resolve().is_relative_to(fixture_root.resolve()):
            raise RuntimeError("Test cleanup target must stay inside workspace tmp")
        self.addCleanup(shutil.rmtree, self.project)
        self.root = self.project / "Adobe" / "_image"
        self.root.mkdir(parents=True)
        self.photo = self.root / "写真_123.jpg"
        Image.new("RGB", (120, 90), "navy").save(self.photo)
        self.source = normalize_asset_source({
            "library_root": str(self.root), "search_status": "completed", "mode": "adobe_stock",
            "selected_assets": [{"path": str(self.photo), "reason": "Job and composition match"}],
            "search_summary": "Reviewed catalog and original photograph",
        })
        self.raw = {
            "mode": "codex_integrated", "asset_source": self.source,
            "text_contract": [{"role": "headline", "text": "スタッフ募集"}],
            "image": {"prompt": "Use the selected work photo in a recruitment ad."},
        }

    def test_catalog_distinguishes_empty_missing_and_partial(self) -> None:
        catalog = adobe_catalog(self.root)
        self.assertEqual(catalog["status"], "available")
        self.assertEqual(catalog["items"][0]["absolute_path"], str(self.photo))
        self.assertEqual(catalog["items"][0]["width"], 120)
        self.assertEqual(adobe_catalog(self.root / "missing")["status"], "unavailable")
        empty = self.root / "empty"
        empty.mkdir()
        self.assertEqual(adobe_catalog(empty)["status"], "available")
        self.assertEqual(adobe_catalog(empty)["count"], 0)
        (self.root / "broken.jpg").write_bytes(b"not an image")
        partial = adobe_catalog(self.root)
        self.assertEqual(partial["status"], "partial")
        self.assertEqual(partial["count"], 2)
        self.assertTrue(partial["errors"])

    def test_default_and_override_root(self) -> None:
        with patch.dict("os.environ", {"ADOBE_IMAGE_ROOT": ""}):
            self.assertTrue(resolve_adobe_root().as_posix().endswith("/Adobe/_image"))
        with patch.dict("os.environ", {"ADOBE_IMAGE_ROOT": str(self.root)}):
            self.assertEqual(resolve_adobe_root(), self.root)

    def test_selection_survives_spec_round_trip_and_enters_brief(self) -> None:
        spec = normalize_creative_spec(self.raw)
        path = self.project / "spec.json"
        write_creative_spec(path, spec)
        loaded = load_creative_spec(path)
        self.assertEqual(loaded["asset_source"], self.source)
        prompt = build_integrated_image_prompt(loaded, width=1200, height=900)
        self.assertIn(str(self.photo), prompt)
        self.assertIn("actual input images", prompt)
        self.assertIn("スタッフ募集", prompt)

    def test_generation_requires_completed_search_and_no_match_reason(self) -> None:
        generated = deepcopy(self.raw)
        generated["asset_source"].update(mode="generated", selected_assets=[], fallback_reason="No job-relevant scene")
        spec = normalize_creative_spec(generated)
        self.assertIn("No job-relevant scene", build_integrated_image_prompt(spec, width=1200, height=900))
        for update in (
            {"search_status": "pending"}, {"search_status": "unavailable"},
            {"fallback_reason": ""}, {"search_summary": ""},
            {"selected_assets": self.source["selected_assets"]},
            {"library_root": str(self.root / "missing")},
        ):
            with self.subTest(update=update):
                invalid = deepcopy(spec)
                invalid["asset_source"].update(update)
                with self.assertRaises(CreativeSpecError):
                    build_integrated_image_prompt(invalid, width=1200, height=900)

    def test_old_specs_remain_readable_but_cannot_start_new_generation(self) -> None:
        old = deepcopy(self.raw)
        old.pop("asset_source")
        spec = normalize_creative_spec(old)
        self.assertEqual(spec["text_contract"][0]["text"], "スタッフ募集")
        with self.assertRaisesRegex(CreativeSpecError, "ADOBE_ASSET_SELECTION_REQUIRED"):
            build_integrated_image_prompt(spec, width=1200, height=900)

    def test_selected_files_must_exist_inside_library(self) -> None:
        for path in (self.root / "missing.jpg", self.project / "outside.jpg"):
            invalid = deepcopy(self.raw)
            invalid["asset_source"]["selected_assets"][0]["path"] = str(path)
            with self.assertRaises(CreativeSpecError):
                build_integrated_image_prompt(normalize_creative_spec(invalid), width=1200, height=900)

    def test_api_fallback_cannot_discard_selected_photos(self) -> None:
        spec_file = self.project / "spec.json"
        write_creative_spec(spec_file, self.raw)
        with patch.dict("os.environ", {
            "API_FALLBACK_ENABLED": "true", "OPENAI_API_KEY": "test-placeholder", "OPENAI_IMAGE_MODEL": "test-placeholder",
        }), patch.object(generate, "_generator_for_backend") as backend:
            with self.assertRaisesRegex(SystemExit, "ADOBE_ASSET_INPUT_UNSUPPORTED"):
                generate._run_api_fallback(
                    project_dir=self.project, creative_id="CR001", version="v001", spec_file=str(spec_file),
                    width=120, height=90, context_path=self.project / "context.json", output_spec_source="test",
                )
            backend.assert_not_called()

    def test_context_and_registration_preserve_source_and_block_unavailable(self) -> None:
        (self.project / "project.yaml").write_text("project: test", encoding="utf-8")
        normalized = self.project / "00_request" / "normalized"
        with patch.object(context_script, "load_environment", return_value=self.project), \
             patch.object(context_script, "resolve_project_dir", return_value=self.project), \
             patch.object(context_script, "normalize_project_inputs", return_value={"ready": True}), \
             patch.object(context_script, "_resolve_reference_root", return_value=self.project / "benchmark"), \
             patch.object(context_script, "resolve_adobe_root", return_value=self.root), \
             patch.object(context_script, "_resolve_output_spec", return_value={"width": 120, "height": 90}), \
             patch.object(sys, "argv", ["prepare_creative_context", "--project-id", "TEST"]), redirect_stdout(io.StringIO()):
            context_script.main()
        context_path = normalized / "creative-context.json"
        context = json.loads(context_path.read_text(encoding="utf-8-sig"))
        library = context["production_asset_library"]
        self.assertEqual(library["count"], 1)
        self.assertTrue(Path(library["catalog"]).is_file())
        self.assertTrue(Path(library["contact_sheets"][0]).is_file())
        write_creative_spec(self.project / "02_direction" / "CR001-creative-spec.json", self.raw)
        batch = self.project / "03_batches" / "CR001" / "v001"
        batch.mkdir(parents=True)
        candidate = batch / "candidate.png"
        Image.new("RGB", (120, 90), "white").save(candidate)
        original_bytes = candidate.read_bytes()
        with patch.object(register, "load_environment", return_value=self.project), \
             patch.object(register, "resolve_project_dir", return_value=self.project), \
             patch.object(register, "verify_image_text", return_value={"status": "unavailable"}), \
             patch.object(sys, "argv", ["register", "--project-id", "TEST"]), redirect_stdout(io.StringIO()):
            register.main()
            metadata = json.loads((batch / "generation-metadata.json").read_text(encoding="utf-8-sig"))
            self.assertEqual(metadata["asset_source"], self.source)
            self.assertFalse(metadata["formal_delivery"])
            self.assertEqual(candidate.read_bytes(), original_bytes)
            context["production_asset_library"]["status"] = "partial"
            context_path.write_text(json.dumps(context), encoding="utf-8")
            register.main()  # A readable selected photo remains usable despite unrelated catalog errors.
            generated = deepcopy(self.raw)
            generated["asset_source"].update(mode="generated", selected_assets=[], fallback_reason="No matching photo")
            write_creative_spec(self.project / "02_direction" / "CR001-creative-spec.json", generated)
            with self.assertRaisesRegex(SystemExit, "ADOBE_ASSET_LIBRARY_UNAVAILABLE"):
                register.main()
            write_creative_spec(self.project / "02_direction" / "CR001-creative-spec.json", self.raw)
            context["production_asset_library"]["status"] = "unavailable"
            context_path.write_text(json.dumps(context), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "ADOBE_ASSET_LIBRARY_UNAVAILABLE"):
                register.main()


if __name__ == "__main__":
    unittest.main()
