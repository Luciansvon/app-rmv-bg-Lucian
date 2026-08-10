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
- unittest kontrak service sudah ditambahkan dan lulus;
- GUI smoke test, VTracer conversion runtime, model LaMa, dan binary FFmpeg belum dijalankan; build EXE sudah selesai.

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
- Adapter `_ModelDownloadProgress` meneruskan byte download `pooch` ke progress bar UI sehingga persentase model terlihat di aplikasi.

### Single-image workflow

1. User memilih alat lalu memilih file.
2. `PIL.Image.open` membaca gambar dan mempertahankan informasi alpha jika tersedia.
3. Gambar asli langsung ditampilkan sebelum proses berat dimulai; memilih file tidak memproses otomatis.
4. User menekan aksi proses yang sesuai dengan alat aktif.
5. Worker thread mengerjakan proses berat agar UI tetap merespons.
6. Callback `after` Tkinter mengembalikan status proses dan progress download/model/frame ke UI.
7. Hasil dikembalikan ke UI; user memilih Export/Simpan, lalu output divalidasi.

### Remove Background pipeline

- Mode AI memakai `ai_remove_bg`, session lazy-load, dan model `birefnet-*` melalui `rembg`.
- Mode White Background memakai `flood_remove_bg` untuk background putih/abu-abu polos tanpa model AI.
- `refine_alpha_mask` menangani penghalusan atau erosi alpha sesuai pengaturan.
- Pipeline menetapkan ukuran yang diharapkan sama dengan ukuran input.
- Hasil dikonversi ke RGBA dan disimpan sebagai PNG.

### Upscale pipeline

- `upscale_image_alpha_safe` membuat folder temporary untuk input dan output backend.
- Backend eksternal dipanggil melalui `subprocess.Popen`.
- Skala 2x atau 4x dikirim langsung ke backend; skala 8x memakai pass AI 4x lalu resize Lanczos 2x.
- Gambar dengan alpha dikembalikan sebagai RGBA; gambar tanpa alpha tetap dapat dikembalikan sebagai RGB.
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
- Progress ditampilkan sebagai status/spinner karena binding tidak menyediakan persentase yang bisa dipercaya.
- Preview tidak merender SVG native; UI hanya menampilkan status validasi dan informasi output.

### Remove Watermark Image

- `MaskCanvas` menyimpan mask L pada ukuran pixel source, sementara canvas hanya menampilkan preview letterbox + zoom.
- Brush, rectangle, eraser, clear, undo/redo, dan multi-stroke tersedia tanpa tracking/auto-detect.
- `LamaInpaintService` melakukan ROI context dan tile 512px overlap; komposisi hanya mengganti area mask.
- Alpha input dipasang kembali ke hasil dan ukuran output harus sama persis.

### Remove Watermark Static Video

- `probe_video` memakai ffprobe bundle dan mengembalikan ukuran visual setelah autorotate, FPS nominal/average, durasi, audio, rotasi, dan VFR warning.
- `VideoProcessor` membaca raw BGR frame satu per satu dari FFmpeg, memproses dengan mask yang sama, lalu menulis frame ke encoder MP4.
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
- Folder `assets/` dan `ffmpeg/` sudah disiapkan sebagai resource path development/`_MEIPASS`; model LaMa dan binary FFmpeg belum disertakan.
- Script build bersifat destruktif terhadap `build/`, `dist/`, dan file `.spec`; target harus diperiksa sebelum dijalankan.

Build terakhir yang dicek:

- Command: `BUILD_EXE.bat`.
- Output: `dist/WhiteFlood_BG_Remover.exe`, 201,367,265 bytes, dibuat 2026-08-10 09:28:30.
- Mode: PyInstaller `--onefile --windowed`.
- SHA-256: `8EC9D22A6A638C23D971B6F1CEFB2137FC2C9D5F867D41D1455CBD92E71401F4`.
- Dependency build: VTracer 0.6.15, ONNX Runtime 1.28.0, PyInstaller 6.21.0.
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
