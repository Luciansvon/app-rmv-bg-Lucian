# Arsitektur WhiteFlood BG Remover & Upscaler

## Status dokumen

Dokumen ini adalah baseline arsitektur berdasarkan source, `README.md`, dan `user.md` yang ada pada 8 Agustus 2026.

Status verifikasi sebelum patch UI:

- source aktif berada di `review-temp/WhiteFlood_BG_Remover_App/whiteflood_app.py`;
- aplikasi memakai Python desktop Windows dengan CustomTkinter/Tkinter;
- alur single-image dan batch sudah terlihat di source;
- Remove Background memakai jalur `rembg`/ONNX atau mode White Background lokal;
- Upscale memanggil backend `realesrgan-ncnn-vulkan.exe` melalui subprocess;
- pemeriksaan runtime GUI, pemrosesan gambar nyata, dan build EXE tidak dijalankan saat dokumen baseline dibuat.

Perubahan patch 2026-08-08 sudah diperiksa melalui syntax check dan static smoke test. Build EXE windowed juga sudah dijalankan setelah persetujuan Bima; GUI dan download model nyata tetap belum dijalankan.

Jangan mengubah status menjadi "terverifikasi" hanya karena fungsi atau komentar sudah ada di source.

Status implementasi fitur 2026-08-10:

- visual baseline enam page dari `docs/WHITEFLOOD_UI_REDESIGN.md` sudah diterapkan ke source aktif;
- source resmi VTracer tag `0.6.15`, OpenCV Zoo LaMa, dan dokumentasi FFmpeg sudah diaudit sebagai acuan adapter;
- service Vectorize, mask, LaMa, media, dan video streaming sudah ditambahkan;
- downloader model persisten, prompt persetujuan, progress byte di UI, dan circular progress workflow sudah ditambahkan ke source;
- profil speed `Lambat`, `Cepat`, dan `Super Cepat` sudah ditambahkan dengan warning UI dan parameter konkret per engine;
- crop logo berbasis alpha untuk title bar dan header sidebar sudah ditambahkan ke source;
- unittest kontrak service sudah ditambahkan dan lulus;
- GUI smoke test, VTracer conversion runtime, model LaMa, dan binary FFmpeg belum dijalankan; build patch UI sudah lulus tetapi runtime EXE belum diuji.

## Tujuan dan batas sistem

WhiteFlood adalah aplikasi desktop Windows lokal untuk foto produk furnitur dan katalog kantor. Workspace sekarang memiliki lima workflow yang dipilih user secara terpisah:

1. Remove Background;
2. Upscale 2x, 4x, atau 8x.
3. Vectorize Image ke SVG;
4. Remove Watermark Image;
5. Remove Watermark Static Video.

Operasional dasar tidak memakai server aplikasi. Model AI dapat perlu diunduh pada penggunaan pertama, tetapi gambar diproses di komputer user dan hasil disimpan sebagai PNG ke path yang dipilih user.

## Bentuk sistem

```mermaid
flowchart TD
    U["User Windows"] --> UI["CustomTkinter UI"]
    UI --> S["WhiteFloodApp state"]
    S --> W{"Alat aktif"}
    W --> BG["Remove Background"]
    W --> UP["Upscale 2x / 4x / 8x"]
    W --> VX["Vectorize Image"]
    W --> WM["Remove Watermark"]
    BG --> AI["rembg + ONNX atau White Background"]
    UP --> NCNN["realesrgan-ncnn-vulkan.exe"]
    VX --> VT["VTracer 0.6.15"]
    WM --> MC["MaskCanvas source-pixel"]
    MC --> LAMA["LaMa ONNX + ONNX Runtime"]
    WM --> VP["VideoProcessor + bundled FFmpeg"]
    AI --> OUT["PNG output"]
    NCNN --> OUT
    VT --> SVG["Validated SVG"]
    LAMA --> OUT
    VP --> VIDEO["Validated MP4"]
```

## Struktur source aktif

```text
review-temp/WhiteFlood_BG_Remover_App/
|-- whiteflood_app.py       # UI, state, pipeline, single-image, batch
|-- requirements.txt        # dependency runtime Python
|-- RUN_APP.bat              # entry point singkat ke launcher tersembunyi
|-- RUN_APP.vbs              # menjalankan source dengan pythonw atau EXE tanpa console
|-- BUILD_EXE.bat            # install/build dengan PyInstaller
|-- build_exe.py             # konfigurasi command PyInstaller
|-- logo.ico, logo.png       # aset branding
|-- features/
|   |-- performance.py       # profil speed/resource lintas workflow
|   |-- model_download.py      # downloader model persisten dan atomic
|   |-- vectorize/            # preset dan adapter VTracer
|   `-- watermark/            # mask, LaMa, media, dan video pipeline
|-- assets/models/            # lokasi model LaMa; model tidak dikomit
|-- ffmpeg/                   # lokasi binary FFmpeg LGPL yang dipin
`-- realesrgan/               # executable, DLL, dan model backend upscale
```

