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
- Model LaMa akan diunduh ke folder user saat disetujui. Binary FFmpeg bundle ditambahkan pada gate berikutnya dan dicatat di bawah.

### File utama

- `review-temp/WhiteFlood_BG_Remover_App/features/model_download.py`
- `review-temp/WhiteFlood_BG_Remover_App/features/watermark/inpaint.py`
- `review-temp/WhiteFlood_BG_Remover_App/features/watermark/mask_canvas.py`
- `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`
- `tests/test_features.py`

---

## 2026-08-10 - Membundel FFmpeg untuk Watermark Video

Status: binary source, preflight build, dan build EXE selesai; runtime GUI masih pending.

### Perubahan

- Menambahkan `ffmpeg.exe`, `ffprobe.exe`, `LICENSE.txt`, dan `checksums.sha256` ke folder source `ffmpeg/`.
- Mem-pin BtbN `autobuild-2026-08-09-13-03`, asset FFmpeg 8.1.2 LGPL Windows x64.
- Menambahkan preflight `build_exe.py` agar build berhenti dengan pesan jelas jika binary video hilang.
- Menambahkan unit test yang menjalankan `ffmpeg.exe -version` dan `ffprobe.exe -version`.

### Bukti verifikasi aktual

- Archive 139.1 MB terunduh dari release pin dan checksum archive cocok.
- `ffmpeg.exe -hide_banner -version` exit code 0.
- `ffprobe.exe -hide_banner -version` exit code 0.
- Hash binary dicatat di `review-temp/WhiteFlood_BG_Remover_App/ffmpeg/checksums.sha256`.
- `python -m unittest discover -s tests -v` lulus: 11 test.
- Build `BUILD_EXE.bat` lulus dalam sekitar 4 menit 30 detik.
- EXE: `dist/WhiteFlood_BG_Remover.exe`, 295.687.413 bytes, dibuat 2026-08-10 10:42:39.
- SHA-256: `5CCBAE993165913FBF6E5B618E5D8AB7EC1098C78A16772E8525F3312170F549`.
- PyInstaller TOC mencatat `ffmpeg/ffmpeg.exe` dan `ffmpeg/ffprobe.exe` masuk ke package.
- Binary `.exe` disiapkan untuk tracking Git LFS karena masing-masing berukuran lebih dari 100 MB.

### Gate pending

- Smoke test video dengan fixture nyata.

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

---

## 2026-08-10 - Timestamp durasi semua workflow

Status: source patch, unit test, dan build EXE selesai; GUI runtime masih pending.

### Perubahan

- Menambahkan timer live `Durasi HH:MM:SS` di status bar.
- Timer dimulai saat worker proses benar-benar dimulai dan berhenti saat selesai, gagal, atau dibatalkan.
- Durasi final ditulis ke status Remove Background, Upscale, Vectorize, Remove Watermark Image/Video, dan batch.
- Menambahkan formatter duration sebagai kontrak unit test.

### Bukti verifikasi aktual

- `python -m py_compile ...` lulus.
- `python -m unittest discover -s tests -v` lulus: 12 test.
- `git diff --check` lulus; warning hanya normalisasi LF/CRLF Git.
- Build `BUILD_EXE.bat` lulus dalam sekitar 6 menit 27 detik.
- EXE: `dist/WhiteFlood_BG_Remover.exe`, 295.689.770 bytes, dibuat 2026-08-10 11:22:19.
- SHA-256: `92CADFB632FACACD8F9828AC08840F2A8A22F7648D96E998053004A64BAB89E8`.

### Gate pending

- GUI smoke test untuk memastikan label timer terlihat dan berhenti di semua workflow.

---

## 2026-08-10 - Processing speed modes

Status: source implementation, unit test, dan build EXE selesai; GUI runtime masih pending.

### Perubahan

- Menambahkan selector `Lambat`, `Cepat`, dan `Super Cepat` pada workflow yang memiliki trade-off speed nyata.
- `Cepat` menjadi default; `Lambat` memprioritaskan resource lebih rendah dan konteks LaMa lebih aman.
- `Super Cepat` memakai thread/resource lebih tinggi, tile/context lebih kecil, serta meminta konfirmasi warning sebelum proses.
- Profil yang sama dipakai single image dan batch untuk Remove Background, Upscale, Vectorize, dan Remove Watermark.
- `White Background` tidak menampilkan selector karena algoritmanya tidak memiliki parameter speed yang aman untuk diubah.

