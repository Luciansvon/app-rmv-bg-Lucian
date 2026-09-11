from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import struct
import time
import zlib
from typing import Iterable, Optional

import numpy as np
from PIL import Image

FRAME_MAGIC = b"WFI1"
FRAME_BYTES = 64
FRAME_BITS = FRAME_BYTES * 8
MAX_PAYLOAD_BYTES = FRAME_BYTES - len(FRAME_MAGIC) - 1 - 4
COEFF_POS = (3, 2)
TILE_W = 32
TILE_H = 16
assert TILE_W * TILE_H == FRAME_BITS
STRENGTH_STEPS = {"light": 24.0, "balanced": 40.0, "strong": 56.0}


def _dct_matrix() -> np.ndarray:
    c = np.empty((8, 8), dtype=np.float32)
    for u in range(8):
        alpha = np.sqrt(1 / 8) if u == 0 else np.sqrt(2 / 8)
        for x in range(8):
            c[u, x] = alpha * np.cos(((2 * x + 1) * u * np.pi) / 16)
    return c


_DCT = _dct_matrix()


@dataclass(frozen=True)
class InvisiblePayload:
    owner_id: str
    file_id: str
    created_at: int
    short_hash: str
    schema_version: int = 1

    @classmethod
    def now(cls, owner_id: str, file_id: str, short_hash: str, schema_version: int = 1):
        return cls(
            owner_id=owner_id,
            file_id=file_id,
            created_at=int(time.time()),
            short_hash=short_hash,
            schema_version=schema_version,
        )

    @property
    def created_at_iso(self) -> str:
        return datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat()


@dataclass(frozen=True)
class InvisibleEmbedResult:
    image: Image.Image
    strength: str
    block_count: int
    repetitions: float


@dataclass(frozen=True)
class InvisibleVerifyResult:
    detected: bool
    payload_valid: bool
    payload: Optional[InvisiblePayload]
    confidence: float
    strength: str
    pixel_offset: tuple[int, int] = (0, 0)
    phase: int = 0
    message: str = ""


def _bounded_utf8(value: str, maximum: int, field: str) -> bytes:
    raw = str(value).encode("utf-8")
    if not raw:
        raise ValueError(f"{field} tidak boleh kosong.")
    if len(raw) > maximum:
        raise ValueError(f"{field} maksimal {maximum} byte UTF-8.")
    return raw


def encode_payload(payload: InvisiblePayload) -> bytes:
    owner = _bounded_utf8(payload.owner_id, 16, "owner_id")
    file_id = _bounded_utf8(payload.file_id, 16, "file_id")
    short_hash = _bounded_utf8(payload.short_hash, 12, "short_hash")
    if not 1 <= int(payload.schema_version) <= 255:
        raise ValueError("schema_version harus 1..255.")
    if not 0 <= int(payload.created_at) <= 0xFFFFFFFF:
        raise ValueError("created_at di luar rentang epoch 32-bit.")
    data = bytearray()
    data.extend(struct.pack(">BI", int(payload.schema_version), int(payload.created_at)))
    for part in (owner, file_id, short_hash):
        data.append(len(part))
        data.extend(part)
    if len(data) > MAX_PAYLOAD_BYTES:
        raise ValueError("Payload terlalu besar untuk frame invisible watermark v1.")
    return bytes(data)


def decode_payload(data: bytes) -> InvisiblePayload:
    if len(data) < 8:
        raise ValueError("Payload terlalu pendek.")
    schema, created_at = struct.unpack(">BI", data[:5])
    cursor = 5
    values = []
    for field in ("owner_id", "file_id", "short_hash"):
        if cursor >= len(data):
            raise ValueError(f"Payload terpotong pada {field}.")
        size = data[cursor]
        cursor += 1
        if size <= 0 or cursor + size > len(data):
            raise ValueError(f"Panjang {field} tidak valid.")
        values.append(data[cursor:cursor + size].decode("utf-8"))
        cursor += size
    return InvisiblePayload(
        owner_id=values[0],
        file_id=values[1],
        created_at=created_at,
        short_hash=values[2],
        schema_version=schema,
    )


def _frame_bytes(payload: InvisiblePayload) -> bytes:
    body = encode_payload(payload)
    header = FRAME_MAGIC + bytes([len(body)]) + body
    crc = zlib.crc32(header) & 0xFFFFFFFF
    frame = header + struct.pack(">I", crc)
    return frame.ljust(FRAME_BYTES, b"\x00")


def _parse_frame(frame: bytes) -> InvisiblePayload:
    if len(frame) != FRAME_BYTES or not frame.startswith(FRAME_MAGIC):
        raise ValueError("Magic invisible watermark tidak cocok.")
    payload_len = frame[len(FRAME_MAGIC)]
    if payload_len <= 0 or payload_len > MAX_PAYLOAD_BYTES:
        raise ValueError("Panjang payload frame tidak valid.")
    body_end = len(FRAME_MAGIC) + 1 + payload_len
    header = frame[:body_end]
    expected_crc = struct.unpack(">I", frame[body_end:body_end + 4])[0]
    actual_crc = zlib.crc32(header) & 0xFFFFFFFF
    if expected_crc != actual_crc:
        raise ValueError("Checksum invisible watermark tidak cocok.")
    return decode_payload(frame[len(FRAME_MAGIC) + 1:body_end])


