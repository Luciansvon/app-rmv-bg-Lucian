# Worklog WhiteFlood BG Remover & Upscaler

## Tujuan

File ini mencatat pekerjaan yang benar-benar dilakukan, keputusan yang disetujui, bukti verifikasi, dan pekerjaan yang masih terbuka.

Worklog bukan pengganti:

- `AGENTS.md` untuk aturan kerja;
- `docs/ARCHITECTURE.md` untuk arsitektur;
- `docs/ERROR_SOLUTIONS.md` untuk bug dan root cause;
- `user.md` untuk aturan produk dan keputusan Bima.

## Aturan pencatatan

- Tambahkan catatan secara kronologis.
- Jangan menghapus catatan lama hanya karena rencana berubah.
- Bedakan status `Selesai`, `Disetujui`, `Direncanakan`, `Ditunda`, dan `Belum diverifikasi`.
- Jangan mencatat rencana sebagai fitur yang sudah tersedia.
- Cantumkan file yang dibuat atau diubah.
- Cantumkan test, build, smoke test, atau pemeriksaan aktual yang dilakukan.
- Jika tidak ada kode yang berubah, tulis jelas bahwa test kode dan build tidak dijalankan.
- Perubahan arsitektur harus disinkronkan dengan `docs/ARCHITECTURE.md`.
- Bugfix harus mempunyai entri di `docs/ERROR_SOLUTIONS.md`.

---

## 2026-08-10 - WhiteFlood UI baseline dan feature services

Status: implementasi source dan static/unit gate selesai; build EXE sudah selesai, sedangkan GUI, model, binary FFmpeg, dan runtime EXE belum diverifikasi.

### Hasil

- UI source aktif mengikuti visual board enam page: Workspace, Hapus Background, Upscale, Vectorize Image, Remove Watermark Image, dan Remove Watermark Video.
- Batch tetap tersedia untuk tiga alat image yang ringan: Hapus Background, Upscale, dan Vectorize Image. Batch tidak ditampilkan untuk watermark.
- Menambahkan adapter VTracer `0.6.15`, preset, temporary SVG, validasi XML, atomic save, dan collision safety.
- Menambahkan MaskCanvas source-pixel, ROI/tile LaMa ONNX, ffprobe metadata, streaming raw-frame FFmpeg, cancellation, audio-copy fallback, VFR warning, output validation, dan temporary cleanup.
- Menambahkan unittest kontrak tanpa dependency test baru.
- Menyelaraskan implementasi dengan source resmi VTracer tag 0.6.15, OpenCV Zoo `lama.py`, dan dokumentasi FFmpeg.

### Bukti verifikasi aktual

- `python -m unittest discover -s tests -v` — 8 test lulus.
- AST parse semua source feature, source app, dan test lulus.
- Import smoke test `whiteflood_app` dengan environment Python system berhasil.

### Belum diverifikasi

- VTracer wheel 0.6.15 sudah terpasang untuk proses build; conversion runtime belum dijalankan.
- Model `inpainting_lama_2025jan.onnx` belum diunduh dan inferensi nyata belum dijalankan.
- Binary FFmpeg LGPL belum dibundel dan pipeline video nyata belum dijalankan.
- GUI/screenshot, smoke test manual, runtime PyInstaller EXE, console suppression, dan output nyata belum diverifikasi.

### File utama

- `implementation_plan.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/WHITEFLOOD_UI_REDESIGN.md`
- `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`
- `review-temp/WhiteFlood_BG_Remover_App/features/`
- `tests/test_features.py`

---

## 2026-08-10 - Prompt model, circular progress, watermark button, dan logo

Status: source patch dan build EXE selesai; GUI runtime masih pending.

### Hasil

