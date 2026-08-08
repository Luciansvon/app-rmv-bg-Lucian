# Implementation Plan - WhiteFlood UI, Preview, dan Distribusi

Status: Disetujui; implementasi selesai, verifikasi berjalan
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
- Tidak menjalankan GUI, download model, install dependency, atau build EXE tanpa persetujuan tambahan karena tindakan tersebut memakai environment/artefak user.
- Dokumentasi hanya akan mencatat bukti yang benar-benar dijalankan.

## Risiko dan batas

- Tanpa GUI smoke test, kelancaran slider dan fidelity visual belum boleh disebut terverifikasi penuh.
- Tanpa download model nyata, angka progress hanya bisa diuji melalui fake downloader/static smoke test; koneksi GitHub dan ukuran file aktual belum dinilai.
- Tanpa build EXE, kesiapan distribusi binary belum boleh disebut terverifikasi.
