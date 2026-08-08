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
