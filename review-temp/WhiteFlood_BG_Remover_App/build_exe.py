import os
import sys
import subprocess
import shutil

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
    "--icon=logo.ico",
    "--add-data=logo.ico;.",
    "--add-data=logo.png;.",
    "--add-data=realesrgan;realesrgan",
    "--add-data=assets;assets",
    "--add-data=ffmpeg;ffmpeg",
    "--collect-all=customtkinter",
    "--collect-all=onnxruntime",
    "--collect-all=rembg",
    "--collect-all=pymatting",
    "--collect-all=vtracer",
    "--copy-metadata=pymatting",
    "--hidden-import=psutil",
    "--exclude-module=PyQt5",
    "--exclude-module=PyQt6",
    "--exclude-module=PySide2",
    "--exclude-module=PySide6",
    "--exclude-module=matplotlib",
    "--name=WhiteFlood_BG_Remover",
    "whiteflood_app.py",
]

print("[INFO] Running PyInstaller build command:")
print(" ".join(cmd))

p = subprocess.run(cmd)
if p.returncode != 0:
    print(f"[ERROR] PyInstaller failed with exit code {p.returncode}")
    sys.exit(p.returncode)

exe_path = os.path.join("dist", "WhiteFlood_BG_Remover.exe")
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
