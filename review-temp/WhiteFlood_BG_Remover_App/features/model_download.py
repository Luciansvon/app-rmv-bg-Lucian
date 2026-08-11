"""Persistent, verified model downloads with a Windows-native fallback."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request


COPY_CHUNK_BYTES = 4 * 1024 * 1024
BITS_STALL_TIMEOUT_SECONDS = 180


class ModelDownloadError(RuntimeError):
    """A user-facing model download or installation failure."""


@dataclass(frozen=True)
class ModelSpec:
    key: str
    label: str
    filename: str
    relative_path: Path
    url: str
    minimum_bytes: int = 1_000_000
    known_hash: str | None = None


LAMA_MODEL = ModelSpec(
    key="lama",
    label="LaMa watermark remover",
    filename="inpainting_lama_2025jan.onnx",
    relative_path=Path("assets") / "models" / "inpainting_lama_2025jan.onnx",
    url=(
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/"
        "47534e27c9851bb1128ccc0102f1145e27f23f98/models/"
        "inpainting_lama/inpainting_lama_2025jan.onnx"
    ),
    minimum_bytes=90_000_000,
    known_hash=(
        "sha256:7df918ac3921d3daf0aae1d219776cf0dc4e4935f035af81841b40adcf74fdf2"
    ),
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


def _emit_progress(status_cb, label, downloaded, total, phase, percent=None):
    if status_cb is None:
        return
    downloaded = max(0, int(downloaded or 0))
    total = max(0, int(total or 0))
    if total <= 0 and percent is None:
        status_cb({"kind": "phase_indeterminate", "message": phase})
        return
    if percent is None:
        percent = int(downloaded / total * 100) if total else 0
    status_cb({
        "kind": "model_download",
        "model": label,
        "phase": phase,
        "percent": max(0, min(100, int(percent))),
        "downloaded": downloaded,
        "total": total,
    })


def _new_hasher(algorithm):
    try:
        return hashlib.new(algorithm, usedforsecurity=False)
    except TypeError:
        return hashlib.new(algorithm)


def _hash_parts(known_hash):
    if not known_hash:
        return None, None
    text = str(known_hash).strip().lower()
    if ":" not in text:
        raise ModelDownloadError("Format hash model tidak valid.")
    algorithm, expected = text.split(":", 1)
    if not algorithm or not expected:
        raise ModelDownloadError("Format hash model tidak valid.")
    try:
        _new_hasher(algorithm)
    except (ValueError, TypeError) as exc:
        raise ModelDownloadError(f"Algoritma hash model tidak didukung: {algorithm}.") from exc
    return algorithm, expected


def verify_model_file(path, known_hash=None, minimum_bytes=1_000_000,
                      status_cb=None, label="Model AI",
                      progress_start=0, progress_end=100):
    """Validate model size and optional digest without loading it into RAM."""
    candidate = Path(path)
    if not candidate.is_file():
        raise ModelDownloadError(f"File model tidak ditemukan: {candidate}")
    total = candidate.stat().st_size
    if total < int(minimum_bytes):
        raise ModelDownloadError(
            f"File model terlalu kecil atau belum selesai ({total:,} byte)."
        )
    algorithm, expected = _hash_parts(known_hash)
    if algorithm is None:
        _emit_progress(
            status_cb, label, total, total, f"Memverifikasi {label}...",
            percent=progress_end,
        )
        return candidate

    hasher = _new_hasher(algorithm)
    checked = 0
    phase = f"Memverifikasi {label}..."
    span = max(0, int(progress_end) - int(progress_start))
    _emit_progress(
        status_cb, label, 0, total, phase, percent=progress_start
    )
    with candidate.open("rb") as source:
        while True:
            chunk = source.read(COPY_CHUNK_BYTES)
            if not chunk:
                break
            hasher.update(chunk)
            checked += len(chunk)
            mapped = int(progress_start) + int((checked / total) * span)
            _emit_progress(
                status_cb, label, checked, total, phase, percent=mapped
            )
    actual = hasher.hexdigest().lower()
    if actual != expected:
        raise ModelDownloadError(
            f"Hash {algorithm.upper()} model tidak cocok. File salah, rusak, atau belum selesai."
        )
    return candidate


def install_model_file(source_path, destination, known_hash=None,
                       minimum_bytes=1_000_000, status_cb=None,
                       label="Model AI"):
    """Copy, verify, and atomically install a user-selected model file."""
    source = Path(source_path)
    target = Path(destination)
    if not source.is_file():
        raise ModelDownloadError(f"File model tidak ditemukan: {source}")
    if source.resolve() == target.resolve():
        return verify_model_file(
            source,
            known_hash=known_hash,
            minimum_bytes=minimum_bytes,
            status_cb=status_cb,
            label=label,
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    handle, partial_name = tempfile.mkstemp(
        prefix=f"{target.name}.", suffix=".part", dir=target.parent
    )
    os.close(handle)
    partial = Path(partial_name)
    total = source.stat().st_size
    copied = 0
    phase = f"Menyalin {label} ke folder aplikasi..."
    try:
        _emit_progress(status_cb, label, 0, total, phase, percent=0)
        with source.open("rb") as input_file, partial.open("wb") as output_file:
            while True:
                chunk = input_file.read(COPY_CHUNK_BYTES)
                if not chunk:
                    break
                output_file.write(chunk)
                copied += len(chunk)
                mapped = int((copied / total) * 60) if total else 0
                _emit_progress(
                    status_cb, label, copied, total, phase, percent=mapped
                )
        verify_model_file(
            partial,
            known_hash=known_hash,
            minimum_bytes=minimum_bytes,
            status_cb=status_cb,
            label=label,
            progress_start=60,
            progress_end=100,
        )
        os.replace(partial, target)
        return target
    finally:
        if partial.exists():
            try:
                partial.unlink()
            except OSError:
                pass


def should_try_windows_fallback(error):
    if os.name != "nt":
        return False
    detail = str(error).lower()
    markers = (
        "connection", "disconnected", "timed out", "timeout", "proxy",
        "ssl", "certificate", "name resolution", "temporary failure",
        "github.com", "status code 403", "status code 407",
        "http error 403", "http error 407", "remote end closed",
        "tidak lengkap", "belum selesai", "hash",
    )
    return any(marker in detail for marker in markers)


def _powershell_path():
    found = shutil.which("powershell.exe") or shutil.which("powershell")
    if found:
        return found
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    candidate = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    return str(candidate) if candidate.is_file() else None


_BITS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Import-Module BitsTransfer -ErrorAction Stop
$job = $null
$completed = $false
try {
    $job = Start-BitsTransfer `
        -Source $env:WHITEFLOOD_BITS_SOURCE `
        -Destination $env:WHITEFLOOD_BITS_DESTINATION `
        -DisplayName 'WhiteFlood model download' `
        -Description 'WhiteFlood AI model' `
        -Priority Foreground `
        -ProxyUsage SystemDefault `
        -UseStoredCredential Proxy `
        -Asynchronous
    Write-Output ('WF_JOB|' + $job.JobId)
    while ($true) {
        if (Test-Path -LiteralPath $env:WHITEFLOOD_BITS_CANCEL) {
            throw 'Pengunduhan model dibatalkan.'
        }
        $job = Get-BitsTransfer -JobId $job.JobId -ErrorAction Stop
        Write-Output ('WF_PROGRESS|' + [int64]$job.BytesTransferred + '|' + [uint64]$job.BytesTotal + '|' + $job.JobState)
        if ($job.JobState -eq 'Transferred') {
            Complete-BitsTransfer -BitsJob $job -ErrorAction Stop
            $completed = $true
            Write-Output 'WF_DONE'
            break
        }
        if ($job.JobState -in @('Error', 'Cancelled', 'Acknowledged')) {
            $detail = if ($job.Error) { $job.Error.Description } else { $job.JobState }
            throw $detail
        }
        Start-Sleep -Milliseconds 250
    }
} catch {
    $detail = $_.Exception.Message -replace '[\r\n|]+', ' '
    Write-Output ('WF_ERROR|' + $detail)
    exit 1
} finally {
    if ($job -and -not $completed) {
        try {
            Get-BitsTransfer -JobId $job.JobId -ErrorAction SilentlyContinue |
                Remove-BitsTransfer -Confirm:$false -ErrorAction SilentlyContinue
        } catch {}
    }
}
"""


