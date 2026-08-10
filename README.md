<p align="center">
  <img src="review-temp/WhiteFlood_BG_Remover_App/logo.png" alt="WhiteFlood logo" width="180">
</p>

<h1 align="center">WhiteFlood — Local Image &amp; Video Toolkit</h1>

<p align="center">
  A local-first Windows desktop tool for furniture product photography and office catalogs.
</p>

<p align="center">
  <a href="https://github.com/Luciansvon/app-rmv-bg-Lucian/releases/tag/v2.5.0"><img src="https://img.shields.io/github/v/release/Luciansvon/app-rmv-bg-Lucian?label=latest%20release" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/platform-Windows-0078D4" alt="Windows">
  <img src="https://img.shields.io/badge/processing-local%20first-2E8B57" alt="Local-first processing">
</p>

WhiteFlood is a local-first desktop workbench for furniture/catalog media. It keeps the original two image tools and adds Vectorize Image plus static-mask watermark removal for images and videos.

## Features

### Remove Background

- AI modes for furniture, general images, people, high-detail objects, and plain white backgrounds.
- Local processing; product photos are not uploaded to an external API.
- Output dimensions stay exactly the same as the input.
- PNG output with an RGBA alpha channel.
- Edge refinement controls for soft edges, fine details, and alpha matting.

### Upscale

- 2x, 4x, and 8x output scales.
- Upscayl NCNN / Real-ESRGAN backend for the AI upscale pass.
- PNG/RGBA input stays in the PNG pipeline, including transparency.
- 8x uses a 4x AI pass followed by a Lanczos 2x resize.
- Exact output dimensions are checked before saving.

### Vectorize Image

- VTracer `0.6.15` converts PNG, JPG/JPEG, WebP, or BMP into validated SVG.
- Presets: Logo, Illustration, Line Art, and Detailed.
- SVG preview is status/output information; there is no native node editor.

### Remove Watermark

- Image and static-video modes use a source-pixel mask with brush, rectangle, eraser, zoom, clear, undo, and redo.
- LaMa ONNX processes only the masked ROI/tile area and preserves image alpha/dimensions.
- Video processing streams one frame at a time through bundled FFmpeg; audio copy, cancellation, VFR warning, and output validation are included in the MVP.

### Product workflow

- Before/After split-slider preview with cached display bitmaps for smoother dragging.
- Circular percentage progress is shown while Remove Background, Upscale, Vectorize, and Watermark workflows run.
- Before a missing AI model is downloaded, WhiteFlood asks for confirmation and shows percentage plus downloaded/total size inside the app.
- Single-image and folder batch processing.
- Batch remains available for Remove Background, Upscale, and Vectorize Image. Watermark batch/tracking is intentionally deferred.
- Collision-safe batch filenames.
- DPI, ICC profile, and EXIF metadata are preserved when supported.
- RSS memory usage is visible in the app while processing.

## Download

For the easiest setup, download the Windows executable from the latest release:

**[Download WhiteFlood v2.5.0](https://github.com/Luciansvon/app-rmv-bg-Lucian/releases/download/v2.5.0/WhiteFlood_BG_Remover.exe)**

The release asset is a one-file, windowed build. Python is not required for the release executable. On first use, missing AI models are confirmed and downloaded to the user model folder with progress shown inside the app. Vectorize uses the bundled VTracer package and does not download an AI model.

> Windows SmartScreen may show a warning because this executable is not code-signed yet.

## Run from source

1. Install Python 3.11 or newer.
2. Install the runtime dependencies once:

   ```powershell
   python -m pip install -r review-temp/WhiteFlood_BG_Remover_App/requirements.txt
   ```

3. Double-click [`RUN_APP.vbs`](review-temp/WhiteFlood_BG_Remover_App/RUN_APP.vbs) to launch without a visible terminal.

`RUN_APP.bat` is a short entry point that forwards to the hidden launcher. If a built executable exists in `dist`, the launcher uses it first.

## Build the Windows executable

From `review-temp/WhiteFlood_BG_Remover_App`:

```powershell
.\BUILD_EXE.bat
```

The build uses PyInstaller `--onefile --windowed` and writes the executable to `dist/WhiteFlood_BG_Remover.exe`. The build script cleans the local `build/`, `dist/`, and generated `.spec` file before rebuilding.

## Output contract

| Tool | Input | Output |
|---|---:|---:|
| Remove Background | 2048 x 2048 | 2048 x 2048 |
| Upscale 2x | 2048 x 2048 | 4096 x 4096 |
| Upscale 4x | 2048 x 2048 | 8192 x 8192 |
| Upscale 8x | 2048 x 2048 | 16384 x 16384 |
| Remove Watermark Image | 2048 x 2048 | 2048 x 2048 PNG |
| Remove Watermark Video | visual input size | same visual size MP4 |

## Privacy and limitations

- Images stay on the local computer during processing.
- The first use of an AI background-removal or watermark mode may require an internet connection to download its model after user confirmation.
- Downloaded LaMa is stored under `%LOCALAPPDATA%\\WhiteFlood\\models`; image processing remains local after download.
- Watermark video release packaging includes pinned Windows x64 LGPL FFmpeg binaries under `ffmpeg/` (BtbN `autobuild-2026-08-09-13-03`, FFmpeg 8.1.2).
- Upscale 8x and large source images require more RAM, GPU resources, and disk space.
- The bundled release was built on Windows; GPU/Vulkan support can vary by computer.

## Documentation

- [`AGENTS.md`](AGENTS.md) — repository rules and safe-change boundaries.
- [`user.md`](user.md) — product requirements and constraints.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — active source architecture.
- [`docs/ERROR_SOLUTIONS.md`](docs/ERROR_SOLUTIONS.md) — evidence-based bug fixes.
- [`docs/WORKLOG.md`](docs/WORKLOG.md) — implementation and verification history.

- [`docs/WHITEFLOOD_UI_REDESIGN.md`](docs/WHITEFLOOD_UI_REDESIGN.md) - visual baseline and page contracts.

## License

Project-specific licensing has not been declared yet. Review third-party notices before redistributing the application.

---

Built by Bima Chakti · © 2026 Bima Chakti
