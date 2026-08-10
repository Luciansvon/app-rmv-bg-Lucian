# Error Solutions WhiteFlood

## Tujuan

File ini menyimpan error atau bug yang benar-benar ditemukan, root cause, solusi, dan bukti verifikasi aktual.

File ini bukan daftar fitur, backlog, dugaan bug, atau tempat menulis klaim yang belum direproduksi.

## Status baseline

Register ini mulai berisi dua patch berbasis root cause dari audit source dan laporan penggunaan Bima. Status `Diverifikasi` hanya dipakai untuk pemeriksaan yang benar-benar dijalankan; keduanya tetap mencatat batasan GUI atau download nyata bila belum dilakukan.

## Aturan pencatatan

- Reproduce masalah sebelum mengubah kode jika kondisi memungkinkan.
- Cari root cause, jangan hanya menambal gejala.
- Catat versi aplikasi, Windows/Python, input yang dipakai, dan alat yang terdampak bila relevan.
- Bedakan error Remove Background, Upscale, UI, batch, packaging, dan environment.
- Catat apakah gambar input tetap utuh dan apakah output yang gagal sudah dibuat sebagian.
- Tambahkan regression test atau pemeriksaan manual yang relevan.
- Jangan menulis "lulus" tanpa command, langkah, atau bukti aktual.
- Jika GUI, model AI, GPU/Vulkan, atau build EXE belum diuji, tulis sebagai belum diverifikasi.
- Jangan menghapus entri lama. Tambahkan update status atau entri lanjutan.

## Format entri

```markdown
## ERR-001 - Judul singkat

Tanggal: YYYY-MM-DD
Versi: 2.5.0
Area: UI | Remove Background | Upscale | Batch | Packaging | Environment
Status: Terbuka | Diperbaiki | Diverifikasi | Ditunda

### Gejala

Apa yang user lihat dan kapan terjadi.

### Cara reproduksi

1. Langkah pertama.
2. Langkah berikutnya.
3. Hasil aktual.

### Hasil yang diharapkan

Behavior yang seharusnya terjadi.

### Root cause

Bukti penyebab masalah.

### Solusi

Perubahan yang dilakukan.

### Perlindungan regresi

Test atau pemeriksaan yang ditambahkan.

### Bukti verifikasi aktual

Command, environment, input, output, dan hasil.

### Batasan

Pemeriksaan yang belum dilakukan.

### File terdampak

- `path/to/file.py`
```

## ERR-001 - Split-slider preview tersendat saat digeser

Tanggal: 2026-08-08
Versi: 2.5.0
Area: UI
Status: Diperbaiki

### Gejala

Handle Before/After terasa berat dan tersendat saat mouse digeser.

### Cara reproduksi

1. Pilih gambar yang sudah memiliki hasil preview.
2. Geser handle split-slider berulang kali.
3. Event mouse memanggil redraw penuh pada setiap gerakan.

### Hasil yang diharapkan

Slider mengikuti pointer dengan respons ringan tanpa mengulang kerja resize gambar sumber pada setiap event.

### Root cause

`_update_slider_from_mouse()` sebelumnya langsung memanggil `redraw()`. Redraw mengulang resize `Image.LANCZOS`, pembuatan checkerboard, crop, komposit, dan `PhotoImage` saat event drag masih terus masuk.

### Solusi

- Cache bitmap display setelah resize berdasarkan ukuran canvas.
- Cache checkerboard hasil untuk sisi transparan.
- Jadwalkan satu redraw setiap frame sekitar 16 ms saat drag.
- Tetap invalidasi cache saat gambar atau ukuran canvas berubah.

### Perlindungan regresi

Static smoke test memeriksa keberadaan cache, scheduler redraw, dan batas posisi slider.

### Bukti verifikasi aktual

Pemeriksaan syntax dan static smoke test dijalankan pada source aktif. Manual drag pada GUI belum dijalankan.

### Batasan

Kelancaran visual dan FPS aktual pada gambar besar belum diukur pada komputer kantor.

### File terdampak

- `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`

## ERR-002 - Console launcher dan progress download model tidak terlihat di UI

Tanggal: 2026-08-08
Versi: 2.5.0
Area: Packaging | UI
Status: Diperbaiki

### Gejala

Jalur `RUN_APP.bat` menjalankan instalasi dependency dan Python foreground sehingga console dapat muncul. Progress download model `rembg` belum memiliki persentase byte yang tampil di aplikasi.

### Cara reproduksi

1. Jalankan source melalui `RUN_APP.bat`.
2. Perhatikan launcher melakukan `pip install` lalu menjalankan Python biasa.
3. Gunakan mode AI pada komputer yang belum memiliki model.

