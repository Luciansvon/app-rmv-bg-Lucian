"""VTracer adapter with validation and cancellation boundaries."""

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from .presets import get_preset


SUPPORTED_RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


class VectorizeError(RuntimeError):
    """A user-facing vectorization failure."""


@dataclass(frozen=True)
class VectorizeResult:
    input_path: Path
    preset: str
    svg_text: str
    byte_length: int


def _cancelled(cancel_event):
    return cancel_event is not None and cancel_event.is_set()


def _notify(status_cb, message):
    if status_cb is not None:
        status_cb(message)


def validate_svg_text(svg_text):
    if not svg_text or not svg_text.strip():
        raise VectorizeError("VTracer menghasilkan SVG kosong.")
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as exc:
        raise VectorizeError(f"Hasil SVG tidak valid: {exc}") from exc
    tag = root.tag.rsplit("}", 1)[-1].lower()
    if tag != "svg":
        raise VectorizeError("Hasil vector tidak memiliki root SVG.")
    if not any(element.tag.rsplit("}", 1)[-1].lower() in {
        "path", "polygon", "polyline", "rect", "circle", "ellipse", "line",
    }
               for element in root.iter() if element is not root):
        raise VectorizeError("Hasil SVG tidak memiliki elemen gambar.")
    return svg_text


class VectorizeService:
    """Convert one raster image using the pinned VTracer Python binding."""

    package_name = "vtracer"
    package_version = "0.6.15"

    def convert(self, input_path, preset, cancel_event=None, status_cb=None):
        source = Path(input_path)
        if not source.is_file():
            raise VectorizeError(f"File input tidak ditemukan: {source}")
        if source.suffix.lower() not in SUPPORTED_RASTER_EXTENSIONS:
            raise VectorizeError("Format vectorize harus PNG, JPG, JPEG, WebP, atau BMP.")
        if _cancelled(cancel_event):
            raise VectorizeError("Vectorize dibatalkan.")

        try:
            import vtracer
        except ImportError as exc:
            raise VectorizeError(
                "Dependency VTracer belum tersedia. Pasang vtracer==0.6.15 "
                "pada environment aplikasi."
            ) from exc
        try:
            installed_version = package_version(self.package_name)
        except PackageNotFoundError:
            installed_version = None
        if installed_version and installed_version != self.package_version:
            raise VectorizeError(
                f"Versi VTracer {installed_version} terdeteksi; WhiteFlood membutuhkan "
                f"vtracer=={self.package_version}."
            )
        converter = getattr(vtracer, "convert_image_to_svg_py", None)
        if not callable(converter):
            raise VectorizeError(
                "Binding VTracer tidak menyediakan convert_image_to_svg_py "
                "yang diperlukan WhiteFlood."
            )

        selected = get_preset(preset)
        _notify(status_cb, "Menyiapkan vectorize lokal...")
        with tempfile.TemporaryDirectory(prefix="whiteflood-vector-") as temp_dir:
            temp_svg = Path(temp_dir) / "result.svg"
            try:
                converter(
                    str(source),
                    str(temp_svg),
                    **dict(selected.config),
                )
            except Exception as exc:
                raise VectorizeError(f"VTracer gagal mengubah gambar: {exc}") from exc

            if _cancelled(cancel_event):
                raise VectorizeError("Vectorize dibatalkan.")
            if not temp_svg.is_file() or temp_svg.stat().st_size == 0:
                raise VectorizeError("VTracer tidak menghasilkan file SVG.")
            try:
                svg_text = temp_svg.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise VectorizeError("Hasil SVG tidak bisa dibaca sebagai UTF-8.") from exc

        validate_svg_text(svg_text)
        _notify(status_cb, "SVG valid dan siap disimpan.")
        return VectorizeResult(
            input_path=source,
            preset=selected.key,
            svg_text=svg_text,
            byte_length=len(svg_text.encode("utf-8")),
        )

    @staticmethod
    def save(result, output_path):
        destination = Path(output_path)
        if destination.exists():
            raise VectorizeError(f"File output sudah ada: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_path = destination.with_name(destination.name + ".tmp")
        try:
            temp_path.write_text(result.svg_text, encoding="utf-8", newline="\n")
            validate_svg_text(temp_path.read_text(encoding="utf-8"))
            temp_path.replace(destination)
        finally:
            if temp_path.exists():
                temp_path.unlink()
        return destination
