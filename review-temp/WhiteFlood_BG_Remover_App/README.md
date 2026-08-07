# WhiteFlood BG Remover v2.0

Aplikasi Windows untuk menghapus background putih / near-white menjadi transparan.
Sekarang dengan **UI modern dark theme** dan **algoritma yang lebih bersih**.

## Yang dijaga

- Tidak melakukan resize.
- Tidak melakukan crop.
- Lebar dan tinggi piksel output selalu sama dengan input.
- Output selalu PNG transparan.
- DPI / ICC profile / EXIF dipertahankan jika format sumber dan Pillow memungkinkan.
- Aplikasi memverifikasi ulang ukuran file setelah PNG disimpan.

Contoh:

Input  : 2048 x 2048 px
Output : 2048 x 2048 px

## Fitur Baru di v2.0

- **UI Modern Dark Theme** — tampilan gelap elegan dengan CustomTkinter
- **Preview Before/After** — lihat hasil sebelum menyimpan
- **Preview Ulang** — ubah setting, klik preview ulang tanpa pilih file lagi
- **Algoritma Lebih Bersih**:
  - Threshold berbasis luminance (lebih baik untuk background abu-abu)
  - Morphological dilation (menutup celah di tepi)
  - Edge smoothing / feathering (transisi halus di pinggir objek)
  - Fringe cleanup yang lebih efektif
- **Mode Agresif** — untuk background bergradasi / ada bayangan (shadow)
- **Progress Bar** visual saat batch processing
- **Thread-safe batch** — UI tidak freeze saat batch

## Jalankan tanpa membuat EXE

1. Install Python 3.11 atau lebih baru.
2. Extract folder ini.
3. Double-click `RUN_APP.bat`.
4. Pertama kali dijalankan, dependency akan otomatis di-install.

## Membuat .EXE Windows

Double-click:

`BUILD_EXE.bat`

Setelah selesai, file ada di:

`dist\WhiteFlood_BG_Remover.exe`

File EXE tersebut dapat dijalankan tanpa membuka Python secara manual.

## Cara pakai

### Satu gambar
1. Klik `Pilih Gambar`
2. Pilih file gambar
3. Hasil langsung muncul di preview (before / after)
4. Ubah setting jika perlu, lalu klik `Preview Ulang`
5. Kalau sudah puas, klik `Simpan Hasil`

### Banyak gambar (batch)
1. Tentukan `Folder Output Batch`
2. Klik `Batch 1 Folder`
3. Pilih folder sumber
4. Semua PNG/JPG/JPEG/WEBP/BMP di folder akan diproses
5. Progress bar menunjukkan kemajuan

## Setting

### White Threshold
Default: 220

Pixel dengan kecerahan (luminance) di atas nilai ini dianggap "putih".
- Naikkan jika background putih masih tertinggal.
- Turunkan jika bagian objek yang terang mulai ikut hilang.

### Fringe Cleanup
Default: 30

Mengurangi sisa garis putih tipis pada tepi objek.

### Edge Smoothing
Default: 2

Membuat transisi antara objek dan background lebih halus (Gaussian blur pada mask alpha). Nilai 0 = transisi tajam, nilai lebih tinggi = lebih smooth.

### Mode Agresif
Default: OFF

Aktifkan untuk background yang bergradasi (putih ke abu-abu) atau ada bayangan/shadow. Mode ini melakukan dua kali proses: pertama menghapus pixel putih, lalu memperluas ke pixel abu-abu yang berdekatan.

## Batasan algoritma

Algoritma menganggap pixel terang yang terhubung dengan tepi kanvas sebagai background.

Karena itu, objek putih yang menyentuh tepi gambar dan menyatu dengan background putih dapat ikut terhapus.

Ini bukan AI segmentation — tidak bisa memisahkan objek secara cerdas dari background berwarna selain putih/abu-abu.
