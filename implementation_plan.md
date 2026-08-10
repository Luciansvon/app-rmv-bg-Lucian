# Implementation Plan - WhiteFlood UI, Preview, dan Distribusi

Status: Disetujui; implementasi source selesai, runtime verification gate pending
Tanggal: 2026-08-08

## Temuan yang sudah dicek

- Source aktif: `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`.
- Worktree sudah memiliki perubahan sebelum pekerjaan ini. Perubahan itu harus dipertahankan.
- `SplitSliderPreview._update_slider_from_mouse()` memanggil `redraw()` pada setiap event drag.
- `redraw()` saat ini mengulang resize `Image.LANCZOS`, pembuatan checkerboard, crop, komposit, dan pembuatan `ImageTk.PhotoImage`.
- Upscale memakai `subprocess.Popen()` dan sudah memiliki `CREATE_NO_WINDOW`; jalur launcher `RUN_APP.bat` masih menjalankan `pip install` setiap kali dan membuka console.
- Download model Remove Background memakai `rembg` 2.0.78 melalui `pooch.retrieve(..., progressbar=True)`. Progress saat ini hanya ditampilkan sebagai status teks dan angka progress dummy.
- `BUILD_EXE.bat`/`build_exe.py` sudah memakai mode PyInstaller `--windowed`, tetapi belum menghilangkan masalah console pada jalur run dari source.

## Scope yang akan dikerjakan

### 1. Redesign UI desktop

- Pertahankan dua alat terpisah, preview utama besar, dark theme, split-slider, dan kredit UI.
- Susun ulang sidebar agar hierarchy-nya jelas: brand/status, pilihan alat, pengaturan alat aktif, aksi gambar utama, lalu batch sebagai bagian sekunder.
- Kurangi teks yang terpotong dan kontrol yang terlihat aktif padahal belum bisa dipakai.
- Buat empty state, loaded state, processing state, success state, dan error state lebih terbaca.
- Hilangkan ketergantungan emoji/glyph yang berisiko tampil sebagai karakter rusak di komputer kantor.
- Tidak menambah dependency UI baru dan tidak mengubah pipeline gambar hanya demi tampilan.

### 2. Perbaikan lag split-slider

- Cache hasil resize preview dan checkerboard berdasarkan ukuran canvas.
- Saat drag, gunakan bitmap display yang sudah disiapkan; jangan resize gambar sumber berulang kali.
- Throttle redraw drag ke satu update terjadwal agar event mouse tidak menumpuk di main thread.
- Tetap lakukan redraw penuh saat gambar atau ukuran canvas berubah.
- Pertahankan rasio gambar, label asli/hasil, batas posisi slider, dan referensi `PhotoImage` agar tidak hilang.

### 3. Progress download model yang nyata

- Tambahkan adapter progress untuk downloader `pooch` yang mengirim persentase byte ke UI.
- Nonaktifkan progress bar terminal bawaan untuk jalur aplikasi dan tampilkan fase download + persentase di UI.
- Bedakan teks progress download model dari progress proses gambar/upscale.
- Terapkan callback yang dit-throttle agar update progress tidak membanjiri event loop Tkinter.
- Pakai callback yang sama pada single image dan batch jika model belum tersedia.
- Jangan mengunduh model saat implementasi atau verifikasi; hanya ubah jalur callback.

### 4. Launcher tanpa console yang mencurigakan

- Hentikan instalasi dependency otomatis setiap kali `RUN_APP.bat` dijalankan.
- Tambahkan jalur launch windowless untuk source menggunakan `pythonw`/launcher tersembunyi.
- Pertahankan `CREATE_NO_WINDOW` untuk subprocess Upscayl.
- Jelaskan di README cara pakai source dan cara membagikan EXE windowed.
- Tidak menghapus artefak `build/`, `dist/`, model, backup, atau hasil test.

## File yang mungkin berubah

- `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`
- `review-temp/WhiteFlood_BG_Remover_App/RUN_APP.bat`
- `review-temp/WhiteFlood_BG_Remover_App/RUN_APP.vbs` (baru, jika launcher source windowless diperlukan)
- `README.md`
- `review-temp/WhiteFlood_BG_Remover_App/README.md`
- `docs/ARCHITECTURE.md`
- `docs/ERROR_SOLUTIONS.md`
- `docs/WORKLOG.md`

`BUILD_EXE.bat`, binary engine, model, backup, dan artefak build tidak akan dihapus atau dibersihkan.

## Verifikasi yang akan dijalankan setelah implementasi