### Hasil yang diharapkan

Launcher tidak menampilkan console yang mengganggu, dan persentase download model tampil di progress bar aplikasi.

### Root cause

`RUN_APP.bat` sebelumnya meng-install dependency setiap kali start dan menjalankan `python`. `rembg` meneruskan `progressbar=True` ke `pooch`, tetapi progress bar bawaan menulis ke stderr, bukan ke state progress UI.

### Solusi

- `RUN_APP.vbs` menjalankan EXE windowed bila tersedia atau `pythonw.exe` untuk source.
- `RUN_APP.bat` hanya meneruskan ke launcher tersembunyi; dependency tidak lagi di-install setiap start.
- Adapter `_ModelDownloadProgress` menerima total dan byte dari `pooch`, lalu mengirim persentase yang di-throttle ke UI.

### Perlindungan regresi

Static smoke test memeriksa adapter progress, `pooch.retrieve` hook, `sess_opts`, `CREATE_NO_WINDOW`, dan tidak adanya `pip install` di launcher.

### Bukti verifikasi aktual

Pemeriksaan syntax dan static smoke test dijalankan. `BUILD_EXE.bat` juga berhasil membuat EXE windowed 200,505,614 bytes pada 2026-08-08 13:34:08. Download model nyata, GUI, dan smoke test EXE belum dijalankan.

### Batasan

Kesesuaian VBS pada instalasi Python/EXE kantor dan progress aktual dari koneksi internet belum diuji.

### File terdampak

- `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`
- `review-temp/WhiteFlood_BG_Remover_App/RUN_APP.bat`
- `review-temp/WhiteFlood_BG_Remover_App/RUN_APP.vbs`

## ERR-003 - Preset VTracer dan nama temporary MP4 tidak aman untuk engine

Tanggal: 2026-08-10
Versi: 2.5.0
Area: Vectorize | Remove Watermark Video
Status: Diperbaiki

### Gejala

Audit source menunjukkan preset Detailed mengirim `length_threshold=3.0`, sementara dokumentasi binding VTracer 0.6.x menetapkan rentang spline mulai 3.5. Pipeline video juga membentuk partial output dengan suffix `.partial`, sehingga container output tidak dapat diandalkan untuk ditebak dari nama file.

### Hasil yang diharapkan

Preset selalu memakai rentang parameter resmi binding yang dipin. Partial video tetap memiliki ekstensi/container MP4 dan divalidasi sebelum dipindahkan ke output final.

### Root cause

Konfigurasi preset belum dicocokkan kembali dengan README Python binding VTracer tag `0.6.15`. Nama temporary video sebelumnya menambahkan `.partial` setelah `.mp4`, sehingga ekstensi terakhir bukan lagi `.mp4`.

### Solusi

- Mengubah Detailed menjadi `length_threshold=3.5`.
- Menambahkan capability/version guard untuk `vtracer==0.6.15`.
- Mengubah partial video menjadi pola `<nama>.partial.mp4` dan menambahkan `-f mp4`.
- Memprobe partial output dan memvalidasi dimensi, FPS, durasi, serta jumlah frame sebelum atomic replace.

### Perlindungan regresi

- unittest memeriksa rentang preset VTracer.
- unittest memeriksa command encoder audio/video-only dan suffix MP4.
- unittest memeriksa penolakan dimension drift.

### Bukti verifikasi aktual

`python -m unittest discover -s tests -v` lulus dengan 8 test. AST parse source aktif juga lulus.

### Batasan

VTracer runtime dan FFmpeg Windows bundle belum dijalankan, jadi keberhasilan engine nyata dan kompatibilitas codec audio masih menunggu smoke test dengan dependency/model/binary yang disetujui.

### File terdampak

- `review-temp/WhiteFlood_BG_Remover_App/features/vectorize/presets.py`
- `review-temp/WhiteFlood_BG_Remover_App/features/vectorize/service.py`
- `review-temp/WhiteFlood_BG_Remover_App/features/watermark/video.py`
- `tests/test_features.py`

## ERR-004 - Tombol Process Watermark tetap disabled setelah mask digambar

Tanggal: 2026-08-10
Versi: 2.5.0
Area: UI | Remove Watermark
Status: Diperbaiki

### Gejala

Canvas sudah menampilkan overlay mask merah setelah brush dipakai, tetapi tombol `Process Image` tetap abu-abu dan tidak bisa ditekan.

### Root cause

