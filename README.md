# WhiteFlood BG Remover & Upscaler v2.5.0

**Built by Bima Chakti © 2026 Bima Chakti**

Aplikasi desktop Windows untuk fotografi produk furnitur dan katalog kantor (high-resolution furniture product photography).

---

## 🌟 Fitur Utama (v2.5.0)

1. **✂️ Remove Background (Hapus Background)**
   - Menggunakan AI `birefnet-massive` (Mode *Furniture Quality*).
   - **Non-Negotiable Rules**: Tanpa crop, tanpa resize, 100% dimensi piksel asli dipertahankan.
   - Masker Alpha Anti-Aliased halus (tanpa gerigi / tajem-tajem).

2. **🔍 Upscale Image (Pembesar Gambar 2x & 4x)**
   - Alat terpisah independen (tidak pernah berjalan otomatis beriringan).
   - **Alpha-Safe Pipeline**: Kanal transparansi (Alpha) diperbesar dengan algoritma presisi Lanczos, menjaga kaki meja tipis & ukiran 100% utuh tanpa distorsi.

3. **🎨 Antarmuka Upscayl-Style & Sidebar Ramping**
   - Layar preview jumbo mengisi 80% layar dengan **Interactive Split-Slider (Geser Kanan-Kiri)**.
   - Sidebar samping kiri ramping (~290px) terinspirasi dari sidebar ChatGPT desktop.
   - Kredit pengembang visual: `Built by Bima Chakti © 2026 Bima Chakti`.

4. **⚡ Manajemen & Bebas RAM Spike 12GB**
   - Konfigurasi `ONNX SessionOptions` (`enable_cpu_mem_arena = False`) mengembalikan RAM langsung ke Windows.
   - Pelepasan memori safe-release (`del old_session` & `gc.collect()`) saat berpindah alat.
   - Pemakaian RAM terpantau stabil di kisaran **1.2 GB - 1.8 GB**.

5. **📁 Penamaan Batch & Anti-Tertimpa**
   - Nama batch kustom (contoh `kursi-panjang`).
   - Penomoran otomatis `kursi-panjang-1.png`, `kursi-panjang-2.png`.
   - Aman dari penimpaan file lama (*collision safety*).

---

## 🚀 Cara Menjalankan Aplikasi

Double click file `RUN_APP.bat` di folder aplikasi.