`whiteflood_app.py` tetap menjadi penghubung UI/state/callback. Core feature yang perlu lifecycle, validasi, atau subprocess dipisahkan ke `features/` supaya tidak memperbesar file UI dan lebih mudah diuji tanpa membuka GUI.

## Lapisan dan tanggung jawab

### UI dan state

- `WhiteFloodApp` mengelola window, sidebar, pilihan alat, pilihan mode, progress, status, preview, dan dialog file.
- `SplitSliderPreview` menampilkan gambar asli dan hasil sebelum/sesudah. Bitmap display dan checkerboard di-cache berdasarkan ukuran canvas; drag hanya menjadwalkan satu redraw ringan setiap frame.
- `active_tool` membedakan Workspace, Remove Background, Upscale, Vectorize, serta mode Watermark Image/Video.
- Tombol proses, simpan, dan batch dikunci melalui state `_processing` agar proses ganda tidak berjalan bersamaan.
- Adapter `_ModelDownloadProgress` meneruskan byte download `pooch` ke progress bar dan circular progress UI sehingga persentase serta ukuran model terlihat di aplikasi.
- Downloader `features/model_download.py` menyimpan LaMa di folder user yang writable; dialog konfirmasi muncul sebelum download pertama.
- `_UiEventQueue` menerima callback dari worker tanpa memanggil Tkinter langsung; main thread menguras queue berkala sehingga download tetap berjalan saat window diminimize.
- Worker single-image, watermark, vectorize, dan batch dilacak oleh `WhiteFloodApp`; close tetap mengirim cancel lalu menunggu worker berhenti sebelum window dihancurkan.
- `LoadingSpinner` menjadi circular progress determinate untuk workflow yang memiliki progress dan tetap indeterminate saat engine tidak menyediakan angka kontinu.
- Progress bar horizontal memakai aturan yang sama: tahap inferensi Remove Background yang tidak menyediakan callback kontinu menampilkan animasi indeterminate dan `...`, bukan persentase tebakan; event angka berikutnya mengembalikannya ke determinate.
- Timer proses terpusat memakai `time.perf_counter()` dan callback `after()` Tkinter; label `Durasi HH:MM:SS` berhenti pada sukses, error, atau cancel untuk single image, vector, watermark, upscale, dan batch.
- `features/performance.py` menjadi source of truth untuk selector speed; mode hanya tampil pada tool yang memiliki parameter speed nyata dan `White Background` tidak menampilkan kontrol pajangan.
- Mode `Lambat` memakai thread lebih rendah, tile/context lebih aman, dan encoder lebih konservatif; `Cepat` menjadi default; `Super Cepat` memakai thread lebih tinggi, tile/context lebih kecil, dan meminta konfirmasi warning.

### Single-image workflow

1. User memilih alat lalu memilih file.
2. `PIL.Image.open` membaca gambar dan mempertahankan informasi alpha jika tersedia.
3. Gambar asli langsung ditampilkan sebelum proses berat dimulai; memilih file tidak memproses otomatis.
4. User menekan aksi proses yang sesuai dengan alat aktif.
5. Worker thread mengerjakan proses berat agar UI tetap merespons.
6. Worker memasukkan status proses dan progress download/model/frame ke `_UiEventQueue`.
7. Callback `after` Tkinter pada main thread menguras queue dan mengembalikan event ke UI.
8. Hasil dikembalikan ke UI; user memilih Export/Simpan, lalu output divalidasi.

### Remove Background pipeline

- Mode AI memakai `ai_remove_bg`, session lazy-load, dan model `birefnet-*` melalui `rembg`.
- Mode White Background memakai `flood_remove_bg` untuk background putih/abu-abu polos tanpa model AI.
- Mode speed diteruskan ke session ONNX melalui `intra_op_num_threads`; perpindahan profil dapat membuat session lama dilepas agar konfigurasi thread tidak tercampur.
- `refine_alpha_mask` menangani penghalusan atau erosi alpha sesuai pengaturan.
- Pipeline menetapkan ukuran yang diharapkan sama dengan ukuran input.
- Hasil dikonversi ke RGBA dan disimpan sebagai PNG.

