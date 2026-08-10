"""Small, stable VTracer preset definitions used by the WhiteFlood UI."""

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class VectorPreset:
    key: str
    label: str
    description: str
    config: MappingProxyType


def _preset(key, label, description, **config):
    return VectorPreset(
        key=key,
        label=label,
        description=description,
        config=MappingProxyType(dict(config)),
    )


PRESETS = MappingProxyType({
    "Logo": _preset(
        "Logo",
        "Logo",
        "Warna bersih untuk logo dengan bentuk bertumpuk.",
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=4,
        color_precision=6,
        layer_difference=16,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=3,
    ),
    "Illustration": _preset(
        "Illustration",
        "Illustration",
        "Menjaga detail warna untuk ilustrasi produk.",
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=2,
        color_precision=7,
        layer_difference=12,
        corner_threshold=60,
        length_threshold=3.5,
        max_iterations=12,
        splice_threshold=45,
        path_precision=3,
    ),
    "Line Art": _preset(
        "Line Art",
        "Line Art",
        "Mode biner untuk gambar garis hitam putih.",
        colormode="binary",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=1,
        color_precision=6,
        layer_difference=16,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=3,
    ),
    "Detailed": _preset(
        "Detailed",
        "Detailed",
        "Detail path lebih tinggi untuk gambar kompleks.",
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=1,
        color_precision=8,
        layer_difference=8,
        corner_threshold=60,
        length_threshold=3.5,
        max_iterations=14,
        splice_threshold=45,
        path_precision=5,
    ),
})


def preset_names():
    return tuple(PRESETS.keys())


def get_preset(name):
    try:
        return PRESETS[name]
    except KeyError as exc:
        raise ValueError(f"Preset vector tidak dikenal: {name}") from exc