def download_with_bits(url, destination, known_hash=None, minimum_bytes=1_000_000,
                       status_cb=None, cancel_event=None, label="Model AI",
                       stall_timeout=BITS_STALL_TIMEOUT_SECONDS):
    """Download through Windows BITS using the signed-in user's proxy settings."""
    if os.name != "nt":
        raise ModelDownloadError("Jalur download Windows hanya tersedia di Windows.")
    powershell = _powershell_path()
    if not powershell:
        raise ModelDownloadError("Windows PowerShell tidak tersedia untuk menjalankan BITS.")

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, partial_name = tempfile.mkstemp(
        prefix=f"{target.name}.", suffix=".bits.part", dir=target.parent
    )
    os.close(handle)
    partial = Path(partial_name)
    partial.unlink()
    cancel_handle, cancel_name = tempfile.mkstemp(
        prefix="whiteflood-bits-cancel-", suffix=".flag"
    )
    os.close(cancel_handle)
    cancel_marker = Path(cancel_name)
    cancel_marker.unlink()

    environment = os.environ.copy()
    environment.update({
        "WHITEFLOOD_BITS_SOURCE": str(url),
        "WHITEFLOOD_BITS_DESTINATION": str(partial),
        "WHITEFLOOD_BITS_CANCEL": str(cancel_marker),
    })
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = None
    reader = None
    output_queue = queue.Queue()
    error_detail = ""
    completed = False
    last_bytes = -1
    last_progress_at = time.monotonic()
    phase = f"Mengunduh {label} lewat jaringan Windows kantor..."
    if status_cb is not None:
        status_cb({"kind": "phase_indeterminate", "message": phase})

    def read_output():
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            output_queue.put(line.rstrip("\r\n"))

    try:
        process = subprocess.Popen(
            [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", _BITS_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            env=environment,
        )
        reader = threading.Thread(target=read_output, name="whiteflood-bits-output", daemon=True)
        reader.start()

        cancel_requested = False
        while True:
            if cancel_event is not None and cancel_event.is_set() and not cancel_requested:
                cancel_marker.touch()
                cancel_requested = True
            try:
                line = output_queue.get(timeout=0.25)
            except queue.Empty:
                line = None

            if line:
                if line.startswith("WF_PROGRESS|"):
                    parts = line.split("|", 3)
                    try:
                        downloaded = max(0, int(parts[1]))
                        total = max(0, int(parts[2]))
                    except (ValueError, IndexError):
                        downloaded, total = 0, 0
                    if total >= (1 << 63) or total < downloaded:
                        total = 0
                    if downloaded != last_bytes:
                        last_bytes = downloaded
                        last_progress_at = time.monotonic()
                    mapped = int((downloaded / total) * 90) if total else None
                    _emit_progress(
                        status_cb, label, downloaded, total, phase, percent=mapped
                    )
                elif line.startswith("WF_ERROR|"):
                    error_detail = line.split("|", 1)[1].strip()
                elif line == "WF_DONE":
                    completed = True

            if not cancel_requested and time.monotonic() - last_progress_at > float(stall_timeout):
                error_detail = (
                    "Jalur Windows tidak menerima data selama "
                    f"{int(stall_timeout)} detik. Proxy atau GitHub kemungkinan diblokir."
                )
                cancel_marker.touch()
                cancel_requested = True

            if process.poll() is not None and output_queue.empty():
                break

        if reader is not None:
            reader.join(timeout=2)
        return_code = process.wait(timeout=5)
        if cancel_event is not None and cancel_event.is_set():
            raise ModelDownloadError("Pengunduhan model dibatalkan.")
        if return_code != 0 or not completed:
            raise ModelDownloadError(
                error_detail or f"BITS gagal dengan kode {return_code}."
            )
        verify_model_file(
            partial,
            known_hash=known_hash,
            minimum_bytes=minimum_bytes,
            status_cb=status_cb,
            label=label,
            progress_start=90,
            progress_end=100,
        )
        os.replace(partial, target)
        return target
    except (OSError, subprocess.SubprocessError) as exc:
        raise ModelDownloadError(f"BITS Windows gagal dijalankan: {exc}") from exc
    finally:
        if process is not None and process.poll() is None:
            try:
                cancel_marker.touch()
                process.wait(timeout=5)
            except Exception:
                process.terminate()
        for temporary in (partial, cancel_marker):
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass


def download_model(spec, cancel_event=None, status_cb=None):
    """Download one model, falling back to Windows BITS when HTTPS is blocked."""
    destination = persistent_model_dir() / spec.filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    primary_error = None

    try:
        request = urllib.request.Request(
            spec.url,
            headers={"User-Agent": "WhiteFlood/2.6 model downloader"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            phase = f"Mengunduh {spec.label}..."
            _emit_progress(status_cb, spec.label, 0, total, phase, percent=0)
            with partial.open("wb") as output:
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        raise ModelDownloadError("Pengunduhan model dibatalkan.")
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    downloaded += len(chunk)
                    mapped = int((downloaded / total) * 90) if total else None
                    _emit_progress(
                        status_cb, spec.label, downloaded, total, phase,
                        percent=mapped,
                    )
            if total and downloaded < total:
                raise ModelDownloadError(
                    f"Pengunduhan model tidak lengkap ({downloaded} dari {total} byte)."
                )
        verify_model_file(
            partial,
            known_hash=spec.known_hash,
            minimum_bytes=spec.minimum_bytes,
            status_cb=status_cb,
            label=spec.label,
            progress_start=90,
            progress_end=100,
        )
        os.replace(partial, destination)
        return destination
    except ModelDownloadError as exc:
        if cancel_event is not None and cancel_event.is_set():
            raise
        primary_error = exc
    except Exception as exc:
        primary_error = exc
    finally:
        if partial.exists():
            try:
                partial.unlink()
            except OSError:
                pass

    if should_try_windows_fallback(primary_error):
        try:
            return download_with_bits(
                spec.url,
                destination,
                known_hash=spec.known_hash,
                minimum_bytes=spec.minimum_bytes,
                status_cb=status_cb,
                cancel_event=cancel_event,
                label=spec.label,
            )
        except ModelDownloadError as bits_error:
            raise ModelDownloadError(
                f"Download HTTPS gagal: {primary_error}. "
                f"Jalur Windows juga gagal: {bits_error}"
            ) from bits_error
    raise ModelDownloadError(f"Gagal mengunduh model: {primary_error}") from primary_error
