import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import types
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
from features.performance import (  # noqa: E402
    PROCESSING_BALANCED,
    PROCESSING_SLOW,
    PROCESSING_SUPER_FAST,
    apply_vector_profile,
    get_processing_profile,
    processing_profile_names,
)
from features.model_download import ModelSpec, download_model  # noqa: E402
from features.watermark.inpaint import LamaInpaintService  # noqa: E402
from features.watermark.mask_canvas import MaskCanvas  # noqa: E402
from features.watermark.media import (  # noqa: E402
    MediaInfo,
    bundled_binary,
    probe_video,
)
from features.watermark.video import VideoProcessor, VideoError  # noqa: E402
import whiteflood_app as app_module  # noqa: E402
from whiteflood_app import (  # noqa: E402
    MODEL_CONNECT_PHASE,
    MODEL_PREPARE_PHASE,
    REMOVE_BG_INFERENCE_PHASE,
    WhiteFloodApp,
    _ModelDownloadProgress,
    _UiEventQueue,
    _friendly_model_download_error,
    format_duration,
)


class FeatureContractTests(unittest.TestCase):
    def test_processing_profiles_have_explicit_tradeoffs(self):
        self.assertEqual(
            processing_profile_names(),
            (PROCESSING_SLOW, PROCESSING_BALANCED, PROCESSING_SUPER_FAST),
        )
        slow = get_processing_profile(PROCESSING_SLOW)
        balanced = get_processing_profile(PROCESSING_BALANCED)
        super_fast = get_processing_profile(PROCESSING_SUPER_FAST)
        self.assertTrue(slow.requires_confirmation)
        self.assertFalse(balanced.requires_confirmation)
        self.assertTrue(super_fast.requires_confirmation)
        self.assertLess(slow.onnx_threads, super_fast.onnx_threads)
        self.assertLess(slow.ffmpeg_threads, super_fast.ffmpeg_threads)
        self.assertGreater(slow.lama_context, super_fast.lama_context)
        self.assertGreater(slow.lama_overlap, super_fast.lama_overlap)

    def test_vector_speed_profile_changes_expensive_settings(self):
        base = dict(get_preset("Detailed").config)
        slow = apply_vector_profile(base, PROCESSING_SLOW)
        balanced = apply_vector_profile(base, PROCESSING_BALANCED)
        super_fast = apply_vector_profile(base, PROCESSING_SUPER_FAST)
        self.assertGreaterEqual(slow["max_iterations"], balanced["max_iterations"])
        self.assertGreaterEqual(slow["path_precision"], balanced["path_precision"])
        self.assertLessEqual(
            super_fast["max_iterations"], balanced["max_iterations"]
        )
        self.assertLessEqual(
            super_fast["path_precision"], balanced["path_precision"]
        )
        self.assertGreaterEqual(
            super_fast["filter_speckle"], balanced["filter_speckle"]
        )

    def test_duration_formatter_uses_hh_mm_ss(self):
        self.assertEqual(format_duration(0), "00:00:00")
        self.assertEqual(format_duration(65), "00:01:05")
        self.assertEqual(format_duration(3661), "01:01:01")

    def test_aggressive_white_background_mode_changes_near_white_removal(self):
        source = Image.new("RGB", (5, 5), (210, 210, 210))
        source.putpixel((2, 2), (20, 20, 20))

        normal = app_module.flood_remove_bg(
            source, threshold=220, fringe=0, aggressive=False
        )
        aggressive = app_module.flood_remove_bg(
            source, threshold=220, fringe=0, aggressive=True
        )

        self.assertEqual(normal.getpixel((0, 0))[3], 255)
        self.assertEqual(aggressive.getpixel((0, 0))[3], 0)
        self.assertEqual(aggressive.getpixel((2, 2))[3], 255)

    def test_alpha_padding_uses_nearby_visible_rgb(self):
        source = Image.new("RGBA", (5, 1), (200, 0, 0, 0))
        source.putpixel((2, 0), (10, 20, 30, 255))

        padded = app_module._alpha_aware_rgb(source, padding_radius=1)

        self.assertEqual(padded.mode, "RGB")
        self.assertEqual(padded.getpixel((1, 0)), (10, 20, 30))
        self.assertEqual(padded.getpixel((3, 0)), (10, 20, 30))
        self.assertEqual(padded.getpixel((0, 0)), (200, 0, 0))

    def test_transparent_upscale_sends_rgb_and_merges_lanczos_alpha(self):
        observed_modes = []

        class FakePopen:
            def __init__(self, command, **_kwargs):
                input_path = Path(command[command.index("-i") + 1])
                output_path = Path(command[command.index("-o") + 1])
                with Image.open(input_path) as input_image:
                    observed_modes.append(input_image.mode)
                    input_image.resize((4, 4), Image.Resampling.NEAREST).save(
                        output_path, format="PNG"
                    )
                self.stderr = []
                self.returncode = 0

            def wait(self):
                return self.returncode

        source = Image.new("RGBA", (2, 2), (220, 0, 0, 0))
        source.putpixel((0, 0), (10, 20, 30, 255))

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with mock.patch.object(
                app_module,
                "_get_realesrgan_paths",
                return_value=(root, root / "fake.exe", root),
            ), mock.patch("subprocess.Popen", FakePopen):
                result = app_module.upscale_image_alpha_safe(source, scale=2)

        self.assertEqual(observed_modes, ["RGB"])
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, (4, 4))
        self.assertIsNotNone(result.getchannel("A").getbbox())

    def test_worker_ui_events_are_drained_on_main_thread(self):
        bridge = _UiEventQueue()
        events = []
        worker = threading.Thread(
            target=lambda: bridge.post(lambda: events.append("download"))
        )
        worker.start()
        worker.join()

        self.assertEqual(events, [])
        for callback in bridge.drain():
            callback()
        self.assertEqual(events, ["download"])

    def test_remove_background_marks_inference_indeterminate_before_engine(self):
        events = []
        source = Image.new("RGB", (2, 2), (20, 30, 40))
        expected = Image.new("RGBA", source.size, (20, 30, 40, 255))

        def fake_remove(*_args, **_kwargs):
            self.assertEqual(
                events[-1],
                {"kind": "phase_indeterminate", "message": REMOVE_BG_INFERENCE_PHASE},
            )
            return expected

        fake_rembg = types.ModuleType("rembg")
        fake_rembg.remove = fake_remove
        with mock.patch.object(app_module, "REMBG_OK", True), \
                mock.patch.object(app_module, "_get_rembg_session", return_value=object()), \
                mock.patch.dict(sys.modules, {"rembg": fake_rembg}):
            result = app_module.ai_remove_bg(source, status_cb=events.append)

        self.assertEqual(result.size, source.size)
        self.assertEqual(
            events[0],
            {"kind": "phase_indeterminate", "message": MODEL_PREPARE_PHASE},
        )
        self.assertEqual(events[1]["kind"], "phase_indeterminate")
        self.assertEqual(events[-1], 100.0)

    def test_model_progress_reports_real_bytes_without_dummy_percent(self):
        events = []
        progress = _ModelDownloadProgress(events.append, "birefnet-massive")
        progress.total = 100

        progress.update(15)
        progress._last_emit_at = 0
        progress.update(35)

        self.assertEqual(events[0]["percent"], 15)
        self.assertEqual(events[-1]["downloaded"], 50)
        self.assertEqual(events[-1]["total"], 100)

    def test_model_connection_error_explains_office_firewall(self):
        message = _friendly_model_download_error(
            "birefnet-massive",
            RuntimeError("HTTPSConnectionPool: Read timed out"),
        )

        self.assertIn("jaringan kantor", message)
        self.assertIn("github.com", message)
        self.assertIn(".u2net", message)
        self.assertIn("Get-ChildItem", message)

    def test_rembg_download_uses_ui_progress_and_explicit_timeouts(self):
        events = []
        fake_session = object()

        class FakeSessionOptions:
            pass

        fake_ort = types.ModuleType("onnxruntime")
        fake_ort.SessionOptions = FakeSessionOptions
        fake_rembg = types.ModuleType("rembg")

        def fake_new_session(*_args, **_kwargs):
            import pooch

            pooch.retrieve(
                "https://example.invalid/model.onnx",
                "md5:fake",
                progressbar=True,
            )
            return fake_session

        fake_rembg.new_session = fake_new_session
        app_module._rembg_session = None
        app_module._rembg_model_name = None
        app_module._rembg_session_threads = None
        try:
            with mock.patch.dict(
                sys.modules,
                {"rembg": fake_rembg, "onnxruntime": fake_ort},
            ), mock.patch("pooch.retrieve") as original_retrieve:
                result = app_module._get_rembg_session(
                    "birefnet-massive",
                    status_cb=events.append,
                    onnx_threads=2,
                )

            self.assertIs(result, fake_session)
            downloader = original_retrieve.call_args.kwargs["downloader"]
            self.assertEqual(downloader.chunk_size, 64 * 1024)
            self.assertEqual(downloader.kwargs["timeout"], (15, 30))
            self.assertIsInstance(downloader.progressbar, _ModelDownloadProgress)
            self.assertEqual(events[-1]["kind"], "phase_indeterminate")
        finally:
            app_module._rembg_session = None
            app_module._rembg_model_name = None
            app_module._rembg_session_threads = None

    def test_remove_background_worker_has_no_dummy_15_percent(self):
        source = (APP_DIR / "whiteflood_app.py").read_text(encoding="utf-8")

        self.assertNotIn("self.progress.set(0.15)", source)
        self.assertNotIn("status_cb(5.0)", source)
        self.assertIn(MODEL_CONNECT_PHASE, source)

    def test_progress_mode_switches_back_after_indeterminate_phase(self):
        class FakeProgress:
            def __init__(self):
                self.events = []

            def configure(self, **kwargs):
                self.events.append(("configure", kwargs["mode"]))

            def start(self):
                self.events.append("start")

            def stop(self):
                self.events.append("stop")

        app = object.__new__(WhiteFloodApp)
        app.progress = FakeProgress()
        app._progress_mode = "determinate"

        app._set_progress_mode("indeterminate")
        app._set_progress_mode("determinate")

        self.assertEqual(
            app.progress.events,
            [
                ("configure", "indeterminate"),
                "start",
                "stop",
                ("configure", "determinate"),
            ],
        )

    def test_bundled_ffmpeg_tools_are_present_and_runnable(self):
        for name in ("ffmpeg", "ffprobe"):
            binary = bundled_binary(name)
            self.assertTrue(binary.is_file(), binary)
            completed = subprocess.run(
                [str(binary), "-hide_banner", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn(b"FFmpeg", completed.stdout + completed.stderr)

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

    def test_mask_canvas_change_callback_is_called_after_mask_commit(self):
        canvas = object.__new__(MaskCanvas)
        changes = []
        canvas._change_callback = lambda: changes.append(True)
        canvas._notify_change()
        self.assertEqual(changes, [True])

    def test_mask_canvas_can_pause_editing_during_processing(self):
        class FakeCanvas:
            def __init__(self):
                self.cursor = None

            def configure(self, **kwargs):
                self.cursor = kwargs["cursor"]

        canvas = object.__new__(MaskCanvas)
        canvas.canvas = FakeCanvas()
        canvas._tool = "brush"
        canvas._interactive = True
        canvas._active_start = (1, 1)
        canvas._active_points = [(1, 1)]

        canvas.set_interactive(False)
        self.assertFalse(canvas._interactive)
        self.assertIsNone(canvas._active_start)
        self.assertEqual(canvas._active_points, [])
        self.assertEqual(canvas.canvas.cursor, "arrow")

        canvas.set_interactive(True)
        self.assertTrue(canvas._interactive)
        self.assertEqual(canvas.canvas.cursor, "crosshair")

    def test_model_download_reports_progress_and_installs_atomically(self):
        class FakeResponse:
            headers = {"Content-Length": "4"}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _size):
                if hasattr(self, "sent"):
                    return b""
                self.sent = True
                return b"test"

        spec = ModelSpec(
            key="test",
            label="Test model",
            filename="test.onnx",
            relative_path=Path("assets") / "models" / "test.onnx",
            url="https://example.invalid/test.onnx",
            minimum_bytes=1,
        )
        events = []
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch("features.model_download.persistent_model_dir", return_value=Path(temp_dir)):
                with mock.patch("features.model_download.urllib.request.urlopen", return_value=FakeResponse()):
                    destination = download_model(spec, status_cb=events.append)
            self.assertEqual(destination.read_bytes(), b"test")
            self.assertEqual(events[-1]["percent"], 100)
            self.assertEqual(events[-1]["downloaded"], 4)
            self.assertFalse(Path(temp_dir, "test.onnx.part").exists())

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
        progress = []
        result = service.inpaint(
            source,
            mask,
            progress_cb=lambda done, total: progress.append((done, total)),
            processing_profile=PROCESSING_SUPER_FAST,
        )
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, source.size)
        self.assertEqual(progress[-1], (1, 1))
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

        super_fast_command = VideoProcessor._build_encoder_command(
            "ffmpeg.exe", "input.mp4", "output.partial.mp4", info, True,
            processing_profile=PROCESSING_SUPER_FAST,
        )
        thread_index = super_fast_command.index("-threads")
        self.assertEqual(super_fast_command[thread_index + 1], "4")

    def test_video_output_validation_rejects_dimension_drift(self):
        source = MediaInfo(1920, 1080, 30.0, 2.0, 60, False, 0)
        output = MediaInfo(1080, 1920, 30.0, 2.0, 60, False, 0)
        with self.assertRaises(VideoError):
            VideoProcessor._validate_output(source, output, 60)


if __name__ == "__main__":
    unittest.main()
