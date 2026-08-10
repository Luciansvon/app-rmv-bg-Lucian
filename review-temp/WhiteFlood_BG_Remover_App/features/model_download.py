"""Persistent, UI-driven downloads for optional WhiteFlood model assets."""

from dataclasses import dataclass
import os
from pathlib import Path
import sys
import urllib.request


class ModelDownloadError(RuntimeError):
    """A user-facing model download failure."""


@dataclass(frozen=True)
class ModelSpec:
    key: str
    label: str
    filename: str
    relative_path: Path
    url: str
    minimum_bytes: int = 1_000_000


LAMA_MODEL = ModelSpec(
    key="lama",
    label="LaMa watermark remover",
    filename="inpainting_lama_2025jan.onnx",
    relative_path=Path("assets") / "models" / "inpainting_lama_2025jan.onnx",
    url=(
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "inpainting_lama/inpainting_lama_2025jan.onnx"
    ),
    minimum_bytes=10_000_000,
)


def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[1]
    return base / relative_path


def persistent_model_dir():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        root = Path(local_app_data)
    else:
        root = Path.home() / "AppData" / "Local"
    return root / "WhiteFlood" / "models"


def model_candidates(spec):
    """Return bundled/source and persistent user paths in lookup order."""
    return (
        resource_path(spec.relative_path),
        persistent_model_dir() / spec.filename,
    )


def find_model(spec):
    for candidate in model_candidates(spec):
        if candidate.is_file() and candidate.stat().st_size >= spec.minimum_bytes:
            return candidate
    return None


def download_model(spec, cancel_event=None, status_cb=None):
    """Download one model to a writable user directory and atomically install it."""
    destination = persistent_model_dir() / spec.filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")

    def emit(downloaded, total, percent=None):
        if status_cb is None:
            return
        if percent is None:
            percent = int(downloaded / total * 100) if total else 0
        status_cb({
            "kind": "model_download",
            "model": spec.label,
            "percent": max(0, min(100, int(percent))),
            "downloaded": max(0, int(downloaded)),
            "total": max(0, int(total)),
        })

    try:
        request = urllib.request.Request(
            spec.url,
            headers={"User-Agent": "WhiteFlood/2.5 model downloader"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            emit(0, total, 0)
            with partial.open("wb") as output:
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        raise ModelDownloadError("Pengunduhan model dibatalkan.")
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    downloaded += len(chunk)
                    emit(downloaded, total)
            if total and downloaded < total:
                raise ModelDownloadError(
                    f"Pengunduhan model tidak lengkap ({downloaded} dari {total} byte)."
                )

        if partial.stat().st_size < spec.minimum_bytes:
            raise ModelDownloadError("File model yang diunduh terlalu kecil atau rusak.")
        partial.replace(destination)
        emit(destination.stat().st_size, total or destination.stat().st_size, 100)
        return destination
    except ModelDownloadError:
        raise
    except Exception as exc:
        raise ModelDownloadError(f"Gagal mengunduh model: {exc}") from exc
    finally:
        if partial.exists():
            try:
                partial.unlink()
            except OSError:
                pass
