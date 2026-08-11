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

- Build release PyInstaller dengan konfigurasi setara `BUILD_EXE.bat` lulus dalam sekitar 3 menit 48 detik; output dibuat di staging temporary karena EXE pada `dist/` sedang dipakai.
- EXE release: `WhiteFlood_BG_Remover.exe`, 295.694.770 bytes, dibuat 2026-08-10 12:06:54.
- SHA-256: `C97C1E3C152FB9F9F0B9A74BBDB0B14E3885F3EFFBDF25784554A7319E231B85`.

## 2026-08-10 - Release v2.6.0

Status: release publik dan asset EXE selesai; link download README sudah diarahkan ke release baru.

- Release: https://github.com/Luciansvon/app-rmv-bg-Lucian/releases/tag/v2.6.0
- Asset: `WhiteFlood_BG_Remover.exe`, digest GitHub cocok dengan SHA-256 build.
- GUI smoke test khusus selector speed tetap tercatat sebagai pemeriksaan lanjutan.

## 2026-08-10 - Plan Vectorize logo dengan pre-clean khusus preset Logo

Status: Menunggu persetujuan Bima; belum ada coding Vectorize.
Mode: REDESIGN lalu HANDOFF
Domain: BRAND_LOGO
Specificity: PROBLEM
Metode: Audit lalu First Principles

### Fakta yang menjadi acuan

- Preset `Logo` saat ini langsung mengirim raster asli ke VTracer `0.6.15` dalam mode warna.
- Dari laporan Bima, logo memiliki anti-alias, gradient/shading emas, background gelap, dan detail sapuan tipis.
- Gejala output: bentuk melebar/belepotan dan detail kecil berubah menjadi path yang tidak diinginkan.
- VTracer tidak mengunduh model; isu minimize pada download model tidak berada di jalur Vectorize.

### Problem statement

Untuk user yang mengubah logo raster menjadi SVG, WhiteFlood harus menangkap silhouette, figure-ground, dan detail utama logo tanpa menyalin noise warna/tepi dari raster, dengan tetap menyimpan input asli dan bekerja lokal.

### Scope yang diusulkan

1. Tambahkan pre-clean sementara yang hanya aktif untuk preset `Logo`:
   - normalisasi background/alpha;
   - flatten warna logo menjadi jumlah warna terbatas;
   - threshold dan penghapusan speckle kecil;
   - pertahankan sparkle, ikon utama, dan sapuan bawah berdasarkan ukuran relatifnya.
2. Kirim hasil pre-clean dari temporary directory ke VTracer; file input user tidak disentuh.
3. Tuning preset `Logo` berdasarkan fixture logo nyata. Preset `Illustration`, `Line Art`, dan `Detailed` tetap memakai jalur sekarang sampai ada bukti regresi.
4. Pertahankan validasi root SVG, elemen grafis, atomic save, collision safety, batch, dan status bahwa preview SVG bukan editor node.
5. Tambahkan opsi fallback yang jelas: jika input masih gradient/bertekstur dan pre-clean otomatis tidak aman, user diberi hasil trace dengan warning atau diarahkan ke redraw manual; jangan mengklaim auto-trace sebagai redraw sempurna.

### Yang tidak dikerjakan dulu

- Tidak membuat editor node native.
- Tidak melakukan redraw geometris otomatis yang mengarang bentuk logo.
- Tidak menambahkan upload cloud atau model AI eksternal.
- Tidak menerapkan pre-clean Logo ke foto/ilustrasi umum.
- Tidak menambah SVGO/dependency baru sebelum ukuran masalah dan output baseline diukur.

### Acceptance criteria

- Input asli tetap utuh; pre-clean hanya berupa file temporary yang dibersihkan setelah proses.
- Fixture logo menghasilkan SVG valid, tidak kosong, dan bisa disimpan atomic.
- Pada inspeksi 100%, 400%, dan ukuran kecil, silhouette utama tidak berubah menjadi blob; speckle/path liar berkurang dibanding baseline preset Logo.
- Detail tipis yang memang disetujui tetap terbaca atau diberi warning jika tidak bisa dipertahankan aman.
- Preset non-Logo dan workflow batch tidak berubah tanpa bukti regresi.
- Test otomatis mencakup warna/alpha, cleanup temporary, validasi SVG, dan regression baseline; VTracer runtime serta GUI dicatat terpisah dari static test.

