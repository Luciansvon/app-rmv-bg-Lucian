from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import os

from PIL import Image, ImageColor, ImageDraw, ImageFont

ANCHORS = ("UL", "UC", "UR", "CL", "CC", "CR", "LL", "LC", "LR")
PATTERNS = ("single", "tile_horizontal", "tile_vertical", "full_tile", "diagonal_repeat")
WATERMARK_TYPES = ("text", "image")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _rgba_color(value: str | tuple[int, ...], opacity: int = 255) -> tuple[int, int, int, int]:
    if isinstance(value, str):
        parsed = ImageColor.getrgb(value)
    else:
        parsed = tuple(int(v) for v in value)
    if len(parsed) == 4:
        rgb = parsed[:3]
        base_alpha = parsed[3]
    else:
        rgb = parsed[:3]
        base_alpha = 255
    return (*rgb, round(base_alpha * (_clamp(opacity, 0, 255) / 255.0)))


def _default_font_path() -> Optional[str]:
    windir = os.environ.get("WINDIR")
    if windir:
        for name in ("segoeui.ttf", "arial.ttf", "calibri.ttf"):
            candidate = Path(windir) / "Fonts" / name
            if candidate.is_file():
                return str(candidate)
    return None


def _load_font(path: Optional[str], size: int):
    size = max(6, int(size))
    candidates = [path, _default_font_path(), "DejaVuSans.ttf"]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return ImageFont.truetype(candidate, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


@dataclass(frozen=True)
class VisibleWatermarkConfig:
    kind: str = "text"
    text: str = "WhiteFlood"
    font_path: Optional[str] = None
    font_size: int = 48
    color: str = "#FFFFFF"
    opacity: int = 60
    rotation: float = -30.0
    stroke_width: int = 0
    stroke_color: str = "#000000"
    shadow: bool = False
    shadow_offset: int = 3
    image_scale_percent: float = 18.0
    anchor: str = "CC"
    offset_x: int = 0
    offset_y: int = 0
    margin: int = 24
    pattern: str = "single"
    spacing_x: int = 80
    spacing_y: int = 80

    def validated(self) -> "VisibleWatermarkConfig":
        if self.kind not in WATERMARK_TYPES:
            raise ValueError(f"Jenis visible watermark tidak dikenal: {self.kind}")
        if self.anchor not in ANCHORS:
            raise ValueError(f"Anchor tidak dikenal: {self.anchor}")
        if self.pattern not in PATTERNS:
            raise ValueError(f"Pattern tidak dikenal: {self.pattern}")
        if not 0 <= int(self.opacity) <= 100:
            raise ValueError("Opacity harus 0..100.")
        if not 1 <= int(self.font_size) <= 1000:
            raise ValueError("Font size harus 1..1000.")
        if not 0.5 <= float(self.image_scale_percent) <= 300:
            raise ValueError("Scale logo harus 0.5..300 persen.")
        if int(self.margin) < 0 or int(self.spacing_x) < 0 or int(self.spacing_y) < 0:
            raise ValueError("Margin dan spacing tidak boleh negatif.")
        return self


def _text_stamp(config: VisibleWatermarkConfig) -> Image.Image:
    text = config.text or ""
    if not text:
        raise ValueError("Teks watermark kosong.")
    font = _load_font(config.font_path, config.font_size)
    stroke = max(0, int(config.stroke_width))
    shadow_pad = max(0, int(config.shadow_offset)) if config.shadow else 0
    probe = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    width = max(1, bbox[2] - bbox[0]) + stroke * 2 + shadow_pad + 6
    height = max(1, bbox[3] - bbox[1]) + stroke * 2 + shadow_pad + 6
    stamp = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(stamp)
    x = 3 + stroke - bbox[0]
    y = 3 + stroke - bbox[1]
    alpha = round(255 * (_clamp(config.opacity, 0, 100) / 100.0))
    if config.shadow:
        shadow_color = (0, 0, 0, round(alpha * 0.55))
        draw.text(
            (x + shadow_pad, y + shadow_pad), text, font=font,
            fill=shadow_color, stroke_width=stroke,
            stroke_fill=shadow_color,
        )
    draw.text(
        (x, y), text, font=font,
        fill=_rgba_color(config.color, alpha),
        stroke_width=stroke,
        stroke_fill=_rgba_color(config.stroke_color, alpha),
    )
    return stamp


def _image_stamp(config: VisibleWatermarkConfig, logo: Image.Image, source_size: tuple[int, int]) -> Image.Image:
    if logo is None:
        raise ValueError("Logo watermark belum dipilih.")
    mark = logo.convert("RGBA")
    target_w = max(1, round(source_size[0] * float(config.image_scale_percent) / 100.0))
    target_h = max(1, round(mark.height * (target_w / max(1, mark.width))))
    mark = mark.resize((target_w, target_h), Image.Resampling.LANCZOS)
    alpha_scale = _clamp(config.opacity, 0, 100) / 100.0
    alpha = mark.getchannel("A").point(lambda p: round(p * alpha_scale))
    mark.putalpha(alpha)
    return mark


def _rotate_stamp(stamp: Image.Image, degrees: float) -> Image.Image:
    degrees = float(degrees)
    if abs(degrees) < 1e-9:
        return stamp
    return stamp.rotate(degrees, expand=True, resample=Image.Resampling.BICUBIC)


def _anchor_xy(canvas: tuple[int, int], stamp: tuple[int, int], anchor: str, margin: int) -> tuple[int, int]:
    cw, ch = canvas
    sw, sh = stamp
    margin = max(0, int(margin))
    horizontal = anchor[1]
    vertical = anchor[0]
    if horizontal == "L":
        x = margin
    elif horizontal == "C":
        x = (cw - sw) // 2
    else:
        x = cw - sw - margin
    if vertical == "U":
        y = margin
    elif vertical == "C":
        y = (ch - sh) // 2
    else:
        y = ch - sh - margin
    return x, y


def _paste(layer: Image.Image, stamp: Image.Image, xy: tuple[int, int]) -> None:
    layer.alpha_composite(stamp, dest=(int(xy[0]), int(xy[1])))


def render_visible_layer(
    source_size: tuple[int, int],
    config: VisibleWatermarkConfig,
    logo: Optional[Image.Image] = None,
) -> Image.Image:
    config = config.validated()
    if source_size[0] <= 0 or source_size[1] <= 0:
        raise ValueError("Ukuran sumber tidak valid.")
    if config.kind == "text":
        stamp = _text_stamp(config)
    else:
        stamp = _image_stamp(config, logo, source_size)
    stamp = _rotate_stamp(stamp, config.rotation)

    layer = Image.new("RGBA", source_size, (0, 0, 0, 0))
    base_x, base_y = _anchor_xy(source_size, stamp.size, config.anchor, config.margin)
    base_x += int(config.offset_x)
    base_y += int(config.offset_y)
    sw, sh = stamp.size
    step_x = max(1, sw + int(config.spacing_x))
    step_y = max(1, sh + int(config.spacing_y))

    if config.pattern == "single":
        _paste(layer, stamp, (base_x, base_y))
        return layer

    if config.pattern == "tile_horizontal":
        y = base_y
        start = -sw
        for x in range(start, source_size[0] + sw, step_x):
            _paste(layer, stamp, (x + int(config.offset_x), y))
        return layer

    if config.pattern == "tile_vertical":
        x = base_x
        start = -sh
        for y in range(start, source_size[1] + sh, step_y):
            _paste(layer, stamp, (x, y + int(config.offset_y)))
        return layer

    row = 0
    for y in range(-sh, source_size[1] + sh, step_y):
        row_shift = step_x // 2 if config.pattern == "diagonal_repeat" and row % 2 else 0
        for x in range(-sw, source_size[0] + sw, step_x):
            _paste(layer, stamp, (x + row_shift + int(config.offset_x), y + int(config.offset_y)))
        row += 1
    return layer


def apply_visible_watermark(
    source: Image.Image,
    config: VisibleWatermarkConfig,
    logo: Optional[Image.Image] = None,
) -> Image.Image:
    has_alpha = source.mode in {"RGBA", "LA", "PA"} or (
        source.mode == "P" and "transparency" in source.info
    )
    base = source.convert("RGBA")
    layer = render_visible_layer(base.size, config, logo=logo)
    result = Image.alpha_composite(base, layer)
    if result.size != source.size:
        raise RuntimeError("Visible watermark mengubah dimensi sumber.")
    return result if has_alpha else result.convert("RGB")