### Upscale pipeline

- `upscale_image_alpha_safe` membuat folder temporary untuk input dan output backend.
- Backend eksternal dipanggil melalui `subprocess.Popen`.
- Profil speed mengatur tile NCNN dan job string `-j`; model, alpha, dan kontrak dimensi tidak berubah.
- Skala 2x atau 4x dikirim langsung ke backend; skala 8x memakai pass AI 4x lalu resize Lanczos 2x.
- Gambar dengan alpha dipadding warnanya di sekitar tepi yang terlihat, RGB dikirim terpisah ke backend, alpha diperbesar dengan Lanczos, lalu keduanya digabung kembali sebagai RGBA.
- Gambar tanpa alpha tetap dikirim dan dikembalikan sebagai RGB.
- `process_file` menetapkan ukuran yang diharapkan sebagai `(lebar * skala, tinggi * skala)`.

### Batch workflow

- `process_folder` menerima PNG, JPG, JPEG, WEBP, dan BMP.
- File diproses satu per satu dalam worker thread.
- `_get_next_sequence_name` membersihkan nama batch dan mencari nomor yang belum dipakai.
- Batch tersedia untuk Remove Background, Upscale, dan Vectorize Image; Watermark Image/Video sengaja tidak menampilkan batch pada MVP.
- Output batch memakai pola `<nama-batch>-<nomor>.png` atau `.svg` dan tidak boleh menimpa file yang sudah ada.
- User dapat membatalkan batch; gambar yang sedang berjalan boleh selesai sebelum worker berhenti.

### Vectorize Image

- `VectorizeService` memanggil API Python VTracer 0.6.x `convert_image_to_svg_py` dengan preset Logo, Illustration, Line Art, atau Detailed.
- Input dibatasi ke PNG, JPG/JPEG, WebP, dan BMP.
- VTracer bekerja di temporary directory. XML root SVG dan elemen grafis diverifikasi sebelum hasil disimpan secara atomic.
- Progress memakai tahap 10/25/85/100% untuk feedback visual; VTracer tidak menyediakan persentase kontinu yang bisa dipercaya.
- Profil `Cepat`/`Super Cepat` dapat membatasi iterasi/path precision dan menambah speckle filter untuk memendekkan kerja VTracer; output tetap divalidasi sebagai SVG.
- Preview tidak merender SVG native; UI hanya menampilkan status validasi dan informasi output.

### Remove Watermark Image

- `MaskCanvas` menyimpan mask L pada ukuran pixel source, sementara canvas hanya menampilkan preview letterbox + zoom.
- Brush, rectangle, eraser, clear, undo/redo, dan multi-stroke tersedia tanpa tracking/auto-detect.
- `LamaInpaintService` melakukan ROI context dan tile 512px overlap; komposisi hanya mengganti area mask.
- Profil speed mengatur context/overlap LaMa; `Super Cepat` memberi warning karena konteks lebih kecil dapat meninggalkan seam/halo pada watermark kompleks.
- Model LaMa dicari dari bundle/source lalu folder user `%LOCALAPPDATA%\\WhiteFlood\\models`; jika belum ada, user ditanya sebelum downloader berjalan.
- Progress image watermark mengikuti tile yang selesai dan progress video mengikuti frame yang selesai.
- Alpha input dipasang kembali ke hasil dan ukuran output harus sama persis.

### Remove Watermark Static Video

- `probe_video` memakai ffprobe bundle dan mengembalikan ukuran visual setelah autorotate, FPS nominal/average, durasi, audio, rotasi, dan VFR warning.
- `VideoProcessor` membaca raw BGR frame satu per satu dari FFmpeg, memproses dengan mask yang sama, lalu menulis frame ke encoder MP4.
- Profil speed diteruskan ke LaMa per frame dan menambahkan jumlah thread encoder FFmpeg tanpa mengubah container, audio policy, FPS, atau validasi output.
- Audio dicoba dengan `-c:a copy`; fallback video-only hanya dilakukan jika stderr encoder mengindikasikan masalah mux audio.
- Partial output memakai ekstensi `.mp4` agar FFmpeg mengenali container, divalidasi dengan ffprobe sebelum dipindahkan, lalu dibersihkan saat cancel/error.
- Event cancellation menghentikan loop dan terminasi subprocess setelah frame yang sedang aman dilepas.

