from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .visible import VisibleWatermarkConfig

PRESET_SCHEMA = 1
VALID_MODES = ("visible", "invisible", "hybrid")


@dataclass(frozen=True)
class InvisiblePresetConfig:
    enabled: bool = False
    owner_id: str = ""
    strength: str = "balanced"


@dataclass(frozen=True)
class CreatorPreset:
    schema: int = PRESET_SCHEMA
    mode: str = "visible"
    visible: VisibleWatermarkConfig = VisibleWatermarkConfig()
    invisible: InvisiblePresetConfig = InvisiblePresetConfig()

    def validated(self) -> "CreatorPreset":
        if int(self.schema) != PRESET_SCHEMA:
            raise ValueError(f"Preset schema {self.schema} tidak didukung.")
        if self.mode not in VALID_MODES:
            raise ValueError(f"Mode preset tidak dikenal: {self.mode}")
        self.visible.validated()
        if self.invisible.strength not in {"light", "balanced", "strong"}:
            raise ValueError("Strength invisible preset tidak valid.")
        return self


def preset_to_dict(preset: CreatorPreset) -> dict[str, Any]:
    preset.validated()
    return {
        "schema": PRESET_SCHEMA,
        "mode": preset.mode,
        "visible": asdict(preset.visible),
        "invisible": asdict(preset.invisible),
    }


def preset_from_dict(data: dict[str, Any]) -> CreatorPreset:
    if not isinstance(data, dict):
        raise ValueError("Preset harus berupa object JSON.")
    schema = int(data.get("schema", 1))
    if schema > PRESET_SCHEMA:
        raise ValueError(f"Preset schema {schema} lebih baru dari aplikasi ini.")
    visible_raw = data.get("visible") or {}
    invisible_raw = data.get("invisible") or {}
    visible_fields = VisibleWatermarkConfig.__dataclass_fields__
    invisible_fields = InvisiblePresetConfig.__dataclass_fields__
    visible = VisibleWatermarkConfig(**{
        key: value for key, value in visible_raw.items() if key in visible_fields
    })
    invisible = InvisiblePresetConfig(**{
        key: value for key, value in invisible_raw.items() if key in invisible_fields
    })
    preset = CreatorPreset(
        schema=PRESET_SCHEMA,
        mode=str(data.get("mode", "visible")),
        visible=visible,
        invisible=invisible,
    )
    return preset.validated()


def save_preset(preset: CreatorPreset, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(preset_to_dict(preset), indent=2, ensure_ascii=False) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, destination)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return destination


def load_preset(path: str | Path) -> CreatorPreset:
    with Path(path).open("r", encoding="utf-8") as handle:
        return preset_from_dict(json.load(handle))
