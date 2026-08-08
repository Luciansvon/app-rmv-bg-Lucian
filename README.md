<p align="center">
  <img src="review-temp/WhiteFlood_BG_Remover_App/logo.png" alt="WhiteFlood logo" width="180">
</p>

<h1 align="center">WhiteFlood BG Remover &amp; Upscaler</h1>

<p align="center">
  A local-first Windows desktop tool for furniture product photography and office catalogs.
</p>

<p align="center">
  <a href="https://github.com/Luciansvon/app-rmv-bg-Lucian/releases/tag/v2.5.0"><img src="https://img.shields.io/github/v/release/Luciansvon/app-rmv-bg-Lucian?label=latest%20release" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/platform-Windows-0078D4" alt="Windows">
  <img src="https://img.shields.io/badge/processing-local%20first-2E8B57" alt="Local-first processing">
</p>

WhiteFlood combines two independent image tools in one focused workflow: remove a background without changing the original pixel dimensions, or upscale a product photo to 2x, 4x, or 8x while preserving PNG transparency.

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

### Product workflow

- Before/After split-slider preview with cached display bitmaps for smoother dragging.
- Visible process phase and percentage for AI model downloads.
- Single-image and folder batch processing.
- Collision-safe batch filenames.
- DPI, ICC profile, and EXIF metadata are preserved when supported.
- RSS memory usage is visible in the app while processing.

## Download

For the easiest setup, download the Windows executable from the latest release:

**[Download WhiteFlood BG Remover v2.5.0](https://github.com/Luciansvon/app-rmv-bg-Lucian/releases/download/v2.5.0/WhiteFlood_BG_Remover.exe)**

The release asset is a one-file, windowed build. Python is not required for the release executable. On the first AI background-removal run, the selected model may need to be downloaded once; the progress is shown inside the app.

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

## Privacy and limitations

- Images stay on the local computer during processing.
- The first use of an AI background-removal mode may require an internet connection to download its model.
- Upscale 8x and large source images require more RAM, GPU resources, and disk space.
- The bundled release was built on Windows; GPU/Vulkan support can vary by computer.

## Documentation

- [`AGENTS.md`](AGENTS.md) — repository rules and safe-change boundaries.
- [`user.md`](user.md) — product requirements and constraints.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — active source architecture.
- [`docs/ERROR_SOLUTIONS.md`](docs/ERROR_SOLUTIONS.md) — evidence-based bug fixes.
- [`docs/WORKLOG.md`](docs/WORKLOG.md) — implementation and verification history.

## License

Project-specific licensing has not been declared yet. Review third-party notices before redistributing the application.

---

Built by Bima Chakti · © 2026 Bima Chakti