### Penyimpanan dan metadata

- Tidak ada database atau penyimpanan state aplikasi yang menjadi source of truth.
- Output disimpan sebagai PNG melalui Pillow.
- `metadata_for_save` digunakan untuk membawa metadata yang didukung ke output.
- Setelah penyimpanan, ukuran file dibaca ulang. Jika berbeda dari ukuran yang diharapkan, proses dianggap gagal.

## Memory dan engine berat

- Session `rembg` disimpan lazy-load pada `_rembg_session`.
- Session LaMa disimpan lazy-load pada `LamaInpaintService` dan dilepas saat pindah engine atau aplikasi ditutup.
- Saat model berubah atau alat berpindah, session lama dilepas dan `gc.collect()` dipanggil.
- ONNX SessionOptions mengatur `enable_cpu_mem_arena = False` pada jalur session yang tersedia.
- RAM ditampilkan melalui `get_process_memory_mb` sebagai RSS proses.
- Angka RAM pada README adalah klaim produk sampai diukur ulang dengan environment dan input yang disebutkan; bukan bukti otomatis dari source.

Jangan menambah engine berat aktif paralel, cache model tambahan, atau proses batch paralel tanpa pengukuran dan persetujuan perubahan arsitektur.

## Packaging

- `BUILD_EXE.bat` memasang dependency dan PyInstaller, membersihkan artefak build lama, lalu menjalankan `build_exe.py`.
- `build_exe.py` membuat executable one-file windowed bernama `WhiteFlood_BG_Remover.exe`.
- `RUN_APP.vbs` memilih EXE di `dist` bila tersedia; jika belum ada, launcher memakai `pythonw.exe` untuk source agar console tidak muncul.
- Aset logo, folder `realesrgan`, metadata package, dan dependency runtime dikumpulkan ke bundle.
- Folder `assets/` dan `ffmpeg/` menjadi resource path development/`_MEIPASS`; LaMa dapat diunduh ke folder user writable, sedangkan `ffmpeg.exe`, `ffprobe.exe`, license, dan checksum sudah disertakan untuk build distribusi. Binary `.exe` ditrack dengan Git LFS.
- Script build bersifat destruktif terhadap `build/`, `dist/`, dan file `.spec`; target harus diperiksa sebelum dijalankan.

Build release terakhir yang dicek:

- Command: `python build_exe.py` dengan konfigurasi PyInstaller one-file windowed.
- Output: `WhiteFlood_BG_Remover.exe` pada asset release `v2.6.1`, 294,711,783 bytes, dibuat 2026-08-10 17:25:16.
- Mode: PyInstaller `--onefile --windowed`.
- SHA-256: `CE1FAE8D148AC540DF5EAD7AEB746B7F93126E5DA0AB69E593ECA040784809A`.
- Release URL: `https://github.com/Luciansvon/app-rmv-bg-Lucian/releases/tag/v2.6.1`.
- Dependency build: VTracer 0.6.15, ONNX Runtime 1.28.0, PyInstaller 6.21.0.
- `Analysis-00.toc`, `PKG-00.toc`, dan `EXE-00.toc` mencatat `ffmpeg/ffmpeg.exe` serta `ffmpeg/ffprobe.exe`.
- Hasil runtime EXE belum diuji; warning log berisi 723 baris, termasuk unresolved `tbb12.dll` dari optional dependency numba.

## Aturan arsitektur yang dikunci

- Dua alat tidak boleh berjalan otomatis beriringan.
- Remove Background tidak boleh crop atau resize input.
- Upscale harus mengikuti skala yang dipilih dan menjaga alpha.
- Gambar input tidak boleh di-upload ke layanan eksternal tanpa persetujuan eksplisit.
- File output tidak boleh menimpa file lama secara diam-diam.
- Perubahan UI tidak boleh mengubah pipeline gambar tanpa regression check ukuran, mode warna, dan output PNG.
- Perubahan engine atau dependency harus dicatat di worklog dan diverifikasi pada environment Windows yang disebutkan.

## Hal yang belum menjadi bagian arsitektur

- server atau cloud processing;
- database aplikasi;
- login atau akun user;
- sinkronisasi antar-device;
- tracking watermark dan auto-detect;
- renderer SVG native Windows atau node editor;
- benchmark RAM lintas ukuran gambar dan mode AI;
- validasi visual otomatis untuk kualitas tepi alpha;
- runtime test dengan model LaMa, VTracer wheel, dan binary FFmpeg bundle.
