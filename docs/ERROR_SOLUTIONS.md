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
