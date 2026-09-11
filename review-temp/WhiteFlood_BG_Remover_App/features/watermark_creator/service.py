from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Callable, Optional

from PIL import Image

from .visible import VisibleWatermarkConfig, apply_visible_watermark
from .invisible import (
    InvisiblePayload,
    InvisibleVerifyResult,
    embed_invisible_watermark,
    verify_invisible_watermark,
)

VALID_MODES = {"visible", "invisible", "hybrid"}
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass(frozen=True)
class CreatorResult:
    image: Image.Image
    mode: str
    invisible_repetitions: float = 0.0


def short_file_hash(path: str | Path, length: int = 10) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:max(6, min(12, int(length)))].upper()


def collision_safe_path(path: str | Path) -> Path:
    target = Path(path)
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    for index in range(1, 100000):
        candidate = target.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("Tidak dapat membuat nama output collision-safe.")


def metadata_for_save(image: Image.Image) -> dict:
    result = {}
    for key in ("dpi", "icc_profile", "exif"):
        value = image.info.get(key)
        if value:
            result[key] = value
    return result


class WatermarkCreatorService:
    def create(
        self,
        source: Image.Image,
        mode: str,
        visible_config: Optional[VisibleWatermarkConfig] = None,
        logo: Optional[Image.Image] = None,
        invisible_payload: Optional[InvisiblePayload] = None,
        invisible_strength: str = "balanced",
    ) -> CreatorResult:
        mode = str(mode).lower().strip()
        if mode not in VALID_MODES:
            raise ValueError(f"Mode watermark tidak dikenal: {mode}")
        original_size = source.size
        result = source.copy()
        repetitions = 0.0
        if mode in {"invisible", "hybrid"}:
            if invisible_payload is None:
                raise ValueError("Payload invisible wajib untuk mode invisible/hybrid.")
            embedded = embed_invisible_watermark(result, invisible_payload, strength=invisible_strength)
            result = embedded.image
            repetitions = embedded.repetitions
        if mode in {"visible", "hybrid"}:
            if visible_config is None:
                raise ValueError("Konfigurasi visible wajib untuk mode visible/hybrid.")
            result = apply_visible_watermark(result, visible_config, logo=logo)
        if result.size != original_size:
            raise RuntimeError("Watermark Creator mengubah dimensi sumber.")
        return CreatorResult(result, mode, repetitions)

    def verify(self, image: Image.Image, robust_scan: bool = True) -> InvisibleVerifyResult:
        return verify_invisible_watermark(image, robust_scan=robust_scan)

    @staticmethod
    def save(result: CreatorResult, destination: str | Path, metadata: Optional[dict] = None) -> Path:
        target = collision_safe_path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        suffix = target.suffix.lower()
        kwargs = dict(metadata or {})
        image = result.image
        if suffix in {".jpg", ".jpeg"}:
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            image.save(target, format="JPEG", quality=95, **{k: v for k, v in kwargs.items() if k != "exif" or v})
        else:
            fmt = "PNG" if suffix == ".png" else None
            image.save(target, format=fmt, **kwargs)
        with Image.open(target) as check:
            if check.size != result.image.size:
                raise RuntimeError("Dimensi output tersimpan tidak cocok dengan hasil creator.")
        return target

    def process_batch(
        self,
        source_dir: str | Path,
        output_dir: str | Path,
        mode: str,
        visible_config: Optional[VisibleWatermarkConfig],
        invisible_owner_id: str = "",
        invisible_strength: str = "balanced",
        logo: Optional[Image.Image] = None,
        recursive: bool = True,
        progress_cb: Optional[Callable[[int, int, Path], None]] = None,
        cancel_event=None,
    ) -> list[Path]:
        source_root = Path(source_dir).resolve()
        output_root = Path(output_dir).resolve()
        if source_root == output_root:
            raise ValueError("Folder output batch harus berbeda dari folder sumber.")
        iterator = source_root.rglob("*") if recursive else source_root.glob("*")
        files = sorted(p for p in iterator if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS)
        outputs: list[Path] = []
        for index, src in enumerate(files, 1):
            if cancel_event is not None and cancel_event.is_set():
                break
            relative = src.relative_to(source_root)
            destination = output_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as opened:
                has_alpha = opened.mode in {"RGBA", "LA", "PA"} or (
                    opened.mode == "P" and "transparency" in opened.info
                )
                source = opened.convert("RGBA") if has_alpha else opened.convert("RGB")
                metadata = metadata_for_save(opened)
            payload = None
            if mode in {"invisible", "hybrid"}:
                payload = InvisiblePayload.now(
                    owner_id=invisible_owner_id,
                    file_id=src.stem[:16] or "file",
                    short_hash=short_file_hash(src),
                )
            created = self.create(
                source,
                mode=mode,
                visible_config=visible_config,
                logo=logo,
                invisible_payload=payload,
                invisible_strength=invisible_strength,
            )
            outputs.append(self.save(created, destination, metadata=metadata))
            if progress_cb:
                progress_cb(index, len(files), src)
        return outputs
