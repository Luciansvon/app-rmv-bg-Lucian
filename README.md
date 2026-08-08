# WhiteFlood BG Remover & Upscaler v2.5.0

**Built by Bima Chakti © 2026 Bima Chakti**

Aplikasi desktop Windows untuk fotografi produk furnitur dan katalog kantor (high-resolution furniture product photography).

---

## 🌟 Fitur Utama (v2.5.0)

1. **✂️ Remove Background (Hapus Background)**
   - Menggunakan AI `birefnet-massive` (Mode *Furniture Quality*).
   - **Non-Negotiable Rules**: Tanpa crop, tanpa resize, 100% dimensi piksel asli dipertahankan.
   - Masker Alpha Anti-Aliased halus (tanpa gerigi / tajem-tajem).

2. **🔍 Upscale Image (Pembesar Gambar 2x, 4x & 8x)**
   - Alat terpisah independen (tidak pernah berjalan otomatis beriringan).
   - **Upscayl NCNN Pipeline**: Backend resmi Upscayl menangani tile stitching dan kanal transparansi PNG secara langsung.
   - Skala 2x/4x dikirim langsung ke engine tanpa resize perantara yang menurunkan detail.
   - Skala 8x memakai 4x AI lalu resize Lanczos 2x agar output besar tetap stabil.

3. **🎨 Antarmuka Upscayl-Style & Sidebar Ramping**
   - Layar preview jumbo dengan **Interactive Split-Slider (Geser Kanan-Kiri)** yang memakai cache bitmap agar drag tidak mengulang resize gambar sumber.
   - Sidebar kiri sekitar 304px berisi alat aktif, kontrol, file, batch, dan aksi utama dengan hierarchy yang lebih jelas.
   - Status bar di dalam aplikasi menampilkan fase proses dan persentase download model.
   - Kredit pengembang visual: `Built by Bima Chakti © 2026 Bima Chakti`.

4. **⚡ Manajemen RAM dan engine berat**
   - Konfigurasi `ONNX SessionOptions` (`enable_cpu_mem_arena = False`) mengembalikan RAM langsung ke Windows.
   - Pelepasan memori safe-release (`del old_session` & `gc.collect()`) saat berpindah alat.
   - UI menampilkan RSS proses saat berjalan; kebutuhan aktual bergantung pada model, resolusi, dan hardware komputer.

5. **📁 Penamaan Batch & Anti-Tertimpa**
   - Nama batch kustom (contoh `kursi-panjang`).
   - Penomoran otomatis `kursi-panjang-1.png`, `kursi-panjang-2.png`.
   - Aman dari penimpaan file lama (*collision safety*).

---

## 🚀 Cara Menjalankan Aplikasi

Untuk source Python, install dependency sekali dengan `python -m pip install -r requirements.txt`, lalu double-click `RUN_APP.vbs`. Launcher ini memakai `pythonw.exe` agar console tidak muncul. `RUN_APP.bat` tetap tersedia sebagai entry point singkat. Untuk dibagikan ke komputer kantor, gunakan `dist\WhiteFlood_BG_Remover.exe` hasil build `--windowed`.

---

## Dokumentasi Repo

- [`AGENTS.md`](AGENTS.md): aturan kerja dan batas perubahan.
- [`user.md`](user.md): aturan produk WhiteFlood.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): arsitektur source aktif dan batas sistem.
- [`docs/ERROR_SOLUTIONS.md`](docs/ERROR_SOLUTIONS.md): error terverifikasi, root cause, dan bukti fix.
- [`docs/WORKLOG.md`](docs/WORKLOG.md): riwayat pekerjaan, keputusan, dan verifikasi.