- `git diff` dan `git diff --check` untuk memastikan scope.
- Pemeriksaan syntax source aktif dengan `python -m py_compile ...` sesuai aturan repo.
- Static smoke test untuk kontrak ukuran output 2x/4x/8x, alpha, progress adapter, dan launcher tanpa mengunduh model atau menjalankan GUI.
- Pemeriksaan bahwa `CREATE_NO_WINDOW` tetap ada dan dependency tidak lagi di-install setiap launch.
- GUI dan download model nyata tidak dijalankan. Setelah persetujuan Bima, `BUILD_EXE.bat` dijalankan dan menghasilkan EXE windowed baru; install dependency yang dilaporkan script seluruhnya sudah tersedia.
- Dokumentasi hanya akan mencatat bukti yang benar-benar dijalankan.

## Risiko dan batas

- Tanpa GUI smoke test, kelancaran slider dan fidelity visual belum boleh disebut terverifikasi penuh.
- Tanpa download model nyata, angka progress hanya bisa diuji melalui fake downloader/static smoke test; koneksi GitHub dan ukuran file aktual belum dinilai.
- EXE baru sudah terbentuk, tetapi kesiapan distribusi binary belum boleh disebut terverifikasi penuh sebelum smoke test menjalankan EXE.

## 2026-08-10 - UI redesign gate sebelum fitur baru

Status: Arah visual dibuat; coding UI dan engine fitur baru menunggu tahap implementasi berikutnya.

### Keputusan desain

- UI dirombak sebagai enam halaman/workspace: Workspace, Hapus Background,
  Upscale, Vectorize Image, Remove Watermark Image, dan Remove Watermark Video.
- Batch folder tetap dipertahankan untuk Hapus Background, Upscale, dan
  Vectorize Image. Batch watermark ditunda agar mask manual tidak salah
  diterapkan ke file lain.
- CustomTkinter/Tkinter, dark theme, preview besar, status bar, dan pemisahan
  tool tetap dipertahankan.
- Arah visual: dark utility workbench dengan satu aksen rose, inspector
  kontekstual, dan state kosong/proses/berhasil/error yang eksplisit.
- Board visual dibuat sebagai referensi komposisi. Board bukan bukti runtime dan
  tidak menggantikan screenshot dari aplikasi.

### Handoff

- `docs/WHITEFLOOD_UI_REDESIGN.md` berisi audit, token, page contract, state
  matrix, dan acceptance gate untuk konversi ke CustomTkinter.
- Visual board generator disimpan di luar repository pada folder generated
  image Codex dan tidak dijadikan source asset aplikasi.

### Bukti yang sudah dijalankan

- Skill design-intelligence, design-taste-frontend, dan artifact-template-system-design dibaca sesuai instruksi.
- Reference System Design DOCX diaudit read-only; section/style audit berhasil.
- Render reference DOCX tidak berjalan karena executable LibreOffice/soffice tidak ditemukan pada environment ini.

### Batas tahap ini

- Tidak ada source code aplikasi yang diubah pada tahap desain ini.
- GUI source, smoke test, model download, instalasi dependency, dan build EXE
  belum dijalankan.

## 2026-08-10 - Implementasi feature services berdasarkan source resmi

Status: Source implementation selesai; unit/static gate lulus; runtime gate menunggu persetujuan untuk dependency/model/binary/GUI.

### Yang diimplementasikan

- `features/vectorize/`: preset dan adapter VTracer `0.6.15`, capability/version guard, temporary SVG, XML validation, dan atomic save.
- `features/watermark/mask_canvas.py`: source-pixel mask, letterbox mapping, brush, rectangle, eraser, zoom, clear, undo/redo, dan overlay.
- `features/watermark/inpaint.py`: lifecycle session LaMa ONNX, ROI context, tile 512px overlap, alpha-safe composition, dan validasi dimensi.
- `features/watermark/media.py`: bundled resource lookup, ffprobe metadata, visual rotation normalization, VFR flag, dan collision safety.
- `features/watermark/video.py`: streaming raw BGR frame, static mask, cancellation, audio-copy fallback, VFR warning, MP4 partial output, ffprobe validation, dan cleanup.
- `whiteflood_app.py`: enam page visual baseline, state/callback, non-auto-process setelah memilih file, serta batch tetap untuk tiga image tools ringan.
- `tests/test_features.py`: 8 unittest tanpa dependency baru.

### Catatan source audit

- VTracer diikuti dari README binding pada tag `0.6.15`, bukan API rewrite `1.0.0-alpha`.
- LaMa diikuti dari `opencv_zoo/models/inpainting_lama/lama.py` untuk BGR blob, mask binary, input name, dan output shape.
- FFmpeg memakai input pipe/map, autorotate default untuk frame visual, serta explicit MP4 output.

### Gate yang sudah lulus