def _bytes_to_bits(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8), bitorder="big")


def _bits_to_bytes(bits: np.ndarray) -> bytes:
    bits = np.asarray(bits, dtype=np.uint8)
    if bits.size != FRAME_BITS:
        raise ValueError("Jumlah bit frame tidak cocok.")
    return np.packbits(bits, bitorder="big").tobytes()


def _image_rgb_alpha(image: Image.Image):
    has_alpha = image.mode in {"RGBA", "LA", "PA"} or (
        image.mode == "P" and "transparency" in image.info
    )
    rgba = image.convert("RGBA")
    rgb = np.asarray(rgba.convert("RGB"), dtype=np.float32)
    alpha = np.asarray(rgba.getchannel("A"), dtype=np.uint8) if has_alpha else None
    return rgb, alpha, has_alpha


def _block_views(channel: np.ndarray, offset_x: int = 0, offset_y: int = 0):
    h, w = channel.shape
    usable_h = ((h - offset_y) // 8) * 8
    usable_w = ((w - offset_x) // 8) * 8
    if usable_h <= 0 or usable_w <= 0:
        return None, None
    view = channel[offset_y:offset_y + usable_h, offset_x:offset_x + usable_w]
    hb, wb = usable_h // 8, usable_w // 8
    blocks = view.reshape(hb, 8, wb, 8).transpose(0, 2, 1, 3).reshape(-1, 8, 8)
    return blocks, (hb, wb, usable_h, usable_w)


def _dct_blocks(blocks: np.ndarray) -> np.ndarray:
    centered = blocks.astype(np.float32) - 128.0
    return _DCT @ centered @ _DCT.T


def _idct_blocks(coeff: np.ndarray) -> np.ndarray:
    return (_DCT.T @ coeff @ _DCT) + 128.0


def _valid_blocks(alpha: Optional[np.ndarray], geometry, offset_x=0, offset_y=0) -> np.ndarray:
    if alpha is None:
        hb, wb, *_ = geometry
        return np.ones(hb * wb, dtype=bool)
    alpha_blocks, _ = _block_views(alpha.astype(np.float32), offset_x, offset_y)
    return alpha_blocks.mean(axis=(1, 2)) >= 220


def _step_for_strength(strength: str) -> float:
    try:
        return float(STRENGTH_STEPS[strength])
    except KeyError as exc:
        raise ValueError(f"Strength tidak dikenal: {strength}") from exc


def embed_invisible_watermark(
    image: Image.Image,
    payload: InvisiblePayload,
    strength: str = "balanced",
) -> InvisibleEmbedResult:
    step = _step_for_strength(strength)
    rgb, alpha, has_alpha = _image_rgb_alpha(image)
    y = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    blocks, geometry = _block_views(y)
    if blocks is None:
        raise ValueError("Gambar terlalu kecil untuk invisible watermark.")
    valid_mask = _valid_blocks(alpha, geometry)
    valid_indices = np.flatnonzero(valid_mask)
    if valid_indices.size < FRAME_BITS:
        raise ValueError(
            f"Butuh minimal {FRAME_BITS} blok 8x8 yang layak; tersedia {valid_indices.size}."
        )

    frame_bits = _bytes_to_bits(_frame_bytes(payload))
    coeff = _dct_blocks(blocks)
    u, v = COEFF_POS
    selected = coeff[valid_indices, u, v]
    hb, wb, usable_h, usable_w = geometry
    rows = valid_indices // wb
    cols = valid_indices % wb
    bit_indices = (rows % TILE_H) * TILE_W + (cols % TILE_W)
    target_bits = frame_bits[bit_indices].astype(np.int32)
    q = np.rint(selected / step).astype(np.int32)
    mismatch = (np.abs(q) % 2) != target_bits
    residual = selected - q * step
    direction = np.where(residual >= 0, 1, -1)
    direction[(q == 0) & (direction < 0)] = 1
    q[mismatch] += direction[mismatch]
    coeff[valid_indices, u, v] = q.astype(np.float32) * step

    rebuilt = _idct_blocks(coeff)
    rebuilt_plane = rebuilt.reshape(hb, wb, 8, 8).transpose(0, 2, 1, 3).reshape(usable_h, usable_w)
    new_y = y.copy()
    new_y[:usable_h, :usable_w] = np.clip(rebuilt_plane, 0, 255)
    delta = (new_y - y)[:, :, None]
    out_rgb = np.clip(rgb + delta, 0, 255).astype(np.uint8)
    out = Image.fromarray(out_rgb, mode="RGB")
    if has_alpha:
        out = out.convert("RGBA")
        out.putalpha(Image.fromarray(alpha, mode="L"))
    if out.size != image.size:
        raise RuntimeError("Invisible watermark mengubah dimensi sumber.")
    return InvisibleEmbedResult(
        image=out,
        strength=strength,
        block_count=int(valid_indices.size),
        repetitions=float(valid_indices.size / FRAME_BITS),
    )


def _extract_sequence(image: Image.Image, strength: str, offset_x: int, offset_y: int):
    step = _step_for_strength(strength)
    rgb, alpha, _ = _image_rgb_alpha(image)
    y = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    blocks, geometry = _block_views(y, offset_x, offset_y)
    if blocks is None:
        empty = np.array([], dtype=np.uint8)
        return empty, empty.astype(np.int32), empty.astype(np.int32)
    valid_mask = _valid_blocks(alpha, geometry, offset_x, offset_y)
    valid_indices = np.flatnonzero(valid_mask)
    if valid_indices.size < max(64, FRAME_BITS // 2):
        empty = np.array([], dtype=np.uint8)
        return empty, empty.astype(np.int32), empty.astype(np.int32)
    hb, wb, *_ = geometry
    coeff = _dct_blocks(blocks)
    u, v = COEFF_POS
    q = np.rint(coeff[valid_indices, u, v] / step).astype(np.int32)
    bits = (np.abs(q) % 2).astype(np.uint8)
    rows = (valid_indices // wb).astype(np.int32)
    cols = (valid_indices % wb).astype(np.int32)
    return bits, rows, cols


def _candidate_tile_phases(sequence: np.ndarray, rows: np.ndarray, cols: np.ndarray, limit: int = 12):
    magic_bits = _bytes_to_bits(FRAME_MAGIC)
    scored = []
    for phase_y in range(TILE_H):
        mapped_rows = (rows + phase_y) % TILE_H
        for phase_x in range(TILE_W):
            mapped = mapped_rows * TILE_W + ((cols + phase_x) % TILE_W)
            mask = mapped < magic_bits.size
            if not np.any(mask):
                continue
            score = float(np.mean(sequence[mask] == magic_bits[mapped[mask]]))
            scored.append((score, phase_x, phase_y))
    scored.sort(reverse=True)
    return scored[:limit]


def _decode_for_tile_phase(sequence: np.ndarray, rows: np.ndarray, cols: np.ndarray, phase_x: int, phase_y: int):
    mapped = ((rows + int(phase_y)) % TILE_H) * TILE_W + ((cols + int(phase_x)) % TILE_W)
    counts = np.bincount(mapped, minlength=FRAME_BITS).astype(np.float32)
    ones = np.bincount(mapped, weights=sequence, minlength=FRAME_BITS).astype(np.float32)
    if np.any(counts == 0):
        return None, 0.0
    ratios = ones / counts
    bits = (ratios >= 0.5).astype(np.uint8)
    margin = np.abs(ratios - 0.5) * 2.0
    confidence = float(np.mean(margin))
    return bits, confidence


def verify_invisible_watermark(
    image: Image.Image,
    strengths: Iterable[str] = ("balanced", "strong", "light"),
    robust_scan: bool = True,
) -> InvisibleVerifyResult:
    offsets = [(0, 0)]
    if robust_scan:
        offsets.extend((x, y) for y in range(8) for x in range(8) if (x, y) != (0, 0))
    best_confidence = 0.0
    best_meta = ("balanced", (0, 0), 0)
    for strength in strengths:
        _step_for_strength(strength)
        for offset_x, offset_y in offsets:
            sequence, rows, cols = _extract_sequence(image, strength, offset_x, offset_y)
            if sequence.size < max(64, FRAME_BITS // 2):
                continue
            for magic_score, phase_x, phase_y in _candidate_tile_phases(sequence, rows, cols):
                if magic_score < 0.72:
                    continue
                bits, confidence = _decode_for_tile_phase(sequence, rows, cols, phase_x, phase_y)
                phase = phase_y * TILE_W + phase_x
                if bits is None:
                    continue
                best_confidence = max(best_confidence, confidence)
                if confidence >= best_confidence:
                    best_meta = (strength, (offset_x, offset_y), phase)
                try:
                    payload = _parse_frame(_bits_to_bytes(bits))
                except Exception:
                    continue
                return InvisibleVerifyResult(
                    detected=True,
                    payload_valid=True,
                    payload=payload,
                    confidence=confidence,
                    strength=strength,
                    pixel_offset=(offset_x, offset_y),
                    phase=phase,
                    message="Invisible watermark terdeteksi dan checksum valid.",
                )
    return InvisibleVerifyResult(
        detected=False,
        payload_valid=False,
        payload=None,
        confidence=best_confidence,
        strength=best_meta[0],
        pixel_offset=best_meta[1],
        phase=best_meta[2],
        message="Not detected / unreadable",
    )
