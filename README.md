<p align="center">
  <img src="review-temp/WhiteFlood_BG_Remover_App/logo.png" alt="WhiteFlood logo" width="180">
</p>

<h1 align="center">WhiteFlood — Local Image &amp; Video Toolkit</h1>

<p align="center">
  A local-first Windows desktop tool for furniture product photography and office catalogs.
</p>

<p align="center">
  <a href="https://github.com/Luciansvon/app-rmv-bg-Lucian/releases/tag/v2.6.3"><img src="https://img.shields.io/github/v/release/Luciansvon/app-rmv-bg-Lucian?label=latest%20release" alt="Latest release"></a>
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
- Live processing duration is shown as `Durasi HH:MM:SS` and remains visible in the completed result status.
- Processing speed profiles are available as `Lambat`, `Cepat`, and `Super Cepat`; the selected profile shows its resource/quality warning before processing.
- Before a missing AI model is downloaded, WhiteFlood asks for confirmation and shows percentage plus downloaded/total size inside the app.
- Single-image and folder batch processing.
- Batch remains available for Remove Background, Upscale, and Vectorize Image. Watermark batch/tracking is intentionally deferred.
- Collision-safe batch filenames.
- DPI, ICC profile, and EXIF metadata are preserved when supported.
- RSS memory usage is visible in the app while processing.

## Download

For the easiest setup, download the Windows executable from the latest release:

