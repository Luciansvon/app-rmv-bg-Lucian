"""Streaming FFmpeg video watermark processor."""

from dataclasses import dataclass
from pathlib import Path
import subprocess
import threading

from PIL import Image
import numpy as np

from .inpaint import LamaInpaintService
from ..performance import get_processing_profile
from .media import (
    MediaError,
    MediaInfo,
    bundled_binary,
    collision_safe_path,
    ensure_not_overwriting,
    probe_video,
)


class VideoError(RuntimeError):
    """A user-facing video processing failure."""

    def __init__(self, message, audio_incompatible=False):
        super().__init__(message)
        self.audio_incompatible = audio_incompatible


@dataclass(frozen=True)
class VideoResult:
    output_path: Path
    input_info: MediaInfo
    output_info: MediaInfo
    preview: Image.Image | None
    audio_copied: bool
    warning: str = ""


def _creation_flags():
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _terminate(process):
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=2)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=2)
        except Exception:
            pass


def _drain(pipe, target):
    try:
        target.append(pipe.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        target.append(str(exc))


class VideoProcessor:
    """Decode, process, and encode one video frame at a time."""

    def __init__(self, inpaint_service=None, ffmpeg_path=None, ffprobe_path=None):
        self.inpaint_service = inpaint_service or LamaInpaintService()
        self.ffmpeg_path = Path(ffmpeg_path) if ffmpeg_path else None
        self.ffprobe_path = Path(ffprobe_path) if ffprobe_path else None

    def _ffmpeg(self):
        return self.ffmpeg_path or bundled_binary("ffmpeg")

    def _ffprobe(self):
        return self.ffprobe_path or bundled_binary("ffprobe")

    def _probe(self, input_path):
        return probe_video(input_path, ffprobe_path=self._ffprobe())

    def extract_first_frame(self, input_path):
        source = Path(input_path)
        ffmpeg = self._ffmpeg()
        command = [
            str(ffmpeg),
            "-v", "error",
            "-i", str(source),
            "-map", "0:v:0",
            "-frames:v", "1",
            "-f", "image2pipe",
            "-vcodec", "png",
            "pipe:1",
        ]
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                creationflags=_creation_flags(),
            )
        except OSError as exc:
            raise VideoError(f"FFmpeg tidak bisa dijalankan: {exc}") from exc
        if completed.returncode != 0 or not completed.stdout:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise VideoError(detail or "Frame pertama video tidak bisa dibaca.")
        try:
            from io import BytesIO
            with Image.open(BytesIO(completed.stdout)) as frame:
                return frame.convert("RGB")
        except Exception as exc:
            raise VideoError(f"Frame pertama video tidak valid: {exc}") from exc

    def process(self, input_path, output_path, mask, cancel_event=None, progress_cb=None, processing_profile=None):
        source = Path(input_path)
        destination = ensure_not_overwriting(output_path)
        try:
            info = self._probe(source)
        except MediaError as exc:
            raise VideoError(str(exc)) from exc
        if mask.size != (info.width, info.height):
            raise VideoError(
                f"Ukuran mask harus {info.width}x{info.height}, bukan {mask.size[0]}x{mask.size[1]}."
            )
        if mask.getbbox() is None:
            raise VideoError("Mask watermark masih kosong.")
        if cancel_event is not None and cancel_event.is_set():
            raise VideoError("Proses video dibatalkan.")

        partial = destination.with_name(
            f"{destination.stem}.partial{destination.suffix or '.mp4'}"
        )
        if partial.exists():
            partial = collision_safe_path(partial)
        audio_copied = info.has_audio
        warnings = []
        if info.is_vfr:
            warnings.append(
                "Input VFR terdeteksi; output memakai FPS nominal/average untuk MVP."
            )
        processed_count = 0
        try:
            try:
                processed_count = self._run_pass(
                    source, partial, info, mask, cancel_event, progress_cb,
                    include_audio=info.has_audio, processing_profile=processing_profile,
                )
            except VideoError as exc:
                if (
                    not info.has_audio
                    or not exc.audio_incompatible
                    or (cancel_event is not None and cancel_event.is_set())
                ):
                    raise
                warnings.append(
                    "Audio tidak kompatibel saat remux; output video-only dibuat."
                )
                audio_copied = False
                if partial.exists():
                    partial.unlink()
                processed_count = self._run_pass(
                    source, partial, info, mask, cancel_event, progress_cb,
                    include_audio=False, processing_profile=processing_profile,
                )
            if cancel_event is not None and cancel_event.is_set():
                raise VideoError("Proses video dibatalkan.")
            output_info = self._probe(partial)
            self._validate_output(info, output_info, processed_count)
            if destination.exists():
                raise VideoError(f"File output sudah ada: {destination}")
            partial.replace(destination)
        except Exception:
            if partial.exists():
                partial.unlink()
            raise

        preview = getattr(self, "_last_preview", None)
        return VideoResult(
            output_path=destination,
            input_info=info,
            output_info=output_info,
            preview=preview.copy() if preview is not None else None,
            audio_copied=audio_copied,
            warning=" ".join(warnings),
        )

    @staticmethod
    def _looks_like_audio_mux_error(detail):
        text = (detail or "").lower()
        patterns = (
            "could not find tag for codec",
            "codec is not supported in the container",
            "could not write header",
            "error writing trailer",
            "invalid audio stream",
            "audio codec",
        )
        return any(pattern in text for pattern in patterns)

    @staticmethod
    def _validate_output(input_info, output_info, processed_count):
        if (output_info.width, output_info.height) != (input_info.width, input_info.height):
            raise VideoError(
                "Dimensi output video berubah dari ukuran frame input "
                f"{input_info.width}x{input_info.height}."
            )
        if output_info.fps <= 0 or abs(output_info.fps - input_info.fps) > 0.05:
            raise VideoError("FPS output video berbeda dari FPS nominal input.")
        if input_info.duration > 0 and output_info.duration > 0:
            tolerance = max(0.15, 2.0 / max(input_info.fps, 1.0))
            if abs(output_info.duration - input_info.duration) > tolerance:
                raise VideoError("Durasi output video berbeda terlalu jauh dari input.")
        if output_info.frame_count is not None and processed_count:
            if abs(output_info.frame_count - processed_count) > 2:
                raise VideoError("Jumlah frame output berbeda dari frame yang diproses.")

    def _run_pass(self, source, partial, info, mask, cancel_event, progress_cb, include_audio, processing_profile=None):
        ffmpeg = self._ffmpeg()
        frame_bytes = info.width * info.height * 3
        decoder = None
        encoder = None
        decoder_log_thread = None
        encoder_log_thread = None
        decoder_errors = []
        encoder_errors = []
        processed = 0
        self._last_preview = None
        try:
            decoder = subprocess.Popen(
                [
                    str(ffmpeg),
                    "-v", "error",
                    "-i", str(source),
                    "-map", "0:v:0",
                    "-f", "rawvideo",
                    "-pix_fmt", "bgr24",
                    "-vsync", "0",
                    "pipe:1",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=_creation_flags(),
            )
            decoder_log_thread = threading.Thread(
                target=_drain, args=(decoder.stderr, decoder_errors), daemon=True
            )
            decoder_log_thread.start()
            encoder_command = self._build_encoder_command(
                ffmpeg,
                source,
                partial,
                info,
                include_audio,
                processing_profile=processing_profile,
            )
            encoder = subprocess.Popen(
                encoder_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=_creation_flags(),
            )
            encoder_log_thread = threading.Thread(
                target=_drain, args=(encoder.stderr, encoder_errors), daemon=True
            )
            encoder_log_thread.start()
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise VideoError("Proses video dibatalkan.")
                chunk = decoder.stdout.read(frame_bytes)
                if not chunk:
                    break
                if len(chunk) != frame_bytes:
                    raise VideoError("FFmpeg mengembalikan frame video yang tidak lengkap.")
                bgr = np.frombuffer(chunk, dtype=np.uint8).reshape((info.height, info.width, 3))
                frame = Image.fromarray(bgr[:, :, ::-1].copy(), mode="RGB")
                if processing_profile:
                    processed_frame = self.inpaint_service.inpaint(
                        frame,
                        mask,
                        cancel_event,
                        processing_profile=processing_profile,
                    )
                else:
                    processed_frame = self.inpaint_service.inpaint(frame, mask, cancel_event)
                if self._last_preview is None:
                    self._last_preview = processed_frame.copy()
                output_bgr = np.asarray(processed_frame.convert("RGB"), dtype=np.uint8)[:, :, ::-1]
                encoder.stdin.write(output_bgr.tobytes())
                processed += 1
                if progress_cb is not None:
                    progress_cb(processed, info.frame_count)
            encoder.stdin.close()
            encoder.stdin = None
            decoder.stdout.close()
            decoder_rc = decoder.wait()
            encoder_rc = encoder.wait()
            for log_thread in (decoder_log_thread, encoder_log_thread):
                if log_thread is not None:
                    log_thread.join(timeout=2)
            if decoder_rc != 0:
                detail = decoder_errors[-1].strip() if decoder_errors else ""
                raise VideoError(detail or f"FFmpeg decode gagal ({decoder_rc}).")
            if encoder_rc != 0:
                detail = encoder_errors[-1].strip() if encoder_errors else ""
                raise VideoError(
                    detail or f"FFmpeg encode gagal ({encoder_rc}).",
                    audio_incompatible=include_audio and self._looks_like_audio_mux_error(detail),
                )
            if processed == 0:
                raise VideoError("Video tidak memiliki frame yang bisa diproses.")
            return processed
        except VideoError:
            _terminate(decoder)
            _terminate(encoder)
            raise
        except (BrokenPipeError, OSError) as exc:
            _terminate(decoder)
            _terminate(encoder)
            detail = encoder_errors[-1].strip() if encoder_errors else str(exc)
            raise VideoError(
                detail or "FFmpeg berhenti saat menulis frame.",
                audio_incompatible=include_audio and self._looks_like_audio_mux_error(detail),
            ) from exc
        finally:
            for process in (decoder, encoder):
                if process is not None:
                    for stream_name in ("stdin", "stdout", "stderr"):
                        try:
                            stream = getattr(process, stream_name, None)
                            if stream:
                                stream.close()
                        except Exception:
                            pass

    @staticmethod
    def _build_encoder_command(ffmpeg, source, partial, info, include_audio, processing_profile=None):
        command = [
            str(ffmpeg),
            "-y",
            "-v", "error",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{info.width}x{info.height}",
            "-r", f"{info.fps:.12f}".rstrip("0").rstrip("."),
            "-i", "pipe:0",
        ]
        if include_audio:
            command += [
                "-i", str(source),
                "-map", "0:v:0",
                "-map", "1:a:0?",
                "-c:a", "copy",
                "-shortest",
            ]
        else:
            command += ["-map", "0:v:0", "-an"]
        if processing_profile:
            profile = get_processing_profile(processing_profile)
            command += ["-threads", str(profile.ffmpeg_threads)]
        command += [
            "-c:v", "mpeg4",
            "-q:v", "3",
            "-movflags", "+faststart",
            "-f", "mp4",
            str(partial),
        ]
        return command