### Bukti verifikasi aktual

- Syntax check untuk source dan service lulus.
- `python -m unittest discover -s tests -v` lulus: 14 test.
- `git diff --check` lulus; warning hanya normalisasi LF/CRLF Git.
- Build release PyInstaller dengan konfigurasi setara `BUILD_EXE.bat` lulus dalam sekitar 3 menit 48 detik; output dibuat di staging temporary karena EXE pada `dist/` sedang dipakai.
- EXE release: `WhiteFlood_BG_Remover.exe`, 295.694.770 bytes, dibuat 2026-08-10 12:06:54.
- SHA-256: `C97C1E3C152FB9F9F0B9A74BBDB0B14E3885F3EFFBDF25784554A7319E231B85`.

### Gate pending

- GUI smoke test selector, warning, dan parameter speed di workflow utama.

---

## 2026-08-10 - Release v2.6.0

Status: release publik dibuat dan asset EXE terupload; link download README sudah diarahkan ke release baru.

### Bukti release

- Release: https://github.com/Luciansvon/app-rmv-bg-Lucian/releases/tag/v2.6.0
- Asset: `WhiteFlood_BG_Remover.exe`, status GitHub `uploaded`.
- Asset digest GitHub cocok dengan SHA-256 build: `C97C1E3C152FB9F9F0B9A74BBDB0B14E3885F3EFFBDF25784554A7319E231B85`.

### Catatan gate

- GUI smoke test khusus selector speed belum dijalankan pada sesi release ini; release dibuat atas permintaan Bima setelah build dan unit test lulus.

---

## 2026-08-10 - Download model tetap berjalan saat window diminimize

Status: source patch dan static/unit verification selesai; GUI minimize serta download internet nyata masih pending.

### Perubahan

- Menambahkan queue thread-safe untuk memisahkan callback worker dari Tkinter main thread.
- Mengubah worker Vectorize, Remove Watermark, Remove Background/Upscale, dan batch agar mengirim event UI melalui queue.
- Menambahkan tracking worker dan mempertahankan cancel-on-close sebelum window dihancurkan.

### Bukti verifikasi aktual

- `python -m py_compile .\review-temp\WhiteFlood_BG_Remover_App\whiteflood_app.py` lulus.
- `python -m unittest discover -s tests -v` lulus: 15 test, termasuk kontrak event worker-to-main-thread dan fake model downloader.
- `git diff --check` lulus; warning hanya normalisasi LF/CRLF Git.

### Gate pending

- GUI smoke test: mulai download model, minimize window, pantau file `.part`, lalu pastikan file model final tersedia.
- Download internet nyata dan runtime EXE belum dijalankan.

---

## 2026-08-10 - Progress Remove Background tidak lagi palsu di 70%

Status: source patch dan static/unit verification selesai; GUI dengan model nyata masih pending.

### Perubahan

- Menghapus event numerik 70% sebelum inferensi `rembg_remove()`.
- Menampilkan fase indeterminate dengan pesan bahwa AI lokal sedang menghitung mask objek.
- Mengembalikan horizontal progress bar ke mode determinate saat progress numerik kembali tersedia.

### Bukti verifikasi aktual

- `python -m py_compile .\\review-temp\\WhiteFlood_BG_Remover_App\\whiteflood_app.py` lulus.
- `python -m unittest discover -s tests -v` lulus dengan 17 test.
- `git diff --check` lulus; warning hanya normalisasi LF/CRLF Git.

### Gate pending

- GUI smoke test Hapus Background dengan model lokal nyata untuk memastikan animasi indeterminate,
  hasil 100%, dan durasi selesai terlihat pada EXE/runtime.

---

## 2026-08-10 - Audit bugfix dan build v2.6.1

Status: release publik v2.6.1 dibuat setelah audit source, patch,
static/unit verification, build, dan push selesai.

### Perubahan

- Mengaktifkan perilaku `Mode Agresif` pada White Background.
- Menyembunyikan kontrol White Background saat mode lain aktif.
- Mereset media state saat file baru gagal dibuka dan mengunci mask/control
  saat worker sedang memproses snapshot.