- Model LaMa sekarang dicari dari bundle/source lalu `%LOCALAPPDATA%\\WhiteFlood\\models`.
- Jika model AI belum tersedia, app meminta konfirmasi sebelum download.
- Download LaMa memakai worker, file `.part`, atomic replace, cancellation, dan progress `% + ukuran terunduh/total` di UI.
- Progress rembg mempertahankan jalur pooch tetapi ukuran byte sekarang tampil di UI.
- Circular progress persen dipakai untuk Remove Background, Upscale, Vectorize, Remove Watermark Image/Video, dan batch.
- Watermark Image melaporkan progress berdasarkan tile; Vectorize memakai progress tahap karena tidak memiliki progress kontinu.
- Mask callback memperbaiki tombol `Process Image` yang tetap disabled setelah brush/rectangle.
- Logo title bar dan header sidebar memakai crop alpha bounding box saat runtime.

### Bukti verifikasi aktual

- `python -m py_compile ...` untuk source yang terdampak lulus.
- `python -m unittest discover -s tests -v` lulus: 10 test.
- `git diff --check` lulus; warning yang muncul hanya normalisasi LF/CRLF Git.
- Build `BUILD_EXE.bat` lulus dalam sekitar 3 menit 31 detik.
- EXE: `dist/WhiteFlood_BG_Remover.exe`, 201.375.415 bytes, dibuat 2026-08-10 10:12:51.
- SHA-256: `1E761624C5E6076ACDD5A3D10A305E2C575CCAB1470B91302E5D1CD4F1E91E5A`.

### Belum diverifikasi

- Dialog konfirmasi dan download model internet nyata.
- GUI click Process Watermark, circular progress visual, logo Windows, serta smoke test Remove Background/Upscale/Vectorize/Watermark.
- FFmpeg bundle dan model LaMa masih belum tersedia di repository; LaMa akan diunduh ke folder user saat disetujui.

### File utama

- `review-temp/WhiteFlood_BG_Remover_App/features/model_download.py`
- `review-temp/WhiteFlood_BG_Remover_App/features/watermark/inpaint.py`
- `review-temp/WhiteFlood_BG_Remover_App/features/watermark/mask_canvas.py`
- `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`
- `tests/test_features.py`

---

## 2026-08-10 - Build executable setelah implementasi fitur

Status: build PyInstaller selesai; runtime EXE dan smoke test resource belum diverifikasi.

### Bukti verifikasi aktual

- Command: `cmd.exe /c "BUILD_EXE.bat < NUL"` dari `review-temp/WhiteFlood_BG_Remover_App`.
- PyInstaller mencatat `Build complete!` dan proses selesai tanpa error.
- Output: `review-temp/WhiteFlood_BG_Remover_App/dist/WhiteFlood_BG_Remover.exe`.
- Ukuran: 201,367,265 bytes (192.04 MB).
- Dibuat: 2026-08-10 09:28:30.
- SHA-256: `8EC9D22A6A638C23D971B6F1CEFB2137FC2C9D5F867D41D1455CBD92E71401F4`.
- Versi yang terdeteksi saat build: VTracer 0.6.15, ONNX Runtime 1.28.0, PyInstaller 6.21.0.
- Warning log PyInstaller berisi 723 baris; salah satu warning yang perlu dicek saat runtime adalah `tbb12.dll` dari optional dependency numba.

### Belum diverifikasi

- Menjalankan EXE, GUI windowed/no-console, resource path `_MEIPASS`, model LaMa, conversion VTracer, dan pipeline FFmpeg.
- Binary FFmpeg dan model LaMa belum ditempatkan ke bundle; folder `ffmpeg/` dan `assets/models/` baru berisi README/notice.

---

## 2026-08-08 - Menambahkan aturan repo dan dokumentasi baseline

Status: Selesai untuk dokumentasi; tidak ada perubahan kode aplikasi.

### Hasil

- Menambahkan `AGENTS.md` sebagai aturan kerja repo.
- Menambahkan `docs/ARCHITECTURE.md` berdasarkan source WhiteFlood yang sedang aktif.
- Menambahkan `docs/ERROR_SOLUTIONS.md` sebagai register error berbasis bukti.
- Menambahkan `docs/WORKLOG.md` sebagai catatan perubahan dan verifikasi.
- Menyinkronkan README dengan tautan ke dokumentasi baru.
- Perubahan lokal lain yang sudah ada di working tree tidak disentuh.

