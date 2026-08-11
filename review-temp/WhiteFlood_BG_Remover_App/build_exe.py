import os
import sys
import subprocess
import shutil


app_dir = os.path.abspath(os.path.dirname(__file__))


def bundled_data(source, destination):
    return f"--add-data={os.path.join(app_dir, source)};{destination}"


ffmpeg_dir = os.path.join(app_dir, "ffmpeg")
required_ffmpeg_files = ("ffmpeg.exe", "ffprobe.exe")
missing_ffmpeg_files = [
    name for name in required_ffmpeg_files
    if not os.path.isfile(os.path.join(ffmpeg_dir, name))
]
if missing_ffmpeg_files:
    print(
        "[ERROR] Binary FFmpeg wajib ada sebelum build: "
        + ", ".join(missing_ffmpeg_files)
    )
    print(f"[ERROR] Folder yang diperiksa: {os.path.abspath(ffmpeg_dir)}")
    sys.exit(1)

# Ensure onnxruntime capi directory is in PATH for PyInstaller isolated subprocesses
try:
    import onnxruntime
    capi_dir = os.path.abspath(os.path.join(os.path.dirname(onnxruntime.__file__), "capi"))
    if os.path.exists(capi_dir):
        print(f"[INFO] Adding onnxruntime DLL directory to PATH: {capi_dir}")
        os.environ["PATH"] = capi_dir + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(capi_dir)
            except Exception:
                pass
except Exception as e:
    print(f"[WARN] Could not find onnxruntime capi dir: {e}")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    f"--icon={os.path.join(app_dir, 'logo.ico')}",
    bundled_data("logo.ico", "."),
    bundled_data("logo.png", "."),
    bundled_data("realesrgan", "realesrgan"),
    bundled_data("assets", "assets"),
    bundled_data("ffmpeg", "ffmpeg"),
    "--collect-all=customtkinter",
    "--collect-all=onnxruntime",
    "--collect-all=rembg",
    "--collect-all=truststore",
    "--collect-all=pymatting",
    "--collect-all=vtracer",
    "--copy-metadata=pymatting",
    "--copy-metadata=truststore",
    "--hidden-import=psutil",
    "--exclude-module=PyQt5",
    "--exclude-module=PyQt6",
    "--exclude-module=PySide2",
    "--exclude-module=PySide6",
    "--exclude-module=matplotlib",
]

dist_path = os.environ.get("WHITEFLOOD_DIST_PATH")
work_path = os.environ.get("WHITEFLOOD_WORK_PATH")
spec_path = os.environ.get("WHITEFLOOD_SPEC_PATH")
if dist_path:
    cmd.extend(["--distpath", os.path.abspath(dist_path)])
if work_path:
    cmd.extend(["--workpath", os.path.abspath(work_path)])
if spec_path:
    cmd.extend(["--specpath", os.path.abspath(spec_path)])
cmd.extend([
    "--name=WhiteFlood_BG_Remover",
    os.path.join(app_dir, "whiteflood_app.py"),
])

print("[INFO] Running PyInstaller build command:")
print(" ".join(cmd))

p = subprocess.run(cmd)
if p.returncode != 0:
    print(f"[ERROR] PyInstaller failed with exit code {p.returncode}")
    sys.exit(p.returncode)

exe_path = os.path.join(
    os.path.abspath(dist_path) if dist_path else "dist",
    "WhiteFlood_BG_Remover.exe",
)
if os.path.exists(exe_path):
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"\n========================================")
    print(f"  BUILD SUCCESSFUL!")
    print(f"  EXE location: {os.path.abspath(exe_path)}")
    print(f"  EXE size: {size_mb:.2f} MB")
    print(f"========================================\n")
else:
    print(f"[ERROR] EXE not found at {exe_path}")
    sys.exit(1)