### Risiko dan keputusan yang masih terbuka

- Threshold terlalu agresif dapat menghapus garis tipis; threshold terlalu longgar akan mengulang masalah belepotan.
- Flatten satu warna bisa merusak logo yang memang membutuhkan beberapa layer warna; jumlah warna harus ditentukan dari fixture, bukan angka tebakan.
- Auto-trace tidak dapat mengetahui bentuk geometris yang dimaksud desainer jika raster terlalu rusak; redraw manual tetap fallback paling bersih.

### Gate sebelum coding

- Siapkan atau konfirmasi satu fixture logo asli dan baseline SVG saat ini.
- Ukur baseline: mode warna, jumlah elemen/path, ukuran SVG, dan screenshot pada tiga skala.
- Setelah plan ini disetujui, implementasikan patch kecil di `features/vectorize/` lalu update error/worklog dan jalankan static test, VTracer runtime, serta GUI smoke test yang disetujui.

## 2026-08-10 - Fix progress Remove Background berhenti di 70%

Status: Source patch dan static/unit verification selesai; GUI dengan model nyata masih pending.

### Fakta dan root cause

- Screenshot menunjukkan progress Remove Background melompat ke 70% lalu tidak berubah.
- `ai_remove_bg()` mengirim angka 70 tepat sebelum `rembg_remove()` menjalankan inferensi AI.
- `rembg_remove()` tidak menyediakan callback progress kontinu, sehingga angka 70 tidak boleh ditampilkan sebagai persentase determinate.

### Scope patch

- Ganti tahap inferensi AI menjadi progress indeterminate dengan pesan yang jelas.
- Kembalikan progress bar ke mode determinate saat event angka berikutnya diterima.
- Pertahankan progress model download, Upscale, Watermark, Vectorize, batch, cancel, dan output image tanpa perubahan perilaku.
- Tambahkan regression test untuk kontrak urutan event sebelum inferensi.

### Acceptance criteria

- UI tidak lagi mengklaim `70%` saat inferensi AI belum selesai.
- Progress bar tetap bergerak secara visual dalam mode indeterminate dan status menjelaskan bahwa AI lokal sedang menghitung mask.
- Setelah hasil tersedia, progress kembali ke 100% dan workflow selesai seperti sebelumnya.
- Syntax check, unit test, diff check, dan dokumentasi bugfix lulus; GUI/model runtime dicatat terpisah jika belum dijalankan.

## 2026-08-10 - Audit lanjutan, bugfix, dan release v2.6.1

Status: selesai. Audit menemukan bug konkret dan patch dikerjakan dalam scope
source aktif, regression test, dokumentasi, build, push, dan release v2.6.1.

### Temuan yang terbukti

- `Mode Agresif` diteruskan ke `flood_remove_bg()` tetapi tidak pernah dipakai,
  sehingga toggle tidak mengubah hasil.
- `adv_section` selalu di-pack dan jalur non-White Background tidak pernah
  memanggil `pack_forget()`, sehingga kontrol White Threshold/Fringe/Agresif
  tampil pada mode AI meskipun tidak berlaku.
- Jika pemilihan file baru gagal dibuka, state preview dan tombol hasil lama
  tidak dibersihkan secara konsisten.
- Jalur input transparan Upscale dikirim sebagai RGBA langsung ke backend;
  kontrak produk mengharuskan RGB dan alpha diproses terpisah lalu digabung.
- Dialog Remove Background menyebut ukuran model `150-250 MB`, sedangkan
  dokumentasi project mencatat sekitar `972.67 MB` per model BiRefNet.

### Scope patch

- Aktifkan Mode Agresif sebagai threshold near-white yang lebih longgar,
  dengan regression test dan penjelasan trade-off.
