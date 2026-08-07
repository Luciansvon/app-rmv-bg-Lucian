# WhiteFlood BG Remover v2.3 🎨

Aplikasi desktop Windows modern & cepat untuk menghapus background gambar menjadi **PNG Transparan** tanpa merubah ukuran/piksel gambar asli (No Crop, No Resize).

Dipersenjatai dengan 2 mode powerful:
1. **🤖 Mode AI State-of-the-Art (BiRefNet, ISNet, U2Net, Bria)** — Hapus background warna apa saja dengan kecerdasan buatan kelas atas.
2. **🌊 Mode WhiteFlood (Flood-Fill)** — Khusus background putih / abu-abu muda, bekerja secara kilat tanpa internet.

---

## ✨ Fitur Utama

- **Model AI Terbaru 2026**:
  - `birefnet-massive` ⭐ **(State-of-the-Art / Terbaik)** — Detail paling halus dan rapi.
  - `birefnet-portrait` — Khusus foto orang / rambut.
  - `birefnet-hrsod` — Khusus gambar resolusi tinggi.
  - `birefnet-general` — Stabil untuk berbagai objek.
  - `isnet-general-use` — Ringan & detail.
  - `bria-rmbg` & `u2net` — Pilihan alternatif.
- **Pop-up Konfirmasi Download AI**: Mengonfirmasi sebelum mengunduh model AI baru (ukuran ±150-250 MB).
- **Alpha Matting & Edge Smoothing**: Pinggiran objek halus tanpa gerigi atau sisa garis putih.
- **Tanpa Crop / Resize**: Ukuran piksel output **100% sama** dengan input.
- **Batch Processing**: Hapus background 1 folder sekaligus dalam hitungan detik.
- **UI Dark Mode Modern**: Dibuat dengan CustomTkinter yang responsif dan nyaman di mata.

---

## 🚀 Cara Menjalankan Aplikasi

1. **Persyaratan**: Pastikan sudah menginstall [Python 3.11+](https://www.python.org/downloads/) (centang *"Add Python to PATH"* saat instalasi).
2. Download / Clone repository ini:
   ```bash
   git clone https://github.com/Luciansvon/app-rmv-bg-Lucian.git
   ```
3. Buka folder `review-temp/WhiteFlood_BG_Remover_App` dan klik 2x file:
   ```text
   RUN_APP.bat
   ```
   *(Semua library yang dibutuhkan akan terinstall secara otomatis pada saat pertama kali dijalankan).*

---

## 📦 Membuat File `.EXE` (Standalone)

Jika ingin membuat aplikasi `.exe` mandiri yang bisa dijalankan tanpa Python:
1. Klik 2x file `BUILD_EXE.bat` di folder `review-temp/WhiteFlood_BG_Remover_App`.
2. Tunggu proses build selesai.
3. File `.exe` siap pakai ada di folder `dist/WhiteFlood_BG_Remover.exe`.

---

## 📖 Cara Penggunaan

### 1. Hapus Background 1 Gambar
1. Klik **Pilih Gambar**.
2. Pilih mode: **AI** (untuk semua background) atau **WhiteFlood** (untuk background putih).
3. Jika menggunakan AI, pilih model (Rekomendasi: `birefnet-massive`).
4. Klik **Simpan Hasil** untuk menyimpan file `.png` transparan.

### 2. Hapus Background 1 Folder (Batch)
1. Tentukan **Folder Output Batch**.
2. Klik **Batch 1 Folder**.
3. Pilih folder asal berisi gambar-gambar yang ingin diproses.

---

## 📄 Lisensi & Kredit
Dibuat oleh Bima / Luciansvon. Didukung oleh `rembg`, `BiRefNet`, `CustomTkinter`, dan `Pillow`.
