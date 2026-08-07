# WhiteFlood BG Remover v2.4.0 🎨

Aplikasi desktop Windows modern & cepat untuk menghapus background gambar produk furnitur & katalog menjadi **PNG Transparan** tanpa mengubah ukuran/piksel gambar asli (No Crop, No Resize).

---

## ✨ Fitur Baru di v2.4.0

- **Splash Screen Loading Awal**: Tampilan jendela loading cepat saat aplikasi dibuka, mencegah pengguna kebingungan menunggu layar kosong.
- **Visual Loading Spinner**: Animasi lingkaran muter-muter saat AI sedang menghapus background, memberi petunjuk jelas bahwa AI sedang bekerja.
- **Mode Berbasis Produk**:
  - `🪑 Furniture Quality` *(Default)* — Mesin `birefnet-massive` untuk ketajaman terbaik pada kayu, kaki meja, ukiran, & interior cabinet.
  - `⚡ Fast` — Mesin `birefnet-general` untuk proses cepat.
  - `👤 Person` — Mesin `birefnet-portrait` untuk foto manusia & pakaian.
  - `🔍 High Detail` — Mesin `birefnet-hrsod` untuk gambar resolusi tinggi & ukiran mikro.
  - `🌊 White Background` — Metode instan tanpa internet untuk background putih polos.
- **Sistem Penamaan Batch Otomatis**:
  - Pengguna memasukkan nama batch (misal `kursi-panjang`).
  - Output otomatis bernomor urut: `kursi-panjang-1.png`, `kursi-panjang-2.png`, dst.
- **Perlindungan File Tertimpa (Collision Safety)**:
  - Jika file `kursi-panjang-1.png` sudah ada di folder output, sistem otomatis melanjutkan nomor berikutnya agar file lama tidak terhapus/tertimpa.
- **Fitur Batal Batch (Cancel Batch)**: Tombol pembatalan aman yang menghentikan antrean tanpa merusak gambar yang sudah selesai.
- **Pengaturan Default Aman**: Edge Smoothing default = 0 (Original), Alpha Matting default = OFF (Irit RAM).
- **RAM Garbage Collection**: Membuang memori model lama dari RAM saat berganti mode agar RAM tidak menumpuk.

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

---

## 📦 Membuat File `.EXE` (Standalone)

Untuk membuat aplikasi `.exe` yang bisa dijalankan tanpa Python:
1. Klik 2x file `BUILD_EXE.bat` di folder `review-temp/WhiteFlood_BG_Remover_App`.
2. Setelah selesai, file `.exe` ada di folder `dist/WhiteFlood_BG_Remover.exe`.

---

## 📄 Lisensi & Kredit
Dibuat oleh Bima / Luciansvon. Didukung oleh `rembg`, `BiRefNet`, `CustomTkinter`, dan `Pillow`.
