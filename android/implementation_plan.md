# WhiteFlood Android Upscale MVP — Implementation Plan

Status: Disetujui melalui permintaan Bima pada 2026-09-10 untuk membangun APK dan preview UI.
Branch: `feat/android-upscale-mvp`
Scope: pilot Android, tidak mengubah source desktop aktif.

## Tujuan

Membuktikan workflow Upscale WhiteFlood dapat berjalan lokal pada Android dengan jalur NCNN/Vulkan yang sudah terbukti di proyek upstream, sambil mengikuti kontrak evidence B.I.M.A-DEV-INFRA.

## Keputusan implementasi

- Pilot dibangun sebagai overlay/branding WhiteFlood di atas upstream `tumuyan/RealSR-NCNN-Android` yang dipin ke commit `0eb16763761e46f55c6223439ca1ad20216bc4ab` (release 1.13.2).
- Tidak menyalin atau mem-port Python desktop ke Android.
- Android pilot menggunakan engine CLI NCNN/Vulkan upstream dan asset/model upstream untuk meminimalkan risiko port native baru.
- Arsitektur ini adalah pilot sideload, bukan arsitektur final Play Store.
- Source desktop Windows dan release v2.6.3 tidak diubah.

## Scope v0.1.0

1. Android arm64, minimum API 24.
2. Pilih satu foto dari perangkat.
3. Dua preset WhiteFlood:
   - `2x Photo` menggunakan command upstream `models-Real-ESRGAN-SourceBook -s 2`.
   - `4x Photo` menggunakan command upstream `models-Real-ESRGANv3-general -s 4`.
4. Pemrosesan lokal, tanpa upload foto ke API/cloud.
5. Preview hasil tetap memakai viewer upstream yang sudah menangani gambar besar.
6. Simpan output melalui flow upstream.
7. UI pilot WhiteFlood dark utility dengan aksen rose, fokus satu layar: pilih foto -> pilih skala -> proses -> preview -> simpan.
8. Kredit visual `Built by Bima Chakti` dan `© 2026 Bima Chakti` hanya di UI.

## Alpha/transparency

Pilot memakai upstream 1.13.2 yang sudah membawa rangkaian perbaikan alpha dari seri 1.13.x. Kontrak WhiteFlood tetap: jangan menambahkan watermark ke output dan jangan meng-upload gambar. Verifikasi alpha nyata pada perangkat tetap merupakan gate runtime terpisah.

## B.I.M.A-DEV-INFRA

Build APK tetap dimiliki repo WhiteFlood. B.I.M.A-DEV-INFRA dipakai sebagai shared repository-audit/evidence gate karena infra saat ini belum menyediakan generic Android build operation.

Build workflow project harus menghasilkan:

- APK debug arm64;
- SHA-256 APK;
- `evidence.json` berisi revision, upstream pin, ukuran dan digest artifact;
- log build GitHub Actions;
- artifact ZIP yang dapat diunduh.

Shared audit menggunakan reusable workflow B.I.M.A-DEV-INFRA yang dipin ke commit yang sudah dipakai consumer AI-COLOR-COMPARE.

## Batas pilot

- Bukan release Play Store.
- Target SDK upstream masih legacy; pilot hanya untuk sideload/proof-of-runtime.
- Tidak menambahkan Remove Background, Vectorize, atau Watermark ke Android pada tahap ini.
- Tidak mengklaim performa/RAM/kompatibilitas Vulkan sebelum diuji pada HP nyata.
- Tidak mengubah model atau binary desktop Windows.

## Verification gate

CI wajib:

1. clone upstream pada SHA yang dipin;
2. download asset upstream yang dibutuhkan;
3. aplikasikan overlay WhiteFlood;
4. build `assembleDebug`;
5. pastikan tepat satu APK ditemukan;
6. hitung SHA-256 dan ukuran artifact;
7. tulis evidence JSON/Markdown;
8. upload artifact;
9. shared repository audit B.I.M.A-DEV-INFRA berjalan terpisah.

Runtime yang belum boleh diklaim dari CI generik:

- Vulkan benar-benar aktif pada HP Bima;
- kualitas 2x/4x pada foto furnitur nyata;
- alpha PNG nyata;
- thermal/RAM pada sesi panjang.

## Definition of done pilot

Pilot dianggap build-complete hanya jika GitHub Actions menghasilkan APK dan digest yang dapat diperiksa. Pilot dianggap runtime-complete hanya setelah APK dipasang pada perangkat Android nyata dan satu fixture foto 2x + 4x berhasil diproses dan disimpan.