- Unit test: 8/8 lulus.
- AST parse source aktif, feature package, dan test lulus.
- Import smoke source app dengan Python system lulus.

### Gate yang masih pending

- VTracer conversion runtime dengan fixture image.
- Tambah model LaMa dan inferensi image nyata.
- Tambah pinned FFmpeg/FFprobe LGPL + checksum/notice.
- GUI smoke test dan screenshot dibanding visual board.
- Build PyInstaller: selesai 2026-08-10; detail dicatat di `docs/WORKLOG.md`.
- Resource-path, console, dan runtime smoke test EXE.

## 2026-08-10 - Model confirmation, circular progress, dan logo icon

Status: Source implementation dan build EXE selesai; GUI runtime gate pending.

### Perubahan

- Model LaMa dicari dari bundle/source lalu folder writable `%LOCALAPPDATA%\\WhiteFlood\\models`.
- Missing model memunculkan dialog konfirmasi; download memakai worker, file `.part`, atomic replace, cancellation, dan progress `% + byte terunduh/total` di UI.
- Remove Background mempertahankan prompt rembg dan adapter progress byte; Upscale, Vectorize, Remove Watermark Image/Video, serta batch memakai circular progress overlay.
- Watermark Image melaporkan progress berdasarkan tile LaMa; video tetap berdasarkan frame; Vectorize memakai progress tahap karena VTracer tidak memberi persentase kontinu.
- MaskCanvas mengirim callback setelah mask berubah agar tombol Process langsung aktif.
- Logo title bar dan header sidebar di-crop berdasarkan alpha bounding box saat runtime agar mark tidak terlihat mengecil.

### Gate aktual

- `python -m py_compile ...` lulus.
- `python -m unittest discover -s tests -v` lulus dengan 10 test.
- `BUILD_EXE.bat` lulus dalam sekitar 3 menit 31 detik; EXE baru tersedia di `review-temp/WhiteFlood_BG_Remover_App/dist/WhiteFlood_BG_Remover.exe`.

### Gate pending

- Download model nyata, GUI confirmation/progress, click Process Watermark, dan screenshot smoke test.
- Runtime EXE, FFmpeg video pipeline, serta visual icon pada Windows.

## 2026-08-10 - Timestamp durasi semua workflow

Status: Source implementation, unit test, dan build EXE selesai; GUI runtime gate pending.

### Perubahan

- Menambahkan timer terpusat berbasis `time.perf_counter()` dan callback `after()` Tkinter.
- Menampilkan `Durasi HH:MM:SS` secara live di status bar.
- Menyimpan durasi final untuk Remove Background, Upscale, Vectorize, Remove Watermark Image/Video, dan batch pada status hasil/error/cancel.

### Gate aktual

- Syntax check lulus.
- Unit test lulus dengan 12 test.
- `BUILD_EXE.bat` lulus dalam sekitar 6 menit 27 detik; EXE baru tersedia di `review-temp/WhiteFlood_BG_Remover_App/dist/WhiteFlood_BG_Remover.exe`.

### Gate pending

- GUI smoke test visual.

## 2026-08-10 - Processing speed modes

Status: source implementation, unit test, dan build EXE selesai; GUI runtime gate pending.

### Keputusan desain

- Selector `Lambat`, `Cepat`, dan `Super Cepat` tampil hanya saat alat yang aktif memiliki parameter speed yang nyata.
- Default `Cepat` menjaga perilaku seimbang dan tidak memunculkan modal tambahan.
- `Lambat` memprioritaskan penggunaan resource yang lebih rendah serta konteks inpaint lebih aman.
- `Super Cepat` memprioritaskan waktu dengan thread/resource lebih tinggi; UI menampilkan peringatan sebelum proses dan menjelaskan trade-off kualitas/hasil.
- Dimensi output, alpha, format, audio policy, dan file input tetap tidak berubah.

### Implementasi

- Profil speed dipusatkan agar single image dan batch memakai konfigurasi yang sama.
- Profil diteruskan ke ONNX Remove Background, Real-ESRGAN, VTracer, LaMa tile/context, dan thread encoder FFmpeg.
- Tambahkan unit test untuk nama profil, konfigurasi valid, dan guard output.

### Gate pending

- GUI smoke test untuk selector, warning, dan tiga workflow utama.

### Bukti build

- `BUILD_EXE.bat` lulus dalam sekitar 5 menit 56 detik.
- EXE: `review-temp/WhiteFlood_BG_Remover_App/dist/WhiteFlood_BG_Remover.exe`, 295.693.085 bytes, dibuat 2026-08-10 11:48:36.
- SHA-256: `BBB932670E8AB633DDC18E8D872233D93D407674E02100479FF5C98E802EFF77`.
