<p align="center">
  <img src="logo.png" alt="WhiteFlood logo" width="160">
</p>

<h1 align="center">WhiteFlood — Local Image &amp; Video Toolkit</h1>

<p align="center">Windows desktop processing tools for furniture product photos and catalogs.</p>

<p align="center"><strong>Version 2.6.3</strong> · Built by Bima Chakti</p>

## What it does

WhiteFlood provides five independent workbench pages:

- **Remove Background** — local AI or white-background flood removal, with exact input dimensions and RGBA PNG output.
- **Upscale** — 2x, 4x, or 8x enlargement through the bundled Upscayl NCNN / Real-ESRGAN backend.
- **Vectorize Image** - VTracer `0.6.15` raster-to-SVG conversion with four presets.
- **Remove Watermark Image** - static source-pixel mask and LaMa ONNX inpainting.
- **Remove Watermark Video** - one static mask applied frame-by-frame through FFmpeg.

## Main features

- Cached Before/After split-slider preview for smoother dragging.
- Circular percentage progress is shown for all processing workflows.
- Live processing duration is shown as `Durasi HH:MM:SS` while a workflow runs and after it completes.
- Processing speed profiles are available as `Lambat`, `Cepat`, and `Super Cepat`, with an in-app description and warning before non-default profiles run.
- Missing AI models ask for confirmation and show downloaded/total size plus percentage inside the app.
- Single-image and folder batch processing.
- Batch is available for Remove Background, Upscale, and Vectorize Image. Watermark batch/tracking is deferred.
- Collision-safe output names.
- PNG transparency and supported metadata preserved.
- Memory usage shown as process RSS while the app is working.
- Hidden launcher path so users do not see a terminal window.

## Dimension contract

| Tool | Input | Output |
|---|---:|---:|
| Remove Background | 2048 x 2048 | 2048 x 2048 |
| Upscale 2x | 2048 x 2048 | 4096 x 4096 |
| Upscale 4x | 2048 x 2048 | 8192 x 8192 |
| Upscale 8x | 2048 x 2048 | 16384 x 16384 |

No unintended crop or resize is allowed.

## Download the release

Download the standalone Windows executable from the [WhiteFlood v2.6.3 release](https://github.com/Luciansvon/app-rmv-bg-Lucian/releases/tag/v2.6.3). The release executable does not require Python. AI background-removal models may be downloaded once on first use, with progress displayed in the app. On strict office networks, WhiteFlood uses the Windows certificate store and automatically falls back to Windows BITS/system proxy. A verified model file can also be installed from the Remove Background sidebar without using a terminal.

## Run from source

1. Install Python 3.11 or newer.
2. From this folder, install dependencies once:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Double-click `RUN_APP.vbs` to launch without a visible console.

`RUN_APP.bat` forwards to `RUN_APP.vbs`. When `dist/WhiteFlood_BG_Remover.exe` exists, the launcher uses that executable first.

## Build

Double-click `BUILD_EXE.bat`. The script creates a PyInstaller `--onefile --windowed` executable at:

```text
dist/WhiteFlood_BG_Remover.exe
```

The build script cleans the local `build/` and generated `.spec` file before rebuilding. Other files already stored in `dist/` are preserved.

## Supported input files

PNG, JPG, JPEG, WEBP, and BMP.

The first AI background-removal or watermark run may need an internet connection to download a model after confirmation. Downloaded LaMa is stored under `%LOCALAPPDATA%\\WhiteFlood\\models`; image processing remains local. Vectorize uses VTracer and does not download an AI model.

Watermark video release packaging includes pinned Windows x64 LGPL FFmpeg binaries under `ffmpeg/` (BtbN `autobuild-2026-08-09-13-03`, FFmpeg 8.1.2). If LaMa is not bundled, the app downloads the OpenCV Zoo model after user confirmation.

---

© 2026 Bima Chakti
