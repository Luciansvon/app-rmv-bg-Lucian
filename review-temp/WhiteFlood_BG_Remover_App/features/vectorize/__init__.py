"""Raster-to-SVG vectorization services."""

from .presets import PRESETS, get_preset, preset_names
from .service import VectorizeError, VectorizeResult, VectorizeService

__all__ = [
    "PRESETS",
    "VectorizeError",
    "VectorizeResult",
    "VectorizeService",
    "get_preset",
    "preset_names",
]