**[Download WhiteFlood v2.6.3](https://github.com/Luciansvon/app-rmv-bg-Lucian/releases/download/v2.6.3/WhiteFlood_BG_Remover.exe)**

The release asset is a one-file, windowed build. Python is not required for the release executable. On first use, missing AI models are confirmed and downloaded to the user model folder with progress shown inside the app. Vectorize uses the bundled VTracer package and does not download an AI model.

> Windows SmartScreen may show a warning because this executable is not code-signed yet.

## Spesifikasi device minimum

Angka di bawah adalah baseline praktis untuk release v2.6.3, bukan hasil benchmark lintas semua tipe komputer.

| Komponen | Minimum / catatan |
|---|---|
| OS | Windows 10 64-bit atau lebih baru. Release EXE dibuat untuk Windows x64. |
| CPU | CPU x64 modern. Remove Background, Vectorize, dan Remove Watermark memakai jalur CPU lokal. |
| RAM | 16 GB sebagai baseline untuk workflow AI. 32 GB lebih aman untuk gambar besar dan Upscale 8x. Benchmark minimum RAM lintas device belum tersedia. |
| GPU | Tidak wajib untuk Remove Background, Vectorize, dan Remove Watermark. Upscale membutuhkan GPU yang mendukung Vulkan dan driver grafik yang sesuai. |
| Ruang kosong | Minimal 5 GB untuk EXE + seluruh model yang diunduh. Sediakan 8 GB atau lebih jika sering memproses gambar besar, Upscale 8x, atau menyimpan banyak output. |

Kalau komputer tidak punya GPU Vulkan, tool lain tetap dapat dipakai, tetapi Upscale tidak dijamin berjalan.

## Penyimpanan model

Jika semua mode AI dipakai setidaknya sekali, file model yang perlu tersedia adalah:

| Fitur | Model | Ukuran |
|---|---|---:|
| Remove Background — Furniture Quality | BiRefNet-Massive | 972.67 MB (927.61 MiB) |
| Remove Background — Fast | BiRefNet-General | 972.67 MB (927.61 MiB) |
| Remove Background — Person | BiRefNet-Portrait | 972.67 MB (927.61 MiB) |
| Remove Background — High Detail | BiRefNet-HRSOD | 972.67 MB (927.61 MiB) |
| Remove Watermark | LaMa ONNX | 92.59 MB (88.30 MiB) |
| **Total model yang diunduh** | **4 BiRefNet + 1 LaMa** | **3,983.26 MB (3.71 GiB)** |

- Model `rembg` disimpan di `%USERPROFILE%\\.u2net`.
- Model LaMa disimpan di `%LOCALAPPDATA%\\WhiteFlood\\models`.
- Model Upscale tidak diunduh saat pertama kali dipakai. `realesrgan-x4plus` sudah dibundel di EXE; seluruh file model Real-ESRGAN yang ada di bundle berjumlah sekitar 46.27 MB (44.12 MiB).
- Ukuran EXE release v2.6.3 adalah 281.12 MiB (294,771,175 bytes). Kebutuhan dasar setelah semua model terunduh tetap sekitar **4.28 GB (3.99 GiB)**, belum termasuk file input, output, dan file sementara.

### Jika unduhan model tidak bergerak

- WhiteFlood memakai certificate store Windows dan otomatis mencoba BITS dengan proxy Windows/SystemDefault jika koneksi HTTPS Python gagal.
- Saat aplikasi masih menghubungkan server, progress bergerak tanpa angka persen palsu. Persentase dan ukuran baru tampil setelah server mulai mengirim data.
- Model Remove Background disimpan di `%USERPROFILE%\\.u2net`, bukan folder Downloads browser.
- WhiteFlood memaksa engine dan pemeriksa model memakai folder yang sama, sehingga environment variable kantor tidak mengarahkan `rembg` ke lokasi lain.
- Jika jalur HTTPS dan BITS sama-sama diblokir, pilih mode Remove Background lalu klik **Pasang Model dari File**. WhiteFlood memeriksa hash, menyalin, dan memberi nama file secara otomatis; model langsung siap dipakai tanpa restart.
- Jika kebijakan kantor memblokir GitHub untuk semua aplikasi, minta admin mengizinkan `github.com`, `release-assets.githubusercontent.com`, `raw.githubusercontent.com`, dan `media.githubusercontent.com`.

Untuk memantau ukuran file lewat terminal tanpa mengubah file, buka tab **Windows PowerShell** (prompt diawali `PS`), bukan Command Prompt/CMD, lalu jalankan:

```powershell
while ($true) {
    Clear-Host
    Get-ChildItem "$env:USERPROFILE\.u2net" -Force -ErrorAction SilentlyContinue |
        Select-Object Name, @{Name="UkuranMB"; Expression={[math]::Round($_.Length / 1MB, 1)}}, LastWriteTime
    Start-Sleep -Seconds 2
}
```

Tekan `Ctrl+C` untuk berhenti. Jika `UkuranMB` terus bertambah, unduhan masih berjalan. Jika tidak berubah lalu aplikasi menampilkan timeout, cek firewall/proxy kantor.

### Instal model secara offline untuk PC kantor strict

Kalau download GitHub dilarang oleh kebijakan kantor, jangan mematikan firewall. Download atau ambil model dari PC lain yang diizinkan, pindahkan memakai media yang disetujui admin kantor, lalu gunakan tombol **Pasang Model dari File** di aplikasi. Nama file sumber bebas; WhiteFlood akan memeriksa hash dan memasangnya ke nama/lokasi yang benar.

| Mode aplikasi | Nama file tujuan | MD5 rembg 2.0.78 |
|---|---|---|
| Furniture Quality | `birefnet-massive.onnx` | `33e726a2136a3d59eb0fdf613e31e3e9` |
| Fast | `birefnet-general.onnx` | `7a35a0141cbbc80de11d9c9a28f52697` |
| Person | `birefnet-portrait.onnx` | `c3a64a6abf20250d090cd055f12a3b67` |
| High Detail | `birefnet-hrsod.onnx` | `c017ade5de8a50ff0fd74d790d268dda` |

Contoh untuk model furnitur dari flashdisk `E:`:

```powershell
New-Item -ItemType Directory "$env:USERPROFILE\.u2net" -Force
Copy-Item "E:\birefnet-massive.onnx" "$env:USERPROFILE\.u2net\birefnet-massive.onnx"
Get-FileHash "$env:USERPROFILE\.u2net\birefnet-massive.onnx" -Algorithm MD5
```

Hasil MD5 harus persis `33e726a2136a3d59eb0fdf613e31e3e9`. Jika berbeda, jangan dipakai karena file salah atau rusak. WhiteFlood akan memakai file valid tersebut secara lokal tanpa download ulang.

Angka model Remove Background mengikuti model yang dipakai `rembg` 2.0.78. Dependency release dipin ke versi tersebut agar nama, ukuran, dan hash model tetap konsisten.

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

The build uses PyInstaller `--onefile --windowed` and writes the executable to `dist/WhiteFlood_BG_Remover.exe`. The build script cleans the local `build/` and generated `.spec` file before rebuilding; file lain yang sudah ada di `dist/` tetap dipertahankan.

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
- Downloaded Remove Background models are stored under `%USERPROFILE%\\.u2net`; downloaded LaMa is stored under `%LOCALAPPDATA%\\WhiteFlood\\models`. Image processing remains local after download.
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
