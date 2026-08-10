"""Local media validation, bundled binary lookup, and collision-safe paths."""

from dataclasses import dataclass
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


class MediaError(RuntimeError):
    """A user-facing media or FFmpeg failure."""


@dataclass(frozen=True)
class MediaInfo:
    width: int
    height: int
    fps: float
    duration: float
    frame_count: int | None
    has_audio: bool
    rotation: int
    video_codec: str = ""
    audio_codec: str = ""
    is_vfr: bool = False


def app_root():
    if getattr(__import__("sys"), "frozen", False):
        return Path(__import__("sys")._MEIPASS)
    return Path(__file__).resolve().parents[2]


def resource_path(relative_path):
    return app_root() / relative_path


def bundled_binary(name):
    filename = name if name.lower().endswith(".exe") else f"{name}.exe"
    candidates = (
        resource_path(Path("ffmpeg") / filename),
        resource_path(Path("media") / "ffmpeg" / filename),
        resource_path(Path("assets") / "ffmpeg" / filename),
        resource_path(Path("tools") / "ffmpeg" / filename),
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise MediaError(
        f"{filename} belum tersedia di bundle WhiteFlood. "
        "Tambahkan binary FFmpeg LGPL yang dipin di folder ffmpeg."
    )


def _creation_flags():
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _run_capture(command):
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            creationflags=_creation_flags(),
        )
    except OSError as exc:
        raise MediaError(f"Tidak bisa menjalankan {command[0]}: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise MediaError(detail or f"Perintah gagal dengan kode {completed.returncode}.")
    return completed.stdout


def ffprobe_json(input_path, ffprobe_path=None):
    ffprobe = Path(ffprobe_path) if ffprobe_path else bundled_binary("ffprobe")
    command = [
        str(ffprobe),
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(Path(input_path)),
    ]
    try:
        return json.loads(_run_capture(command).decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise MediaError("FFprobe mengembalikan metadata yang tidak valid.") from exc


def _parse_fraction(value, default=0.0):
    if not value or value in {"0/0", "N/A"}:
        return default
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default


def _parse_rotation(stream):
    tags = stream.get("tags") or {}
    side_data = stream.get("side_data_list") or []
    raw = tags.get("rotate")
    if raw is None:
        for item in side_data:
            if "rotation" in item:
                raw = item["rotation"]
                break
    try:
        value = int(round(float(raw or 0))) % 360
        return value if value in {0, 90, 180, 270} else 0
    except (TypeError, ValueError):
        return 0


def probe_video(input_path, ffprobe_path=None):
    source = Path(input_path)
    if not source.is_file():
        raise MediaError(f"Video tidak ditemukan: {source}")
    if source.suffix.lower() not in VIDEO_EXTENSIONS:
        raise MediaError("Format video harus MP4, MOV, MKV, AVI, atau WebM.")
    payload = ffprobe_json(source, ffprobe_path=ffprobe_path)
    streams = payload.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        raise MediaError("File tidak memiliki stream video yang valid.")
    encoded_width = int(video.get("width") or 0)
    encoded_height = int(video.get("height") or 0)
    if encoded_width <= 0 or encoded_height <= 0:
        raise MediaError("Ukuran frame video tidak valid.")
    fps_text = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/0"
    fps = _parse_fraction(fps_text, 0.0)
    if fps <= 0:
        raise MediaError("FPS video tidak bisa ditentukan.")
    format_data = payload.get("format") or {}
    try:
        duration = float(format_data.get("duration") or video.get("duration") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    raw_frames = video.get("nb_frames")
    try:
        frame_count = int(raw_frames) if raw_frames not in (None, "N/A") else None
    except (TypeError, ValueError):
        frame_count = None
    if frame_count is None and duration > 0:
        frame_count = max(1, round(duration * fps))
    rotation = _parse_rotation(video)
    if rotation in {90, 270}:
        width, height = encoded_height, encoded_width
    else:
        width, height = encoded_width, encoded_height
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    r_rate = _parse_fraction(video.get("r_frame_rate"), fps)
    is_vfr = abs(r_rate - fps) > 0.01 if r_rate > 0 else False
    return MediaInfo(
        width=width,
        height=height,
        fps=fps,
        duration=max(0.0, duration),
        frame_count=frame_count,
        has_audio=audio is not None,
        rotation=rotation,
        video_codec=str(video.get("codec_name") or ""),
        audio_codec=str(audio.get("codec_name") or "") if audio else "",
        is_vfr=is_vfr,
    )


def collision_safe_path(path):
    destination = Path(path)
    if not destination.exists():
        return destination
    for index in range(1, 10000):
        candidate = destination.with_name(
            f"{destination.stem} ({index}){destination.suffix}"
        )
        if not candidate.exists():
            return candidate
    raise MediaError(f"Terlalu banyak file dengan nama yang sama: {destination.name}")


def ensure_not_overwriting(path):
    destination = Path(path)
    if destination.exists():
        raise MediaError(f"File output sudah ada: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination
