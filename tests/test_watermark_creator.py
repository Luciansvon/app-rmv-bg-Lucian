import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from review_temp_import_helper import ensure_app_on_path

ensure_app_on_path()

from features.watermark_creator import (
    CreatorPreset,
    InvisiblePayload,
    VisibleWatermarkConfig,
    WatermarkCreatorService,
    apply_visible_watermark,
    benchmark_invisible,
    embed_invisible_watermark,
    load_preset,
    save_preset,
    verify_invisible_watermark,
)


def fixture(size=(512, 512), alpha=False):
    w, h = size
    y, x = np.mgrid[0:h, 0:w]
    r = ((x / max(1, w - 1)) * 180 + 40).astype(np.uint8)
    g = ((y / max(1, h - 1)) * 150 + 50).astype(np.uint8)
    b = (((x + y) % 160) + 50).astype(np.uint8)
    arr = np.dstack([r, g, b])
    image = Image.fromarray(arr, "RGB")
    if alpha:
        a = np.full((h, w), 255, dtype=np.uint8)
        a[:20, :20] = 0
        image = Image.fromarray(np.dstack([arr, a]), "RGBA")
    return image


class VisibleTests(unittest.TestCase):
    def test_text_watermark_preserves_dimensions(self):
        source = fixture(alpha=True)
        result = apply_visible_watermark(source, VisibleWatermarkConfig(
            text="BIMA", pattern="diagonal_repeat", opacity=58, rotation=-30,
        ))
        self.assertEqual(result.size, source.size)
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.getpixel((0, 0))[3], 0)

    def test_image_watermark_preserves_alpha(self):
        source = fixture(alpha=True)
        logo = Image.new("RGBA", (120, 60), (255, 0, 0, 180))
        result = apply_visible_watermark(
            source,
            VisibleWatermarkConfig(kind="image", image_scale_percent=20, anchor="LR", rotation=12),
            logo=logo,
        )
        self.assertEqual(result.size, source.size)
        self.assertEqual(result.mode, "RGBA")


class InvisibleTests(unittest.TestCase):
    def setUp(self):
        self.payload = InvisiblePayload(
            owner_id="BIMA", file_id="8F31A2", created_at=1789100000,
            short_hash="A1B2C3D4",
        )

    def test_embed_verify_roundtrip(self):
        source = fixture((512, 512))
        embedded = embed_invisible_watermark(source, self.payload, strength="balanced")
        self.assertEqual(embedded.image.size, source.size)
        verified = verify_invisible_watermark(embedded.image, robust_scan=False)
        self.assertTrue(verified.detected, verified.message)
        self.assertTrue(verified.payload_valid)
        self.assertEqual(verified.payload, self.payload)

    def test_unwatermarked_is_not_detected(self):
        result = verify_invisible_watermark(fixture((512, 512)), robust_scan=False)
        self.assertFalse(result.detected)

    def test_hybrid_pipeline(self):
        source = fixture((512, 512), alpha=True)
        service = WatermarkCreatorService()
        result = service.create(
            source,
            mode="hybrid",
            visible_config=VisibleWatermarkConfig(text="BIMA", opacity=35, anchor="LR", rotation=0),
            invisible_payload=self.payload,
            invisible_strength="strong",
        )
        self.assertEqual(result.image.size, source.size)
        self.assertEqual(result.image.mode, "RGBA")


class PresetTests(unittest.TestCase):
    def test_preset_roundtrip_and_unknown_field_tolerance(self):
        preset = CreatorPreset(visible=VisibleWatermarkConfig(text="TEST", opacity=44))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "preset.json"
            save_preset(preset, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["visible"]["future_field"] = 123
            path.write_text(json.dumps(data), encoding="utf-8")
            loaded = load_preset(path)
        self.assertEqual(loaded.visible.text, "TEST")
        self.assertEqual(loaded.visible.opacity, 44)


class ServiceTests(unittest.TestCase):
    def test_save_collision_safe(self):
        service = WatermarkCreatorService()
        source = fixture((256, 256))
        result = service.create(source, "visible", visible_config=VisibleWatermarkConfig(text="X"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.png"
            first = service.save(result, path)
            second = service.save(result, path)
            self.assertNotEqual(first, second)
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())

    def test_batch_preserves_relative_structure(self):
        service = WatermarkCreatorService()
        with tempfile.TemporaryDirectory() as src_tmp, tempfile.TemporaryDirectory() as out_tmp:
            src = Path(src_tmp)
            nested = src / "sub"
            nested.mkdir()
            fixture((256, 256)).save(src / "a.png")
            fixture((256, 256)).save(nested / "b.png")
            outputs = service.process_batch(
                src, out_tmp, "visible", VisibleWatermarkConfig(text="BIMA"), recursive=True,
            )
            self.assertEqual(len(outputs), 2)
            self.assertTrue((Path(out_tmp) / "a.png").exists())
            self.assertTrue((Path(out_tmp) / "sub" / "b.png").exists())


class BenchmarkTests(unittest.TestCase):
    def test_benchmark_report_has_required_attacks(self):
        payload = InvisiblePayload("BIMA", "FILE01", 1789100000, "ABC123")
        report = benchmark_invisible(fixture((512, 512)), payload, strength="strong")
        names = {item.name for item in report.attacks}
        self.assertIn("jpeg_80", names)
        self.assertIn("resize_90_roundtrip", names)
        self.assertIn("crop_5_percent", names)
        self.assertIn("visible_overlay", names)
        self.assertFalse(report.false_positive)


if __name__ == "__main__":
    unittest.main()
