"""LaMa ONNX inpainting with source-size and alpha-safe composition."""

from pathlib import Path
import gc

from PIL import Image
import numpy as np

from .media import resource_path


class LamaInpaintError(RuntimeError):
    """A user-facing LaMa failure."""


MODEL_RELATIVE_PATH = Path("assets") / "models" / "inpainting_lama_2025jan.onnx"
MODEL_INPUT_SIZE = 512
TILE_OVERLAP = 64


def _cancelled(cancel_event):
    return cancel_event is not None and cancel_event.is_set()


class LamaInpaintService:
    """Lazy ONNX Runtime wrapper for OpenCV Zoo's LaMa model."""

    def __init__(self, model_path=None):
        self.model_path = Path(model_path) if model_path else resource_path(MODEL_RELATIVE_PATH)
        self._session = None

    @property
    def is_loaded(self):
        return self._session is not None

    def load(self):
        if self._session is not None:
            return self._session
        if not self.model_path.is_file():
            raise LamaInpaintError(
                f"Model LaMa tidak ditemukan: {self.model_path}. "
                "Tambahkan model ONNX OpenCV Zoo ke assets/models."
            )
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise LamaInpaintError("ONNX Runtime belum tersedia untuk LaMa.") from exc

        options = ort.SessionOptions()
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
        try:
            providers = ["CPUExecutionProvider"]
            available = set(ort.get_available_providers())
            providers = [item for item in providers if item in available] or None
            self._session = ort.InferenceSession(
                str(self.model_path),
                sess_options=options,
                providers=providers,
            )
        except Exception as exc:
            raise LamaInpaintError(f"Model LaMa gagal dimuat: {exc}") from exc
        return self._session

    def unload(self):
        session = self._session
        self._session = None
        if session is not None:
            try:
                del session
                gc.collect()
            except Exception:
                pass

    def inpaint(self, image, mask, cancel_event=None):
        if not isinstance(image, Image.Image) or not isinstance(mask, Image.Image):
            raise LamaInpaintError("Input inpaint harus berupa PIL.Image.")
        if image.size != mask.size:
            raise LamaInpaintError(
                f"Ukuran gambar dan mask berbeda: {image.size} vs {mask.size}."
            )
        if _cancelled(cancel_event):
            raise LamaInpaintError("Proses watermark dibatalkan.")

        source_has_alpha = image.mode in {"RGBA", "LA", "PA"} or (
            image.mode == "P" and "transparency" in image.info
        )
        source_rgba = image.convert("RGBA") if source_has_alpha else None
        source_rgb = image.convert("RGB")
        source_mask = mask.convert("L")
        mask_array = np.asarray(source_mask, dtype=np.uint8)
        if not np.any(mask_array > 0):
            raise LamaInpaintError("Mask watermark masih kosong.")

        session = self.load()
        bbox = source_mask.getbbox()
        if bbox is None:
            raise LamaInpaintError("Mask watermark masih kosong.")
        tiles = self._build_tiles(bbox, source_rgb.size)
        result = np.asarray(source_rgb, dtype=np.uint8).copy()
        for index, box in enumerate(tiles, 1):
            if _cancelled(cancel_event):
                raise LamaInpaintError("Proses watermark dibatalkan.")
            x0, y0, x1, y1 = box
            crop_image = source_rgb.crop(box)
            crop_mask = source_mask.crop(box)
            crop_mask_array = np.asarray(crop_mask, dtype=np.uint8)
            if not np.any(crop_mask_array > 0):
                continue
            inferred = self._infer_tile(session, crop_image, crop_mask)
            target_width = x1 - x0
            target_height = y1 - y0
            if inferred.size != (target_width, target_height):
                inferred = inferred.resize((target_width, target_height), Image.Resampling.LANCZOS)
            inferred_array = np.asarray(inferred, dtype=np.uint8)
            region_mask = crop_mask_array > 0
            result[y0:y1, x0:x1] = np.where(
                region_mask[..., None],
                inferred_array,
                result[y0:y1, x0:x1],
            )

        output = Image.fromarray(result, mode="RGB")
        if source_rgba is not None:
            output.putalpha(source_rgba.getchannel("A"))
        return output

    @staticmethod
    def _build_tiles(bbox, size, context=None):
        width, height = size
        left, top, right, bottom = bbox
        if context is None:
            context = min(256, max(32, int(max(width, height) * 0.08)))
        outer = (
            max(0, left - context),
            max(0, top - context),
            min(width, right + context),
            min(height, bottom + context),
        )
        x_positions = LamaInpaintService._axis_positions(
            outer[0], outer[2], width
        )
        y_positions = LamaInpaintService._axis_positions(
            outer[1], outer[3], height
        )
        return [
            (x, y, min(width, x + MODEL_INPUT_SIZE), min(height, y + MODEL_INPUT_SIZE))
            for y in y_positions
            for x in x_positions
        ]

    @staticmethod
    def _axis_positions(start, end, limit):
        tile = MODEL_INPUT_SIZE
        if limit <= tile:
            return [0]
        max_start = limit - tile
        start = max(0, min(int(start), max_start))
        end = max(start, min(int(end), limit))
        if end - start <= tile:
            return [start]
        step = tile - TILE_OVERLAP
        positions = []
        position = start
        while True:
            clamped = min(position, max_start)
            if not positions or clamped != positions[-1]:
                positions.append(clamped)
            if clamped + tile >= end:
                break
            position += step
        return positions

    @staticmethod
    def _infer_tile(session, image, mask):
        resized_image = image.resize(
            (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE), Image.Resampling.LANCZOS
        )
        resized_mask = mask.resize(
            (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE), Image.Resampling.NEAREST
        )
        # OpenCV Zoo's lama.py uses OpenCV's native BGR blob and no RGB swap.
        image_bgr = np.asarray(resized_image, dtype=np.float32)[:, :, ::-1]
        image_blob = (image_bgr / 255.0).transpose(2, 0, 1)[None, ...].astype(np.float32)
        mask_blob = (np.asarray(resized_mask, dtype=np.uint8) > 0).astype(np.float32)[None, None, ...]
        try:
            outputs = session.run(None, {"image": image_blob, "mask": mask_blob})
        except Exception as exc:
            raise LamaInpaintError(f"Inferensi LaMa gagal: {exc}") from exc
        if not outputs:
            raise LamaInpaintError("LaMa tidak mengembalikan output.")
        output = np.asarray(outputs[0])
        if output.ndim == 4:
            output = output[0]
        if output.ndim != 3 or output.shape[0] != 3:
            raise LamaInpaintError(f"Shape output LaMa tidak didukung: {output.shape}")
        output = np.transpose(output, (1, 2, 0))
        output = np.clip(output, 0, 255).astype(np.uint8)
        return Image.fromarray(output[:, :, ::-1], mode="RGB")