- Sinkronkan visibility advanced settings dengan mode White Background sejak
  startup dan setiap pergantian mode.
- Bersihkan media state sebelum pemuatan file baru dan saat load gagal agar
  preview/output lama tidak terlihat sebagai hasil file baru.
- Pisahkan RGB dan alpha pada Upscale transparan; gunakan padding warna dekat
  tepi alpha, AI hanya pada RGB, Lanczos deterministik untuk alpha, lalu merge
  RGBA dengan ukuran final yang tepat.
- Hilangkan angka ukuran model Remove Background yang tidak sesuai dari dialog.
- Update `docs/ERROR_SOLUTIONS.md`, `docs/WORKLOG.md`, dan arsitektur bila
  kontrak pipeline berubah.

### Gate verifikasi

- Syntax check source aktif.
- Semua unittest termasuk regression untuk agresif, alpha split/merge, dan mask
  interaction lock; state reset serta visibility contract diverifikasi lewat
  inspeksi source karena membutuhkan GUI untuk pembuktian runtime.
- `git diff --check` dengan catatan jika ada warning pre-existing pada backup.
- Build EXE dan pemeriksaan ukuran, timestamp, serta SHA-256 artifact.
- Runtime GUI, model nyata, dan GPU Vulkan tetap dicatat terpisah bila belum
  dijalankan.

### Bukti gate sebelum publish

- Syntax source aktif lulus.
- `python -m unittest discover -s tests -v` lulus: 21 test.
- Build `python build_exe.py` exit code 0; artifact 294,711,783 bytes,
  timestamp 2026-08-10 17:25:16, SHA-256
  `CE1FAE8D148AC540DF5EAD7AEB746B7F93126E5DA0AB69E593ECA040784809A`.
- GUI EXE, model nyata, dan GPU Vulkan belum dijalankan.

### Handoff final

- Commit: `53b004722a02c581a57df577ee45f9066324730c`.
- Branch: `codex/fix-remove-bg-progress` sudah dipush ke origin.
- Release: `https://github.com/Luciansvon/app-rmv-bg-Lucian/releases/tag/v2.6.1`.
- Asset GitHub berstatus `uploaded`; digest cocok dengan SHA-256 lokal.

## 2026-08-11 - Fix unduhan model mentok 15% dan release v2.6.2

Status: Selesai. Implementasi, test, smoke download, build, smoke start EXE,
commit, push, dan release publik v2.6.2 lulus.

### Fakta dan root cause yang sudah terbukti

- Worker memaksa progress visual ke `15%` sebelum koneksi atau unduhan model
  dimulai. Angka ini bukan persentase byte unduhan.
- Saat koneksi ke host model belum menghasilkan respons/data, UI tetap
  menampilkan `15%`, sehingga terlihat seperti unduhan macet dan tidak memberi
  tahu apakah aplikasi sedang menghubungi server atau benar-benar menerima data.
- Model BiRefNet diambil oleh `rembg 2.0.78` dari GitHub Releases melalui
  `pooch 1.9.0`. Pooch baru dapat mengisi total byte setelah respons HTTP
  diterima; timeout bawaannya 30 detik.
- Runtime download internet pada EXE v2.6.1 sebelumnya memang belum pernah
  diverifikasi dan tercatat sebagai gate pending di worklog.

### Scope patch

1. Hapus angka dummy `15%` dari awal worker Remove Background.
2. Tampilkan fase indeterminate yang jujur saat aplikasi menyiapkan model dan
   menghubungkan ke server; progress determinate baru muncul setelah total byte
   unduhan tersedia.
3. Pertahankan adapter custom progress Pooch, tetapi tambahkan event status
   yang membedakan menghubungkan server, mengunduh byte, verifikasi file, dan
   memuat model lokal.
4. Perjelas error koneksi khusus lingkungan kantor: internet putus, GitHub
   diblokir firewall/proxy, timeout, serta lokasi model `%USERPROFILE%\\.u2net`.
5. Tambahkan regression test agar angka 15% palsu tidak kembali dan urutan event
   download dapat diuji tanpa mengunduh model 972 MB.