`MaskCanvas` memperbarui mask internal saat operasi selesai, tetapi tidak mengirim callback ke `WhiteFloodApp`. Akibatnya `_update_button_states()` hanya berjalan saat file/tool berubah, bukan setelah mask berubah.

### Solusi

- Menambahkan `change_callback` pada `MaskCanvas`.
- Callback dipanggil setelah commit brush/rectangle/eraser, undo, redo, clear, dan set image.
- `WhiteFloodApp` langsung menghitung ulang state tombol dan menampilkan jumlah region mask.

### Perlindungan regresi

Unittest kontrak memeriksa callback mask. GUI click test belum dijalankan.

### Bukti verifikasi aktual

- `python -m py_compile ...` lulus.
- `python -m unittest discover -s tests -v` lulus dengan 11 test.

### Batasan

EXE baru dan klik manual pada canvas belum diuji pada GUI.

### File terdampak

- `review-temp/WhiteFlood_BG_Remover_App/features/watermark/mask_canvas.py`
- `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`
- `tests/test_features.py`

## ERR-005 - Model LaMa tidak ditemukan saat Remove Watermark

Tanggal: 2026-08-10
Versi: 2.5.0
Area: Remove Watermark | Packaging
Status: Diperbaiki

### Gejala

Saat proses Remove Watermark dijalankan dari EXE, aplikasi menampilkan `Model LaMa tidak ditemukan`.

### Root cause

Model LaMa belum tersedia di `assets/models/`, dan workflow watermark belum memiliki dialog persetujuan atau downloader aplikasi. Folder `_MEIPASS` pada one-file EXE juga bukan lokasi penyimpanan model user yang persisten.

### Solusi

- Menambahkan lookup model ke bundle/source lalu `%LOCALAPPDATA%\\WhiteFlood\\models`.
- Menambahkan dialog konfirmasi sebelum download.
- Menambahkan download ONNX resmi OpenCV Zoo ke file `.part`, progress byte, cancellation, validasi ukuran minimum, dan atomic replace.
- Download berjalan di worker; terminal tidak dipakai untuk progress.

### Perlindungan regresi

Unittest fake downloader memeriksa progress byte, instalasi atomic, dan cleanup file `.part`.

### Bukti verifikasi aktual

- `python -m py_compile ...` lulus.
- `python -m unittest discover -s tests -v` lulus dengan 11 test.
- Download internet nyata, inferensi LaMa, dan GUI belum dijalankan.

### Batasan

Model baru akan diunduh saat user menyetujui dialog di EXE baru. Model tidak diunduh selama build ini.

### File terdampak

- `review-temp/WhiteFlood_BG_Remover_App/features/model_download.py`
- `review-temp/WhiteFlood_BG_Remover_App/features/watermark/inpaint.py`
- `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`

## ERR-007 - FFprobe tidak tersedia di EXE Watermark Video

Tanggal: 2026-08-10
Versi: 2.5.0
Area: Remove Watermark Video | Packaging
Status: Diperbaiki

### Gejala

Saat user memilih video dari EXE, aplikasi menampilkan `ffprobe.exe belum tersedia di bundle WhiteFlood`.

### Root cause

Folder `ffmpeg/` hanya berisi README dan notice, tetapi source video dan PyInstaller sudah mengharapkan `ffmpeg.exe` serta `ffprobe.exe` di folder resource tersebut.

### Solusi

- Menambahkan binary Windows x64 LGPL yang dipin ke folder `ffmpeg/`.
- Menambahkan `LICENSE.txt`, checksum binary, dan metadata release.
- Menambahkan preflight build agar EXE tidak bisa dibuat ketika binary wajib hilang.
- Menambahkan unit test yang menjalankan kedua binary dengan `-version`.

### Bukti verifikasi aktual

- Archive BtbN release pin terverifikasi dengan SHA-256.
- `ffmpeg.exe -version` dan `ffprobe.exe -version` exit code 0.
- `python -m unittest discover -s tests -v` lulus dengan 11 test.
- Build `BUILD_EXE.bat` lulus; TOC PyInstaller mencatat kedua binary FFmpeg di dalam package.

### File terdampak

- `review-temp/WhiteFlood_BG_Remover_App/ffmpeg/`
- `review-temp/WhiteFlood_BG_Remover_App/build_exe.py`
- `tests/test_features.py`
- `tests/test_features.py`

## ERR-006 - Logo window tampak terlalu kecil

Tanggal: 2026-08-10
Versi: 2.5.0
Area: UI | Packaging
Status: Diperbaiki

### Gejala

Logo pada title bar dan header sidebar tampak kecil walaupun file logo berukuran besar.

