# User Notes & Product Rules (Bima / WhiteFlood v2.4+)

## Profil & Aturan Komunikasi
- Bima (User) adalah orang yang belum/tidak memahami fundamental pemrograman/coding.
- Komunikasi wajib menggunakan **Bahasa Indonesia** sepenuhnya, ramah, jujur, dan mudah dipahami tanpa jargon teknis berlebihan.
- **Jangan pernah auto-approve plan**. Selalu buat `implementation_plan.md` dan tunggu persetujuan eksplisit dari Bima.
- **Jangan ubah kode sebelum diminta/disetujui**.

---

## Aturan Produk Utama WhiteFlood BG Remover (v2.4+)

### 1. Tujuan Utama
Aplikasi ditujukan untuk foto produk furnitur (kursi, meja, lemari, dll.) untuk keperluan katalog dan kantor.
Prioritas utama: **Menjaga ketajaman objek (kaki kursi tipis, gagang pintu, ukiran, interior gelap) dan hasil potong yang bersih**.

### 2. Aturan Output yang Tidak Boleh Dilanggar
- **Haram Resize & Crop**: Ukuran piksel output harus 100% sama dengan gambar asli.
- **Format Output**: Selalu PNG transparan (RGBA).
- **Keamanan Data**: Olah data secara lokal, jangan upload gambar kantor ke API cloud eksternal.
- **Dukungan CPU**: Harus bisa jalan di komputer kantor biasa tanpa wajib kartu grafis GPU mahal.

### 3. Pengaturan Default AI
- **Default Mode**: `Furniture Quality` (menggunakan mesin `birefnet-massive`).
- **Default Smoothing**: `0` (Original / tanpa blur).
- **Default Alpha Matting**: `OFF` (Tidak aktif agar RAM irit).

### 4. Sistem Penamaan Batch (Batch Naming)
- Pengguna memasukkan nama batch (misal `kursi-panjang`).
- Hasil otomatis diberi nomor urut: `kursi-panjang-1.png`, `kursi-panjang-2.png`, dst.
- Karakter aneh/ilegal pada nama file otomatis disanitasi menjadi `-`.
- **Pengaman File**: Jika file dengan nama tersebut sudah ada di folder tujuan, sistem melanjutkan nomor berikutnya agar tidak menimpa (*overwrite*) file lama.
- Dilengkapi tombol **Batal Batch** yang aman.
