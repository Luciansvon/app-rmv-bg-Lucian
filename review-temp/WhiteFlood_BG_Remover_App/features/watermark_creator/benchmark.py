from __future__ import annotations

from dataclasses import asdict, dataclass
import io
import json
from pathlib import Path
import time
from typing import Callable

import numpy as np
from PIL import Image, ImageEnhance

from .invisible import InvisiblePayload, embed_invisible_watermark, verify_invisible_watermark
from .visible import VisibleWatermarkConfig, apply_visible_watermark


@dataclass(frozen=True)
class AttackResult:
    name: str
    detected: bool
    payload_valid: bool
    confidence: float
    elapsed_ms: int


@dataclass(frozen=True)
class BenchmarkReport:
    algorithm: str
    strength: str
    recovery_rate: float
    false_positive: bool
    psnr_db: float
    benchmark_passed: bool
    attacks: tuple[AttackResult, ...]

    def to_dict(self):
        result = asdict(self)
        result["attacks"] = [asdict(item) for item in self.attacks]
        return result


def _psnr(reference: Image.Image, changed: Image.Image) -> float:
    a = np.asarray(reference.convert("RGB"), dtype=np.float32)
    b = np.asarray(changed.convert("RGB"), dtype=np.float32)
    mse = float(np.mean((a - b) ** 2))
    if mse <= 1e-12:
        return 99.0
    return float(20 * np.log10(255.0 / np.sqrt(mse)))


def _jpeg_roundtrip(image: Image.Image, quality: int) -> Image.Image:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=False)
    buffer.seek(0)
    with Image.open(buffer) as reopened:
        return reopened.convert("RGB")


def _resize_roundtrip(image: Image.Image) -> Image.Image:
    w, h = image.size
    smaller = image.resize((max(1, round(w * 0.9)), max(1, round(h * 0.9))), Image.Resampling.LANCZOS)
    return smaller.resize((w, h), Image.Resampling.LANCZOS)


def _crop_light(image: Image.Image) -> Image.Image:
    w, h = image.size
    dx = max(1, round(w * 0.05))
    dy = max(1, round(h * 0.05))
    return image.crop((dx, dy, w - dx, h - dy))


def benchmark_invisible(
    source: Image.Image,
    payload: InvisiblePayload,
    strength: str = "balanced",
) -> BenchmarkReport:
    embedded_result = embed_invisible_watermark(source, payload, strength=strength)
    embedded = embedded_result.image
    visible_overlay = apply_visible_watermark(
        embedded,
        VisibleWatermarkConfig(
            text="VISIBLE TEST",
            font_size=max(16, source.width // 20),
            opacity=55,
            rotation=-25,
            pattern="diagonal_repeat",
            spacing_x=max(24, source.width // 14),
            spacing_y=max(24, source.height // 14),
        ),
    )
    attacks: list[tuple[str, Callable[[Image.Image], Image.Image]]] = [
        ("original_png", lambda im: im.copy()),
        ("jpeg_95", lambda im: _jpeg_roundtrip(im, 95)),
        ("jpeg_80", lambda im: _jpeg_roundtrip(im, 80)),
        ("resize_90_roundtrip", _resize_roundtrip),
        ("crop_5_percent", _crop_light),
        ("brightness_plus_10", lambda im: ImageEnhance.Brightness(im).enhance(1.10)),
        ("brightness_minus_10", lambda im: ImageEnhance.Brightness(im).enhance(0.90)),
        ("contrast_plus_10", lambda im: ImageEnhance.Contrast(im).enhance(1.10)),
        ("contrast_minus_10", lambda im: ImageEnhance.Contrast(im).enhance(0.90)),
        ("visible_overlay", lambda _im: visible_overlay.copy()),
    ]
    outcomes = []
    for name, attack in attacks:
        attacked = attack(embedded)
        started = time.perf_counter()
        verified = verify_invisible_watermark(attacked, robust_scan=name == "crop_5_percent")
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        same_payload = verified.payload == payload if verified.payload else False
        outcomes.append(AttackResult(
            name=name,
            detected=verified.detected and same_payload,
            payload_valid=verified.payload_valid and same_payload,
            confidence=verified.confidence,
            elapsed_ms=elapsed_ms,
        ))

    false_positive_result = verify_invisible_watermark(source, robust_scan=False)
    false_positive = bool(false_positive_result.detected)
    recovery = sum(1 for item in outcomes if item.payload_valid) / max(1, len(outcomes))
    required_names = {
        "original_png", "jpeg_95", "jpeg_80", "resize_90_roundtrip",
        "crop_5_percent", "brightness_plus_10", "brightness_minus_10",
        "contrast_plus_10", "contrast_minus_10", "visible_overlay",
    }
    by_name = {item.name: item for item in outcomes}
    benchmark_passed = (
        not false_positive
        and recovery >= 0.90
        and all(by_name[name].payload_valid for name in required_names)
        and _psnr(source, embedded) >= 34.0
    )
    return BenchmarkReport(
        algorithm="DCT-QIM-v0-experimental",
        strength=strength,
        recovery_rate=recovery,
        false_positive=false_positive,
        psnr_db=_psnr(source, embedded),
        benchmark_passed=benchmark_passed,
        attacks=tuple(outcomes),
    )


def save_benchmark_report(report: BenchmarkReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return destination