6. Update `docs/ERROR_SOLUTIONS.md`, `docs/WORKLOG.md`, dan README bila teks
   troubleshooting pengguna terdampak.

### Acceptance criteria

- Sebelum byte pertama diterima, UI menampilkan status bergerak tanpa mengklaim
  persentase tertentu.
- Setelah header/byte tersedia, UI menampilkan persen dan ukuran
  terunduh/total dari downloader asli.
- Koneksi gagal tidak diam selamanya di 15%; pengguna mendapat pesan penyebab
  yang masuk akal dan langkah lanjut.
- Model valid tetap disimpan di `%USERPROFILE%\\.u2net` dan pemrosesan gambar
  tetap lokal setelah model tersedia.
- Syntax check, semua unittest, diff check, build EXE, pemeriksaan artifact dan
  SHA-256 lulus sebelum release.
- Runtime download nyata diuji memakai file kecil melalui downloader yang sama.
  Download penuh BiRefNet/GUI di komputer kantor tetap dicatat sebagai bukti
  terpisah bila tidak bisa dijalankan dari environment ini.

### Release

- Versi patch yang diusulkan: `v2.6.2`.
- Setelah gate lulus: update versi/link dokumentasi, commit, push branch aktif,
  buat GitHub Release `v2.6.2`, upload EXE, lalu cocokkan ukuran dan SHA-256
  asset GitHub dengan artifact lokal.
- Release tidak akan di-merge ke branch lain kecuali diminta.

## 2026-08-11 - Download model otomatis untuk jaringan kantor strict

Status: Disetujui dan diimplementasikan; seluruh gate lokal v2.6.3 lulus,
publikasi GitHub berjalan.
Mode: AUDIT lalu REDESIGN
Domain: UI_UX dengan batas teknis download Windows
Specificity: PROBLEM
Metode: Audit lalu First Principles

### Fakta yang sudah terbukti

- Pada PC kantor, release v2.6.2 tetap berada di `0%`; berarti downloader belum
  melaporkan satu byte model yang diterima aplikasi.
- File yang sama dapat diunduh manual melalui browser pada PC tersebut.
- Downloader Remove Background saat ini memakai Pooch `1.9.0`, yang memakai
  Requests untuk HTTPS.
- Microsoft mendokumentasikan bahwa aplikasi Python dapat gagal pada jaringan
  dengan TLS inspection karena tidak memakai certificate store Windows secara
  default.
- Truststore menyediakan certificate store native Windows melalui CryptoAPI.
- BITS memakai proxy Windows/SystemDefault, mendukung proxy authentication,
  progress, serta transfer background pada sesi user Windows yang sedang login.
- Model manual sebelumnya tidak terbaca bila nama dan lokasi akhirnya tidak
  persis seperti yang dicari rembg di `%USERPROFILE%\\.u2net`.

### Inferensi yang perlu dibuktikan di PC kantor

- Penyebab paling mungkin adalah sertifikat TLS inspection atau konfigurasi
  proxy Windows/PAC yang dipercaya browser tetapi tidak dipakai Requests dalam
  EXE. Keyakinan: sedang-tinggi, karena browser berhasil sementara aplikasi
  belum menerima byte.
- Kebijakan kantor masih dapat memblokir GitHub untuk semua program selain
  browser. Karena itu tidak ada patch yang bisa menjamin auto-download tanpa
  fallback bila server memang diblokir oleh admin.

### Problem statement

Untuk user WhiteFlood pada PC kantor, pemasangan model harus selesai dari dalam
aplikasi dengan mengikuti konfigurasi keamanan Windows, menampilkan status yang
jujur, dan tidak meminta user memakai CMD, memindahkan folder, atau mengganti
nama file secara manual.

### Scope yang diusulkan

1. Aktifkan Truststore sedini mungkin pada startup EXE agar Pooch/Requests
   memverifikasi HTTPS memakai certificate store Windows, tanpa mematikan
   verifikasi SSL.