### Bukti verifikasi aktual

- `git diff --check` dijalankan untuk perubahan tracked dan tidak menemukan whitespace error.
- Pemeriksaan sintaks Python tidak dijalankan karena perubahan ini hanya dokumentasi.
- Aplikasi GUI, model AI, test gambar, dan build EXE tidak dijalankan.

### Batasan

- Arsitektur pada dokumen ini adalah audit source, bukan bukti runtime.
- Belum ada regression test otomatis khusus dimensi, alpha, collision safety, atau RAM.
- Belum ada entri error terverifikasi karena tidak ada bugfix yang dikerjakan pada perubahan ini.

### File

- `AGENTS.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/ERROR_SOLUTIONS.md`
- `docs/WORKLOG.md`

---

## 2026-08-08 - Redesign UI, slider cache, dan launcher windowless

Status: Selesai untuk patch source dan dokumentasi; verifikasi GUI, download nyata, dan build EXE belum dilakukan.

### Hasil

- Menata ulang UI menjadi sidebar alat aktif, kontrol alat, aksi file, batch sekunder, preview shell, dan status bar yang selalu menampilkan fase serta persentase.
- Mengganti emoji/glyph kontrol utama dengan label teks yang aman untuk Windows kantor.
- Memperbaiki root cause slider lag dengan cache bitmap display/checkerboard dan redraw terjadwal saat drag.
- Mengirim progress byte download model `pooch` ke progress bar UI untuk single image dan batch.
- Menambahkan `RUN_APP.vbs`; `RUN_APP.bat` tidak lagi melakukan `pip install` setiap start dan jalur source memakai `pythonw.exe`.
- Memperbarui arsitektur, error register, dan README yang terdampak.

### Bukti verifikasi aktual

- `python -m py_compile .\review-temp\WhiteFlood_BG_Remover_App\whiteflood_app.py`
- Static smoke test untuk slider cache, kontrak skala 2x/4x/8x, output alpha/dimensi, adapter progress, launcher, dan `CREATE_NO_WINDOW`.
- `git diff --check`

### Belum diverifikasi

- Manual GUI untuk drag Before/After.
- Download model nyata dan persentase dari koneksi internet.
- Jalur `RUN_APP.vbs` pada komputer kantor.
- Build atau run EXE.

### File

- `implementation_plan.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/ERROR_SOLUTIONS.md`
- `docs/WORKLOG.md`
- `review-temp/WhiteFlood_BG_Remover_App/README.md`
- `review-temp/WhiteFlood_BG_Remover_App/RUN_APP.bat`
- `review-temp/WhiteFlood_BG_Remover_App/RUN_APP.vbs`
- `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`

---

## 2026-08-08 - Build EXE windowed dari source terbaru

Status: Build selesai; runtime EXE belum diverifikasi.

### Hasil

- Menjalankan `BUILD_EXE.bat` setelah persetujuan Bima.
- Dependency project dan PyInstaller terdeteksi sudah tersedia.
- PyInstaller selesai dengan mode `--onefile --windowed`.
- EXE baru dibuat di `review-temp/WhiteFlood_BG_Remover_App/dist/WhiteFlood_BG_Remover.exe`.

### Bukti verifikasi aktual

- Exit code build: `0`.
- Ukuran file: `200,505,614` bytes (`191.22 MB`).
- Waktu dibuat: `2026-08-08 13:34:08`.
- SHA256: `2A36E97CCE8B3AF55A9289AD20533116C5F79BFD8D793A7A660CE658712D0B02`.
- Log build memberi warning tentang modul opsional `onnx`, `filetype`, dan `tbb12.dll`; belum ada bukti warning tersebut menghalangi jalur aplikasi.

### Belum diverifikasi

- Menjalankan EXE dan membuka GUI.
- Drag slider, remove background, upscale, dan download model dari EXE.
- Menjalankan EXE pada PC kantor.

### File/artefak

- `review-temp/WhiteFlood_BG_Remover_App/dist/WhiteFlood_BG_Remover.exe`
- `review-temp/WhiteFlood_BG_Remover_App/build/`
