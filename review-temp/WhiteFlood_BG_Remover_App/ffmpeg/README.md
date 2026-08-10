# Bundled FFmpeg

WhiteFlood menyertakan binary Windows x64 LGPL yang dipin di folder ini:

- `ffmpeg.exe`
- `ffprobe.exe`
- `LICENSE.txt`
- `checksums.sha256`

Pinned source:

- Provider: `BtbN/FFmpeg-Builds`
- Release tag: `autobuild-2026-08-09-13-03`
- Asset: `ffmpeg-n8.1.2-34-g9b6c8969e0-win64-lgpl-8.1.zip`
- Release: https://github.com/BtbN/FFmpeg-Builds/releases/tag/autobuild-2026-08-09-13-03

WhiteFlood tidak mencari FFmpeg global agar hasil packaging tidak bergantung
pada komputer user. `build_exe.py` memasukkan folder ini ke dalam EXE. Binary
`.exe` di source ditrack dengan Git LFS agar tidak terkena batas file GitHub.
