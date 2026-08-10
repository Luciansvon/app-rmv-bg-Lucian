"""Shared processing-speed profiles used by every heavy workflow."""

from dataclasses import dataclass
from types import MappingProxyType


PROCESSING_SLOW = "Lambat"
PROCESSING_BALANCED = "Cepat"
PROCESSING_SUPER_FAST = "Super Cepat"


@dataclass(frozen=True)
class ProcessingProfile:
    """Concrete resource/quality trade-offs for one processing run."""

    key: str
    label: str
    description: str
    warning: str
    requires_confirmation: bool
    onnx_threads: int
    upscale_tile: int
    upscale_jobs: str
    lama_context: int
    lama_overlap: int
    ffmpeg_threads: int
    vector_max_iterations: int | None
    vector_path_precision: int | None
    vector_speckle_delta: int


PROFILES = MappingProxyType({
    PROCESSING_SLOW: ProcessingProfile(
        key=PROCESSING_SLOW,
        label=PROCESSING_SLOW,
        description="Lebih hemat resource dan menjaga konteks detail, tetapi waktu proses paling lama.",
        warning="Peringatan: video atau gambar resolusi tinggi bisa memerlukan waktu jauh lebih lama.",
        requires_confirmation=True,
        onnx_threads=2,
        upscale_tile=128,
        upscale_jobs="1:2:2",
        lama_context=256,
        lama_overlap=64,
        ffmpeg_threads=1,
        vector_max_iterations=14,
        vector_path_precision=5,
        vector_speckle_delta=0,
    ),
    PROCESSING_BALANCED: ProcessingProfile(
        key=PROCESSING_BALANCED,
        label=PROCESSING_BALANCED,
        description="Rekomendasi harian: seimbang antara waktu, resource, dan kualitas hasil.",
        warning="Pilih Cepat untuk pemakaian normal dan cek preview sebelum menyimpan hasil.",
        requires_confirmation=False,
        onnx_threads=4,
        upscale_tile=0,
        upscale_jobs="1:4:4",
        lama_context=128,
        lama_overlap=32,
        ffmpeg_threads=2,
        vector_max_iterations=10,
        vector_path_precision=4,
        vector_speckle_delta=0,
    ),
    PROCESSING_SUPER_FAST: ProcessingProfile(
        key=PROCESSING_SUPER_FAST,
        label=PROCESSING_SUPER_FAST,
        description="Prioritas selesai cepat dengan penggunaan CPU/GPU dan RAM yang lebih tinggi.",
        warning="Peringatan: watermark kompleks bisa meninggalkan seam/halo; gunakan untuk draft dan periksa preview.",
        requires_confirmation=True,
        onnx_threads=6,
        upscale_tile=0,
        upscale_jobs="1:6:6",
        lama_context=64,
        lama_overlap=16,
        ffmpeg_threads=4,
        vector_max_iterations=8,
        vector_path_precision=3,
        vector_speckle_delta=1,
    ),
})


def processing_profile_names():
    return tuple(PROFILES.keys())


def get_processing_profile(name):
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"Mode processing tidak dikenal: {name}") from exc


def apply_vector_profile(config, profile):
    """Return VTracer config adjusted for the selected speed profile."""
    selected = get_processing_profile(profile) if isinstance(profile, str) else profile
    adjusted = dict(config)
    if selected.vector_max_iterations is not None:
        current_iterations = int(
            adjusted.get("max_iterations", selected.vector_max_iterations)
        )
        adjusted["max_iterations"] = (
            max(current_iterations, selected.vector_max_iterations)
            if selected.key == PROCESSING_SLOW
            else min(current_iterations, selected.vector_max_iterations)
        )
    if selected.vector_path_precision is not None:
        current_precision = int(
            adjusted.get("path_precision", selected.vector_path_precision)
        )
        adjusted["path_precision"] = (
            max(current_precision, selected.vector_path_precision)
            if selected.key == PROCESSING_SLOW
            else min(current_precision, selected.vector_path_precision)
        )
    if selected.vector_speckle_delta:
        adjusted["filter_speckle"] = max(
            0,
            int(adjusted.get("filter_speckle", 0)) + selected.vector_speckle_delta,
        )
    return adjusted
