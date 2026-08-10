import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image


APP_DIR = Path(__file__).resolve().parents[1] / "review-temp" / "WhiteFlood_BG_Remover_App"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from features.vectorize.presets import get_preset  # noqa: E402
from features.vectorize.service import (  # noqa: E402
    VectorizeError,
    VectorizeService,
    validate_svg_text,
)
from features.watermark.inpaint import LamaInpaintService  # noqa: E402
from features.watermark.mask_canvas import MaskCanvas  # noqa: E402
from features.watermark.media import MediaInfo, probe_video  # noqa: E402
from features.watermark.video import VideoProcessor, VideoError  # noqa: E402


class FeatureContractTests(unittest.TestCase):
    def test_vector_presets_use_supported_vtracer_ranges(self):
        for name in ("Logo", "Illustration", "Line Art", "Detailed"):
            preset = get_preset(name)
            self.assertIn(preset.config["colormode"], {"color", "binary"})
            self.assertIn(preset.config["mode"], {"spline", "polygon", "none"})
            self.assertGreaterEqual(preset.config["length_threshold"], 3.5)
            self.assertLessEqual(preset.config["length_threshold"], 10.0)

    def test_svg_validation_rejects_empty_graphics(self):
        valid = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h1v1z"/></svg>'
        self.assertEqual(validate_svg_text(valid), valid)
        with self.assertRaises(VectorizeError):
            validate_svg_text('<svg xmlns="http://www.w3.org/2000/svg"><g/></svg>')

    def test_vector_save_is_atomic_and_rejects_existing_destination(self):
        valid = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>'
        result = type("Result", (), {"svg_text": valid})()
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "output.svg"
            VectorizeService.save(result, destination)
            self.assertEqual(destination.read_text(encoding="utf-8"), valid)
            with self.assertRaises(VectorizeError):
                VectorizeService.save(result, destination)
            self.assertFalse((Path(temp_dir) / "output.svg.tmp").exists())

    def test_mask_canvas_mapping_removes_letterbox_offset(self):
        canvas = object.__new__(MaskCanvas)
        canvas._image = Image.new("RGB", (100, 50))
        canvas._display_box = (10, 20, 200, 100)
        canvas._display_scale = 2.0
        self.assertEqual(canvas._canvas_to_source(10, 20), (0, 0))
        self.assertEqual(canvas._canvas_to_source(209, 119), (99, 49))
        self.assertIsNone(canvas._canvas_to_source(9, 20))

    def test_lama_inpaint_preserves_alpha_and_unmasked_pixels(self):
        class FakeSession:
            def run(self, _outputs, inputs):
                self.inputs = inputs
                return [np.full((1, 3, 512, 512), 80, dtype=np.uint8)]

        service = LamaInpaintService(model_path="unused.onnx")
        service._session = FakeSession()
        source = Image.new("RGBA", (12, 8), (10, 20, 30, 123))
        mask = Image.new("L", source.size, 0)
        mask.paste(255, (3, 2, 8, 6))
        result = service.inpaint(source, mask)
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, source.size)
        self.assertEqual(result.getchannel("A").getextrema(), (123, 123))
        self.assertEqual(result.getpixel((0, 0)), source.getpixel((0, 0)))
        self.assertNotEqual(result.getpixel((4, 3))[:3], source.getpixel((4, 3))[:3])

    def test_video_media_info_uses_visual_dimensions_for_rotation(self):
        payload = {
            "streams": [{
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "avg_frame_rate": "30000/1001",
                "r_frame_rate": "30000/1001",
                "nb_frames": "60",
                "codec_name": "h264",
                "tags": {"rotate": "90"},
            }, {
                "codec_type": "audio",
                "codec_name": "aac",
            }],
            "format": {"duration": "2.002"},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "portrait.mp4"
            source.write_bytes(b"placeholder")
            with mock.patch("features.watermark.media.ffprobe_json", return_value=payload):
                info = probe_video(source)
        self.assertEqual((info.width, info.height), (1080, 1920))
        self.assertEqual(info.rotation, 90)
        self.assertTrue(info.has_audio)

    def test_video_command_keeps_mp4_container_and_audio_fallback_boundary(self):
        info = MediaInfo(1280, 720, 30.0, 2.0, 60, True, 0)
        audio_command = VideoProcessor._build_encoder_command(
            "ffmpeg.exe", "input.mp4", "output.partial.mp4", info, True
        )
        video_only_command = VideoProcessor._build_encoder_command(
            "ffmpeg.exe", "input.mp4", "output.partial.mp4", info, False
        )
        self.assertIn("-c:a", audio_command)
        self.assertIn("copy", audio_command)
        self.assertIn("-shortest", audio_command)
        self.assertIn("-an", video_only_command)
        self.assertNotIn("-shortest", video_only_command)
        self.assertEqual(audio_command[-3:-1], ["-f", "mp4"])
        self.assertTrue(audio_command[-1].endswith(".mp4"))

    def test_video_output_validation_rejects_dimension_drift(self):
        source = MediaInfo(1920, 1080, 30.0, 2.0, 60, False, 0)
        output = MediaInfo(1080, 1920, 30.0, 2.0, 60, False, 0)
        with self.assertRaises(VideoError):
            VideoProcessor._validate_output(source, output, 60)


if __name__ == "__main__":
    unittest.main()
