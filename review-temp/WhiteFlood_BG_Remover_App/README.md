# WhiteFlood BG Remover & Upscaler v2.5.0

**Built by Bima Chakti © 2026**

Aplikasi Windows Desktop untuk menghapus background dan memperbesar foto produk furnitur.
Output selalu PNG transparan dengan dimensi presisi 100%.

---

## Fitur Utama

### ✂️ Remove Background (Hapus Background)
- **5 Mode AI**:
  - 🪑 Furniture Quality — Rekomendasi utama untuk foto produk furnitur, kayu, & katalog
  - ⚡ Fast — Proses cepat untuk gambar biasa
  - 👤 Person — Khusus foto orang, pakaian, & rambut
  - 🔍 High Detail — Khusus resolusi tinggi & ukiran halus
  - 🌊 White Background — Instan tanpa AI untuk background putih polos
- **Ketajaman Tepi**: Original, Soft (Pinggiran Halus), Alpha Matte (Deteksi Rambut)
- **Pengaturan Lanjutan**: White Threshold, Fringe Cleanup, Mode Agresif

### 🔍 Upscale (Perbesar Foto)
- Perbesaran **2x**, **4x**, atau **8x**
- Menggunakan backend **Upscayl NCNN Vulkan** untuk tile stitching yang konsisten
- PNG/RGBA diproses langsung oleh engine; kanal alpha tidak lagi dipisah lewat JPEG sementara
- Skala 2x/4x dikirim langsung tanpa resize perantara
- Skala 8x memakai 4x AI lalu resize Lanczos 2x

### Fitur Umum
- **Preview Before/After** — Split-slider interaktif gaya Upscayl dengan cache bitmap agar drag lebih ringan
- **Batch Processing** — Proses satu folder sekaligus dengan penamaan otomatis
- **Metadata Preserved** — DPI / ICC Profile / EXIF dipertahankan
- **RAM Monitor** — Tampilan penggunaan memori real-time
- **Progress Model** — Persentase download model AI tampil di dalam aplikasi
- **Dark Theme** — UI modern gelap dengan CustomTkinter

## Aturan Dimensi

Dimensi output dijaga ketat:

| Tool | Input | Output |
|---|---|---|
| Remove BG | 2048×2048 px | 2048×2048 px (sama persis) |
| Upscale 2x | 2048×2048 px | 4096×4096 px |
| Upscale 4x | 2048×2048 px | 8192×8192 px |
| Upscale 8x | 2048×2048 px | 16384×16384 px |

Tidak ada resize atau crop yang tidak diinginkan.

## Jalankan dari Source Tanpa Membuat EXE

1. Install **Python 3.11** atau lebih baru
2. Extract folder ini
3. Install dependency satu kali: `python -m pip install -r requirements.txt`
4. Double-click `RUN_APP.vbs` agar aplikasi jalan tanpa console

`RUN_APP.bat` hanya meneruskan ke `RUN_APP.vbs`. Jika folder `dist` memiliki EXE hasil build, launcher akan memilih EXE tersebut lebih dulu.

## Membuat .EXE Windows

Double-click: `BUILD_EXE.bat`

Setelah selesai, file ada di: `dist\WhiteFlood_BG_Remover.exe`

> File EXE besar (~300-500 MB) karena berisi AI model dan semua library. Ini normal, bukan virus.

## Cara Pakai

### Satu Gambar — Remove BG
1. Pilih alat **✂️ Hapus BG**
2. Pilih mode AI yang sesuai
3. Klik **Pilih Gambar**
4. Hasil langsung muncul di preview (split before/after)
5. Ubah setting jika perlu, lalu klik **Proses Ulang**
6. Klik **Simpan Hasil**

### Satu Gambar — Upscale
1. Pilih alat **🔍 Upscale**
2. Klik **Pilih Gambar** — gambar ditampilkan tanpa auto-proses
3. Pilih skala **2x**, **4x**, atau **8x**
4. Klik **Proses Upscale**
5. Klik **Simpan Hasil**

### Batch (Banyak Gambar)
1. Pilih alat yang diinginkan (Hapus BG atau Upscale)
2. Isi **Nama Batch** (contoh: kursi-panjang)
3. Pilih **Folder Output**
4. Klik **Mulai Batch**, lalu pilih folder sumber gambar
5. Semua PNG/JPG/JPEG/WEBP/BMP di folder akan diproses
6. Hasil disimpan sebagai: `kursi-panjang-1.png`, `kursi-panjang-2.png`, dst.

## Dependencies

```
Pillow>=10.0
numpy>=1.24
customtkinter>=5.2
rembg[cpu]>=2.0
psutil>=5.9
```

## Batasan

- Mode White Background hanya bekerja pada background putih/abu-abu polos
- Model AI pertama kali perlu diunduh (~150-250 MB per model)
- Upscale 8x pada gambar besar membutuhkan RAM dan ruang disk yang lebih besar

---

**© 2026 Bima Chakti**