### Root cause

Logo memiliki area transparan besar; alpha bounding box `logo.png` hanya sekitar bagian tengah gambar. `iconbitmap` memakai seluruh canvas sehingga mark terlihat mengecil pada ukuran icon Windows.

### Solusi

- Crop berbasis alpha bounding box saat runtime tanpa mengubah file asset asli.
- Terapkan hasil crop ke `iconphoto` title bar.
- Tampilkan mark crop yang sama di header sidebar dengan ukuran yang lebih terbaca.

### Perlindungan regresi

Ukuran dan alpha bounding box asset diperiksa secara read-only. Syntax check lulus; visual GUI belum dijalankan.

### File terdampak

- `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`

## ERR-008 - Download model tersendat saat window diminimize

Tanggal: 2026-08-10
Versi: 2.6.0
Area: UI | Remove Background | Remove Watermark
Status: Diperbaiki

### Gejala

Saat model AI sedang diunduh lalu window WhiteFlood diminimize, progress dapat terlihat berhenti dan download tidak memberi hasil yang meyakinkan.

### Cara reproduksi

1. Jalankan workflow yang belum memiliki model AI.
2. Setujui dialog download model.
3. Minimize window ketika progress download berjalan.

### Hasil yang diharapkan

Download tetap berjalan di background selama proses WhiteFlood masih hidup. Progress kembali diproses oleh UI saat event loop berjalan, dan window close tetap membatalkan proses dengan aman.

### Root cause

Callback progress dari worker sebelumnya memanggil `self.after(...)` Tkinter secara langsung dari thread worker. Jalur download model ikut bergantung pada komunikasi lintas thread yang tidak memiliki antrean event khusus. Source juga tidak melacak worker secara terpusat saat proses ditutup.

### Solusi

- Menambahkan `_UiEventQueue` yang thread-safe.
- Mengubah callback worker untuk memasukkan progress/hasil ke queue, bukan memanggil Tkinter langsung.
- Main thread menguras queue setiap 50 ms, termasuk saat window diminimize.
- Menambahkan tracking worker dan mempertahankan cancel-on-close serta cleanup model parsial yang sudah ada.

### Perlindungan regresi

Unittest memverifikasi event yang diposting dari thread worker baru diterapkan saat main thread menguras queue. Downloader fake tetap memverifikasi progress byte, atomic install, dan cleanup `.part`.

### Bukti verifikasi aktual

- `python -m py_compile .\review-temp\WhiteFlood_BG_Remover_App\whiteflood_app.py` dijalankan.
- `python -m unittest discover -s tests -v` dijalankan.
- GUI minimize dan download internet nyata belum dijalankan pada sesi ini.

### Batasan

Belum ada bukti runtime bahwa file model nyata selesai saat window diminimize; pemeriksaan itu membutuhkan GUI, koneksi internet, dan model yang belum tersedia.

### File terdampak

- `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`
- `tests/test_features.py`

## ERR-009 - Progress Remove Background berhenti di 70%

Tanggal: 2026-08-10
Versi: 2.6.0
Area: UI | Remove Background
Status: Diperbaiki

### Gejala

Saat Hapus Background dimulai, progress naik dari loading awal ke 70% lalu tampak
stuck. Screenshot user menunjukkan status tersebut setelah proses berjalan cukup lama.

### Root cause

`ai_remove_bg()` mengirim progress numerik 70% tepat sebelum `rembg_remove()` menjalankan
inferensi AI. Fungsi rembg tidak menyediakan callback progress kontinu untuk tahap ini,
sehingga UI menampilkan angka yang tidak bisa diperbarui sampai inferensi selesai.

### Solusi

- Mengganti event 70% dengan fase `phase_indeterminate` berlabel
  `Menjalankan AI lokal untuk menghitung mask objek...`.
- Mengubah progress bar horizontal ke mode indeterminate selama fase tanpa progress
  kontinu; circular spinner tetap bergerak.
- Mengembalikan progress bar ke mode determinate saat event angka berikutnya diterima
  atau workflow selesai.

### Perlindungan regresi

Unittest memakai engine rembg palsu untuk memastikan fase indeterminate diterima sebelum
inferensi dan menguji perpindahan progress bar kembali ke determinate.

### Bukti verifikasi aktual

- Syntax check source dijalankan.
- `python -m unittest discover -s tests -v` dijalankan.
- `git diff --check` dijalankan.
- GUI dengan model nyata belum dijalankan pada sesi ini.

### File terdampak

- `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`
- `tests/test_features.py`
- `docs/ARCHITECTURE.md`