2. Pertahankan downloader Pooch sebagai jalur utama. Jika gagal sebelum model
   tersedia, ambil URL, nama file, dan hash langsung dari pemanggilan rembg lalu
   pindah otomatis ke BITS dengan proxy `SystemDefault`.
3. BITS mengirim byte terunduh/total ke progress UI, menulis ke file `.part`,
   memverifikasi hash resmi rembg, lalu melakukan atomic replace ke nama model
   persis di `%USERPROFILE%\\.u2net`.
4. Tambahkan satu aksi cadangan `Pasang Model dari File` di halaman Remove
   Background. File yang dipilih diverifikasi di worker, lalu disalin dan
   dinamai otomatis; user tidak perlu membuka terminal atau folder cache.
5. Error akhir membedakan kegagalan HTTPS Python, BITS/policy Windows, hash
   salah, dan server diblokir. Jangan menyarankan `verify=False` atau mematikan
   firewall.
6. Perbarui dependency/build, README, `docs/ERROR_SOLUTIONS.md`, dan
   `docs/WORKLOG.md`; naikkan versi patch menjadi v2.6.3 setelah seluruh gate
   release lulus.

### Yang tidak dikerjakan

- Tidak membundel model 927.61 MiB ke dalam PyInstaller `--onefile`, karena
  model akan memperbesar EXE dan berisiko diekstrak ulang setiap aplikasi dibuka.
- Tidak meng-upload foto atau model ke cloud selain URL model resmi yang sudah
  dipakai rembg.
- Tidak menonaktifkan SSL, firewall, antivirus, proxy, atau kebijakan kantor.
- Tidak mengunduh model BiRefNet penuh saat pengujian lokal tanpa persetujuan.

### Acceptance criteria

- Jalur normal memakai sertifikat Windows dan tetap memverifikasi HTTPS.
- Jika Requests gagal, UI otomatis berpindah ke `Mencoba jalur Windows kantor`
  tanpa kembali diam di `0%`.
- Progress BITS memakai byte nyata; status indeterminate dipakai bila total
  belum diketahui.
- Hanya file dengan hash yang sesuai yang dapat menjadi
  `birefnet-*.onnx`; file rusak tidak menimpa model valid.
- File manual dengan nama apa pun dapat dipilih, diverifikasi, dan dipasang ke
  nama/lokasi yang benar tanpa CMD atau PowerShell.
- Model yang selesai dipasang langsung dipakai pada proses yang sama; user tidak
  perlu memindahkan file atau restart aplikasi.
- Syntax check, seluruh unittest, fallback test dengan fixture kecil, hash dan
  atomic-install regression, diff check, build EXE, smoke-start EXE, ukuran,
  timestamp, dan SHA-256 artifact lulus.
- Download model penuh dan pembuktian proxy tetap diberi label pending sampai
  release diuji pada PC kantor yang mengalami masalah.

### Release

- Setelah plan disetujui: implementasi patch kecil, test, build v2.6.3, commit,
  push branch aktif, buat release GitHub, upload EXE, lalu cocokkan ukuran dan
  SHA-256 asset GitHub dengan artifact lokal.

### Hasil implementasi aktual

- Truststore Windows, fallback BITS/SystemDefault proxy, cache model kanonis,
  instalasi model dari file, verifikasi hash, dan atomic replace diterapkan.
- Progress Remove Background, model, Watermark, Upscale, dan batch dipetakan
  per fase serta dijaga agar tidak mundur.
- Audit tambahan menemukan dan memperbaiki TclError saat berpindah dari White
  Background kembali ke mode AI.
- 35 unittest, syntax check, `git diff --check`, BITS fixture, GUI construction,
  BiRefNet-Massive nyata, Real-ESRGAN nyata, VTracer nyata, LaMa Image, dan
  LaMa Video lulus.
- Build staging PyInstaller UI-final lulus: 294.769.390 byte, SHA-256
  `A556A60F5A819224C0247CE92396F4F9135B853696FBCA95BCBE5174FACE3E6D`.
- Smoke start EXE 15 detik lulus. Jaringan/proxy PC kantor tetap menjadi gate
  eksternal karena tidak tersedia pada laptop build.
