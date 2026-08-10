# Bundled FFmpeg

Tempatkan binary Windows x64 LGPL yang sudah dipin di folder ini:

- `ffmpeg.exe`
- `ffprobe.exe`

Tambahkan DLL yang dibutuhkan oleh build yang dipilih, checksum masing-masing
binary, dan notice lisensi sebelum membuat EXE distribusi. WhiteFlood tidak
mencari FFmpeg global agar hasil packaging tidak bergantung pada komputer user.
