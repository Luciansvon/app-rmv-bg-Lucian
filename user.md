# User Notes & Product Rules (Bima / WhiteFlood v2.5.0)

## Profil & Aturan Komunikasi
- Bima (User) adalah orang yang belum/tidak memahami fundamental pemrograman/coding.
- Komunikasi wajib menggunakan **Bahasa Indonesia** sepenuhnya, ramah, jujur, dan mudah dipahami tanpa jargon teknis berlebihan.
- **Kredit Pengembang Visual**: Aplikasi WhiteFlood selalu menampilkan identitas:
  > **Built by Bima Chakti**
  > **© 2026 Bima Chakti**
  *(HANYA pada antarmuka UI aplikasi — HARAM hukumnya menempelkan watermark pada file gambar output).*
- **Jangan pernah auto-approve plan**. Selalu buat `implementation_plan.md` dan tunggu persetujuan eksplisit dari Bima.
- **Jangan ubah kode sebelum diminta/disetujui**.

---

## Aturan Produk Utama WhiteFlood BG Remover (v2.5.0)

### 1. Tujuan Utama & Arsitektur Dual-Tool
Aplikasi ditujukan untuk foto produk furnitur (kursi, meja, lemari, dll.) untuk keperluan katalog dan kantor.
WhiteFlood v2.5.0 menyediakan 2 Alat Terpisah:
1. **✂️ Remove Background**
2. **🔍 Upscale (Pembesar Resolusi 2x / 4x)**

Kedua alat ini **tidak boleh berjalan bersamaan secara otomatis**. Pengguna memilih salah satu alat yang dibutuhkan melalui tombol navigasi di sidebar.

### 2. Manajemen & Pengukuran Memori RAM (Strict Single Engine)
- Hanya ada **1 mesin berat yang boleh aktif di RAM** pada satu waktu.
- Pembersihan safe-release saat berpindah alat:
  ```python
  global _rembg_session, _rembg_model_name
  if _rembg_session is not None:
      old_session = _rembg_session
      _rembg_session = None
      _rembg_model_name = None
      del old_session
      import gc
      gc.collect()
  ```
- Dilengkapi opsi `enable_cpu_mem_arena = False` pada ONNX SessionOptions untuk mengembalikan RAM langsung ke Windows setelah tiap gambar selesai diproses.

### 3. Aturan Khusus Upscale PNG Transparan (Alpha-Safe Pipeline)
- Gambar transparansi RGBA diolah terpisah:
  - **RGB (Warna foto)**: Dibersihkan dari sisa warna background lama di tepi (*alpha-aware padding*) lalu di-upscale.
  - **Alpha (Transparansi)**: Diperbesar dengan metode presisi deterministik Lanczos.
  - **Merge RGBA**: Digabung kembali menjadi PNG RGBA utuh.
- **Hasil**: Kaki meja tipis, ukiran kayu, dan siluet transparansi tetap aman 100% tanpa halo warna atau distorsi AI.

### 4. Aturan Output Remove Background
- **Haram Resize & Crop**: Ukuran piksel output harus 100% sama dengan gambar asli.
- **Format Output**: Selalu PNG transparan (RGBA).
- **Keamanan Data**: Olah data secara lokal, jangan upload gambar kantor ke API cloud eksternal.
- **Dukungan CPU**: Harus bisa jalan di komputer kantor biasa tanpa wajib GPU mahal.

### 5. Antarmuka (Gaya Upscayl & Sidebar ChatGPT)
- **Kredit Visual**: `Built by Bima Chakti © 2026 Bima Chakti` pada footer sidebar.
- **Layar Preview Utama Jumbo**: Mengisi 80% layar aplikasi dengan **Split-Slider Interaktif (Upscayl-style)**.
- **Sidebar Samping Kiri Ramping (~290px)**: Terinspirasi dari sidebar ChatGPT desktop.
- **Penamaan Batch**: Format `kursi-panjang-1.png`, `kursi-panjang-2.png` dengan pengaman anti-tertimpa (*collision safety*).