- Memisahkan RGB dan alpha pada Upscale transparan, termasuk padding warna tepi,
  resize alpha Lanczos, dan merge RGBA berukuran tepat.
- Menyelaraskan teks ukuran model dengan dokumentasi project dan menaikkan versi
  aplikasi ke v2.6.1.

### Bukti verifikasi aktual

- `python -m py_compile .\review-temp\WhiteFlood_BG_Remover_App\whiteflood_app.py .\review-temp\WhiteFlood_BG_Remover_App\features\watermark\mask_canvas.py` lulus.
- `python -m unittest discover -s tests -v` lulus: 21 test.
- `git diff --check` untuk file patch lulus; warning repository penuh hanya
  berasal dari backup lama yang tidak disentuh.
- `python build_exe.py` lulus dengan exit code 0 pada Python 3.12.10 dan
  PyInstaller 6.21.0.
- Artifact: `review-temp/WhiteFlood_BG_Remover_App/dist/WhiteFlood_BG_Remover.exe`,
  dibuat 2026-08-10 17:25:16, ukuran 294,711,783 bytes (281.06 MiB),
  SHA-256 `CE1FAE8D148AC540DF5EAD7AEB746B7F93126E5DA0AB69E593ECA040784809A`.
- Paket build terdeteksi membawa FFmpeg, Real-ESRGAN binary/model, dan logo.

### Catatan risiko

- Build log masih memuat warning dependency opsional `onnx`, `filetype`,
  `pycparser`, `scipy`, dan `tbb12.dll`; build tetap exit 0.
- GUI EXE, model nyata, dan GPU Vulkan belum dijalankan karena membutuhkan
  smoke test runtime terpisah.

### Bukti release

- Commit: `53b004722a02c581a57df577ee45f9066324730c` pada branch
  `codex/fix-remove-bg-progress`.
- Release: https://github.com/Luciansvon/app-rmv-bg-Lucian/releases/tag/v2.6.1
- Asset `WhiteFlood_BG_Remover.exe` berstatus GitHub `uploaded`, ukuran
  294,711,783 bytes.
- Digest GitHub `sha256:ce1fae8d148ac540df5ead7aeb746b7f93126e5da0ab69e593eca040784809a`
  cocok dengan hash lokal.

---

## 2026-08-11 - Fix unduhan model 15% dan persiapan v2.6.2

Status: source patch, test, build, dan smoke start EXE selesai; release sedang berjalan.

### Perubahan

- Menghapus progress awal dummy 15% pada worker dan 5% sebelum model session.
- Menambahkan fase menghubungkan server, progress byte asli, verifikasi file,
  dan pemuatan model lokal.
- Download Pooch memakai chunk 64 KiB, connect timeout 15 detik, read timeout
  30 detik, serta retry maksimal tiga kali.
- Error menjelaskan kemungkinan firewall/proxy kantor dan lokasi model
  `%USERPROFILE%\\.u2net`.
- README menambahkan monitor PowerShell read-only untuk ukuran file model.
- Menaikkan versi aplikasi menjadi v2.6.2.

### Bukti verifikasi aktual

- Syntax check source aktif lulus.
- `python -m unittest discover -s tests -v` lulus: 25 test.
- Smoke download file kecil dari repository resmi Pooch melalui HTTPS selesai;
  adapter UI menerima event progress sampai 100%.
- Endpoint BiRefNet-Massive merespons HTTP 200 dari
  `release-assets.githubusercontent.com` dengan content-length 972,666,916 byte.
- Build PyInstaller selesai dengan `Build complete`.
- Artifact: `review-temp/WhiteFlood_BG_Remover_App/dist/WhiteFlood_BG_Remover.exe`,
  dibuat 2026-08-11 09:33:56, ukuran 294,709,318 bytes (281.06 MiB), SHA-256
  `51DAE4515C8166AAA556F36EEDECB17F732F9851152524C4ABEEB6B440C826AB`.
- Smoke start EXE selama 15 detik berhasil; proses tetap hidup dan ditutup setelah
  pemeriksaan.

### Gate berjalan

- Final diff check, commit, push, dan GitHub Release v2.6.2.
- Rendering GUI serta unduhan penuh BiRefNet pada PC kantor belum diverifikasi.
