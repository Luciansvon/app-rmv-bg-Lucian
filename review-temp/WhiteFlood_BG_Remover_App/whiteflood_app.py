"""
WhiteFlood BG Remover & Upscaler v2.5.0
Built by Bima Chakti © 2026 Bima Chakti
Aplikasi Windows Desktop untuk Foto Produk Furnitur (PNG Transparan).
Dual Tools: Remove Background (Dimensi 100% Presisi) & Upscale (2x/4x Alpha-Safe).
Layout: Upscayl-Style Interactive Split-Slider Preview + Narrow Sidebar (~290px).
"""

import os
import sys
import gc
import threading
import importlib.util
import re
import math
from pathlib import Path
from collections import deque

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageFilter, ImageDraw, ImageTk
import numpy as np

# ── Fix pythonw (windowless) stdout/stderr error ────────
class _DummyWriter:
    def write(self, s): pass
    def flush(self): pass

if sys.stdout is None:
    sys.stdout = _DummyWriter()
if sys.stderr is None:
    sys.stderr = _DummyWriter()

# ── Fix taskbar icon on Windows ──────────────────────────
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "BimaChakti.WhiteFlood.2.5"
    )
except Exception:
    pass

# ── Helper to measure process RSS RAM memory ────────────
def get_process_memory_mb():
    try:
        import psutil
        return round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 1)
    except Exception:
        return 0.0

# ── Helper to check if model is already downloaded ──────
def is_model_downloaded(model_name):
    u2net_dir = Path.home() / ".u2net"
    if not u2net_dir.exists():
        return False
    target = u2net_dir / f"{model_name}.onnx"
    if target.exists() and target.stat().st_size > 1_000_000:
        return True
    for f in u2net_dir.glob("*.onnx"):
        if model_name in f.name and f.stat().st_size > 1_000_000:
            return True
    return False

# ── Filename Sanitization for Windows ────────────────────
def sanitize_filename(name):
    """Sanitize invalid Windows filename characters."""
    if not name or not name.strip():
        return "output"
    cleaned = re.sub(r'[<>:"/\\|?*]', '-', name.strip())
    cleaned = re.sub(r'[\s\-]+', '-', cleaned).strip('.- ')
    return cleaned if cleaned else "output"

# ── Check if rembg is available ──────────────────────────
REMBG_OK = importlib.util.find_spec("rembg") is not None

# Cache for rembg session (lazy loaded)
_rembg_session = None
_rembg_model_name = None

# ═══════════════════════════════════════════════════════════
#  Theme & Constants
# ═══════════════════════════════════════════════════════════

APP_NAME = "WhiteFlood BG Remover"
VERSION = "2.5.0"
DEVELOPER_CREDIT = "Built by Bima Chakti\n© 2026 Bima Chakti"

TOOL_REMOVE_BG = "remove_bg"
TOOL_UPSCALE = "upscale"

MODE_FURNITURE = "🪑  Furniture Quality"
MODE_FAST = "⚡  Fast"
MODE_PERSON = "👤  Person"
MODE_HIGH_DETAIL = "🔍  High Detail"
MODE_WHITE = "🌊  White Background"

MODE_MAP = {
    MODE_FURNITURE: "birefnet-massive",
    MODE_FAST: "birefnet-general",
    MODE_PERSON: "birefnet-portrait",
    MODE_HIGH_DETAIL: "birefnet-hrsod",
}

MODE_DESC_MAP = {
    MODE_FURNITURE: "🪑 Furniture Quality (Rekomendasi Utama — Foto Produk Furnitur, Kayu, & Katalog)",
    MODE_FAST: "⚡ Fast (Proses Cepat untuk Gambar Biasa)",
    MODE_PERSON: "👤 Person (Khusus Foto Orang, Manusia, Pakaian, & Rambut)",
    MODE_HIGH_DETAIL: "🔍 High Detail (Khusus Resolusi Tinggi & Ukiran Halus)",
    MODE_WHITE: "🌊 White Background (Instan Tanpa AI / Tanpa Internet untuk Background Polos)",
}

REFINE_ORIGINAL = "Original (Rekomendasi)"
REFINE_SOFT = "Soft (Pinggiran Halus)"
REFINE_ALPHA_MATTE = "Alpha Matte (Deteksi Rambut)"

C = {
    "bg":           "#0f0f18",
    "card":         "#161626",
    "card_alt":     "#11111d",
    "border":       "#222238",
    "accent":       "#e94560",
    "accent_hover": "#d63851",
    "blue":         "#1e3a8a",
    "blue_hover":   "#1d4ed8",
    "text":         "#f1f5f9",
    "dim":          "#8e8ea0",
    "green":        "#22c55e",
    "green_dark":   "#16a34a",
    "purple":       "#a855f7",
    "purple_hover": "#9333ea",
    "red":          "#ef4444",
    "red_hover":    "#dc2626",
}

NEIGHBORS_8 = [(-1, -1), (-1, 0), (-1, 1),
               (0, -1),           (0, 1),
               (1, -1),  (1, 0),  (1, 1)]


# ═══════════════════════════════════════════════════════════
#  Splash Screen & Custom Widgets
# ═══════════════════════════════════════════════════════════

def show_splash(parent):
    """Show a lightweight splash screen while application loads."""
    splash = ctk.CTkToplevel(parent)
    splash.overrideredirect(True)
    splash.geometry("420x220")
    splash.configure(fg_color=C["card_alt"])

    try:
        ws = splash.winfo_screenwidth()
        hs = splash.winfo_screenheight()
        x = max(0, (ws // 2) - 210)
        y = max(0, (hs // 2) - 110)
        splash.geometry(f"420x220+{x}+{y}")
    except Exception:
        pass

    lbl_title = ctk.CTkLabel(
        splash, text="◆  WhiteFlood BG Remover",
        font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
        text_color=C["accent"],
    )
    lbl_title.pack(pady=(35, 4))

    lbl_sub = ctk.CTkLabel(
        splash, text=f"v{VERSION}  •  Built by Bima Chakti",
        font=ctk.CTkFont(size=11), text_color=C["dim"],
    )
    lbl_sub.pack(pady=(0, 20))

    progress = ctk.CTkProgressBar(splash, width=320, height=4, progress_color=C["accent"])
    progress.pack()
    progress.configure(mode="indeterminate")
    progress.start()

    splash.update()
    return splash


class LoadingSpinner(ctk.CTkCanvas):
    """Clean animated circular spinner for processing feedback."""
    def __init__(self, parent, size=50, color=C["accent"], bg_color=C["card_alt"]):
        super().__init__(parent, width=size, height=size, bg=bg_color, highlightthickness=0)
        self.size = size
        self.color = color
        self.bg_color = bg_color
        self.angle = 0
        self.running = False

    def start(self):
        if not self.running:
            self.running = True
            self._animate()

    def stop(self):
        self.running = False

    def _animate(self):
        if not self.running:
            return
        self.delete("all")
        margin = 6
        extent = 100
        self.create_arc(
            margin, margin, self.size - margin, self.size - margin,
            start=self.angle, extent=extent,
            style="arc", outline=self.color, width=4
        )
        self.angle = (self.angle + 12) % 360
        self.after(30, self._animate)


class SplitSliderPreview(ctk.CTkCanvas):
    """Interactive Upscayl-style split-slider image comparison widget."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["card_alt"], highlightthickness=0, **kwargs)
        self.slider_pos = 0.5
        self.original_img = None
        self.result_img = None
        self._dragging = False

        self.bind("<Configure>", self._on_resize)
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    def set_images(self, original, result):
        self.original_img = original
        self.result_img = result
        self.redraw()

    def _on_resize(self, event):
        self.redraw()

    def _on_click(self, event):
        self._update_slider_from_mouse(event.x)
        self._dragging = True

    def _on_drag(self, event):
        if self._dragging:
            self._update_slider_from_mouse(event.x)

    def _on_release(self, event):
        self._dragging = False

    def _update_slider_from_mouse(self, mouse_x):
        w = self.winfo_width()
        if w > 20:
            self.slider_pos = max(0.02, min(0.98, mouse_x / float(w)))
            self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()

        if not self.original_img or w < 30 or h < 30:
            self.create_text(
                w // 2, h // 2,
                text="Belum ada gambar\n\nKlik 'Pilih Gambar' pada menu samping untuk memulai.",
                fill=C["dim"], font=("Segoe UI", 13), justify="center"
            )
            return

        # Use result size as the reference for display when available (Upscale mode)
        ref_img = self.result_img if self.result_img else self.original_img
        ref_w, ref_h = ref_img.size
        scale = min(w / ref_w, h / ref_h)
        disp_w = max(1, int(ref_w * scale))
        disp_h = max(1, int(ref_h * scale))

        offset_x = (w - disp_w) // 2
        offset_y = (h - disp_h) // 2

        orig_disp = self.original_img.resize((disp_w, disp_h), Image.LANCZOS)
        if orig_disp.mode != "RGBA":
            orig_disp = orig_disp.convert("RGBA")

        if self.result_img:
            res_disp = self.result_img.resize((disp_w, disp_h), Image.LANCZOS)
            checker = make_checkerboard(disp_w, disp_h, cell=10)
            checker.paste(res_disp, (0, 0), res_disp)
            res_disp = checker
        else:
            res_disp = orig_disp

        split_x = int(self.slider_pos * disp_w)
        split_x = max(0, min(disp_w, split_x))

        comp = Image.new("RGBA", (disp_w, disp_h))
        if split_x > 0:
            left_part = orig_disp.crop((0, 0, split_x, disp_h))
            comp.paste(left_part, (0, 0))
        if split_x < disp_w:
            right_part = res_disp.crop((split_x, 0, disp_w, disp_h))
            comp.paste(right_part, (split_x, 0))

        self._comp_tk = ImageTk.PhotoImage(comp)
        self.create_image(offset_x, offset_y, anchor="nw", image=self._comp_tk)

        line_x = offset_x + split_x
        self.create_line(line_x, offset_y, line_x, offset_y + disp_h, fill=C["accent"], width=3)

        handle_y = offset_y + (disp_h // 2)
        self.create_rectangle(line_x - 14, handle_y - 18, line_x + 14, handle_y + 18, fill=C["accent"], outline=C["text"], width=1)
        self.create_text(line_x, handle_y, text="◄  ►", fill="#ffffff", font=("Segoe UI", 9, "bold"))

        self.create_rectangle(offset_x + 10, offset_y + 10, offset_x + 110, offset_y + 32, fill="#12121f", outline=C["border"], width=1)
        self.create_text(offset_x + 60, offset_y + 21, text="GAMBAR ASLI", fill="#ffffff", font=("Segoe UI", 9, "bold"))

        self.create_rectangle(offset_x + disp_w - 130, offset_y + 10, offset_x + disp_w - 10, offset_y + 32, fill="#12121f", outline=C["border"], width=1)
        self.create_text(offset_x + disp_w - 70, offset_y + 21, text="HASIL PROSES", fill="#ffffff", font=("Segoe UI", 9, "bold"))


class CollapsibleFrame(ctk.CTkFrame):
    """Clean collapsible section for advanced settings."""
    def __init__(self, parent, title="Pengaturan Lanjutan", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.is_open = False

        self.btn_toggle = ctk.CTkButton(
            self, text=f"▶  {title}", anchor="w",
            fg_color="transparent", text_color=C["dim"],
            hover_color=C["card_alt"], font=ctk.CTkFont(size=12, weight="bold"),
            height=28, command=self.toggle
        )
        self.btn_toggle.pack(fill="x")
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")

    def toggle(self):
        self.is_open = not self.is_open
        if self.is_open:
            self.btn_toggle.configure(text=self.btn_toggle.cget("text").replace("▶", "▼"))
            self.content_frame.pack(fill="x", pady=(4, 0))
        else:
            self.btn_toggle.configure(text=self.btn_toggle.cget("text").replace("▼", "▶"))
            self.content_frame.pack_forget()


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def make_checkerboard(w, h, cell=10):
    img = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(img)
    c1, c2 = (210, 210, 210, 255), (170, 170, 170, 255)
    for row in range(0, h, cell):
        for col in range(0, w, cell):
            c = c1 if (col // cell + row // cell) % 2 == 0 else c2
            draw.rectangle([col, row, col + cell - 1, row + cell - 1], fill=c)
    return img


def metadata_for_save(img):
    kw = {}
    for key in ("dpi", "icc_profile", "exif"):
        val = img.info.get(key)
        if val:
            kw[key] = val
    return kw


# ═══════════════════════════════════════════════════════════
#  AI Background Removal Engine
# ═══════════════════════════════════════════════════════════

def _get_rembg_session(model_name="birefnet-massive", status_cb=None):
    """Lazy-load rembg and cache session with ONNX SessionOptions to prevent 12GB RAM arenas."""
    global _rembg_session, _rembg_model_name

    if _rembg_session is not None:
        if _rembg_model_name == model_name:
            return _rembg_session
        else:
            old_session = _rembg_session
            _rembg_session = None
            _rembg_model_name = None
            try:
                del old_session
                gc.collect()
            except Exception:
                pass

    from rembg import new_session
    import onnxruntime as ort

    # Configure ONNX SessionOptions: disable arena memory allocation to release RAM back to OS
    opts = ort.SessionOptions()
    opts.enable_cpu_mem_arena = False
    opts.enable_mem_pattern = False

    max_retries = 3
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            if status_cb:
                if attempt > 1:
                    status_cb(f"⬇  Mencoba ulang unduhan model AI '{model_name}' ({attempt}/{max_retries})…")
                else:
                    status_cb(f"⬇  Mengunduh model AI '{model_name}'… (cuma sekali, mohon tunggu)")

            _rembg_session = new_session(model_name, sess_options=opts)
            _rembg_model_name = model_name

            if status_cb:
                status_cb(f"✅  Model AI '{model_name}' siap!")

            return _rembg_session
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                import time
                time.sleep(1.5)

    err_msg = str(last_err)
    if any(k in err_msg for k in ("Connection", "RemoteDisconnected", "time out", "timed out", "Disconnected")):
        raise RuntimeError(
            f"Koneksi internet terputus saat mengunduh model '{model_name}'.\n\n"
            f"Silakan pastikan koneksi internet stabil lalu klik 'Preview Ulang' untuk mencoba lagi."
        )
    raise RuntimeError(f"Gagal memuat model '{model_name}': {err_msg}")


def _get_realesrgan_exe_path():
    """Locate realesrgan-ncnn-vulkan.exe in frozen MEIPASS, local directory, or PATH."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent

    candidates = [
        base / "realesrgan" / "realesrgan-ncnn-vulkan.exe",
        base / "realesrgan-ncnn-vulkan.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    import shutil
    which_exe = shutil.which("realesrgan-ncnn-vulkan")
    if which_exe:
        return Path(which_exe)
    return None


def refine_alpha_mask(alpha_img, edge_smooth=0, erode_size=0):
    """
    Community Mask Refinement:
    1. Erode (shrink) 1px to strip white background color bleed along outer edge if requested.
    2. Apply GaussianBlur for smooth anti-aliased edge when requested.
    """
    if erode_size > 0:
        alpha_img = alpha_img.filter(ImageFilter.MinFilter(3))

    if edge_smooth > 0:
        alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=edge_smooth))

    return alpha_img


def ai_remove_bg(img, edge_smooth=0, erode_size=0, model_name="birefnet-massive",
                 alpha_matting=False, status_cb=None):
    """Remove background using neural network preserving exact pixel dimensions."""
    if not REMBG_OK:
        raise RuntimeError(
            "Pustaka 'rembg' belum terinstall.\n"
            "Silakan install dengan: pip install rembg[cpu]"
        )

    from rembg import remove as rembg_remove

    original_size = img.size
    rgba = img.convert("RGBA")

    session = _get_rembg_session(model_name, status_cb=status_cb)

    result = rembg_remove(
        rgba,
        session=session,
        post_process_mask=False,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10,
    )

    if edge_smooth > 0 or erode_size > 0:
        arr = np.array(result, dtype=np.uint8)
        alpha = arr[:, :, 3]
        alpha_pil = Image.fromarray(alpha, "L")

        refined_alpha = refine_alpha_mask(alpha_pil, edge_smooth=edge_smooth, erode_size=erode_size)
        arr[:, :, 3] = np.array(refined_alpha)

        result = Image.fromarray(arr, "RGBA")
        del arr, alpha, alpha_pil, refined_alpha
        gc.collect()

    if result.size != original_size:
        raise RuntimeError("Internal error: Ukuran piksel berubah.")
    return result


def flood_remove_bg(img, threshold=220, fringe=30,
                    edge_smooth=0, aggressive=False):
    """Remove near-white connected background preserving exact pixel dimensions."""
    original_size = img.size
    rgba = img.convert("RGBA")
    arr = np.array(rgba, dtype=np.uint8)
    h, w = arr.shape[:2]

    rgb = arr[:, :, :3].astype(np.float32)
    alpha = arr[:, :, 3].copy()
    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

    near_white = (lum > threshold) & (alpha > 0)

    visited = np.zeros((h, w), dtype=np.bool_)
    q = deque()

    for x in range(w):
        for y in (0, h - 1):
            if near_white[y, x] and not visited[y, x]:
                visited[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if near_white[y, x] and not visited[y, x]:
                visited[y, x] = True
                q.append((y, x))

    while q:
        y, x = q.popleft()
        for dy, dx in NEIGHBORS_8:
            ny, nx = y + dy, x + dx
            if (0 <= ny < h and 0 <= nx < w
                    and not visited[ny, nx] and near_white[ny, nx]):
                visited[ny, nx] = True
                q.append((ny, nx))

    bg_float = visited.astype(np.float32)
    if edge_smooth > 0:
        m = Image.fromarray((bg_float * 255).astype(np.uint8), "L")
        m = m.filter(ImageFilter.GaussianBlur(radius=edge_smooth))
        bg_smooth = np.array(m).astype(np.float32) / 255.0
    else:
        bg_smooth = bg_float

    new_alpha = arr[:, :, 3].astype(np.float32) * (1.0 - bg_smooth)

    if fringe > 0:
        edge_adj = np.zeros_like(visited)
        for dy, dx in NEIGHBORS_8:
            sy = slice(max(0, -dy), min(h, h - dy))
            sx = slice(max(0, -dx), min(w, w - dx))
            dy2 = slice(max(0, dy), min(h, h + dy))
            dx2 = slice(max(0, dx), min(w, w + dx))
            edge_adj[dy2, dx2] |= visited[sy, sx]
        candidate = edge_adj & (~visited) & (new_alpha > 0)
        ws = np.clip((lum - (threshold - 30)) / max(1, 255 - (threshold - 30)), 0, 1)
        amt = np.clip(fringe / 80.0, 0.0, 0.85)
        red = ws * amt * 255.0
        new_alpha[candidate] = np.maximum(0, new_alpha[candidate] - red[candidate])

    arr[:, :, 3] = new_alpha.astype(np.uint8)
    result = Image.fromarray(arr, "RGBA")

    del arr, rgb, alpha, lum, near_white, visited
    gc.collect()

    if result.size != original_size:
        raise RuntimeError("Internal error: Ukuran piksel berubah.")
    return result


# ═══════════════════════════════════════════════════════════
#  Alpha-Safe Real-ESRGAN NCNN Vulkan Upscaler Engine (2x / 4x)
# ═══════════════════════════════════════════════════════════

def upscale_image_alpha_safe(img, scale=2, status_cb=None):
    """
    Upscale image using Real-ESRGAN NCNN Vulkan GPU Backend:
    - RGB Channels: AI-upscaled via Real-ESRGAN NCNN Vulkan subprocess.
    - Alpha Channel: Deterministic Lanczos upscale.
    Preserves exact furniture silhouettes, thin legs, and handles without AI alpha hallucination.
    """
    original_size = img.size
    new_w = original_size[0] * scale
    new_h = original_size[1] * scale

    exe_path = _get_realesrgan_exe_path()
    if exe_path is None:
        raise RuntimeError(
            "Biner 'realesrgan-ncnn-vulkan.exe' tidak ditemukan.\n"
            "Pastikan folder 'realesrgan' terikut pada aplikasi."
        )

    if status_cb:
        status_cb(f"🔍 AI Upscale ({scale}x: {original_size[0]}×{original_size[1]} → {new_w}×{new_h} px) via Real-ESRGAN Vulkan...")

    import tempfile
    import subprocess

    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        in_tmp = tmpdir_path / "input_rgb.jpg"
        out_tmp = tmpdir_path / "output_rgb.png"

        if has_alpha:
            img_rgba = img.convert("RGBA")
            r, g, b, a = img_rgba.split()
            rgb_img = Image.merge("RGB", (r, g, b))
            rgb_img.save(in_tmp, format="JPEG", quality=95)

            a_upscaled = a.resize((new_w, new_h), Image.LANCZOS)
        else:
            img_rgb = img.convert("RGB")
            img_rgb.save(in_tmp, format="JPEG", quality=95)
            a_upscaled = None

        cmd = [
            str(exe_path),
            "-i", str(in_tmp.resolve()),
            "-o", str(out_tmp.resolve()),
            "-s", str(scale),
            "-n", "realesrgan-x4plus",
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not out_tmp.exists():
            err_msg = res.stderr.strip() if res.stderr else f"Exit code {res.returncode}"
            raise RuntimeError(f"Gagal memproses Real-ESRGAN Vulkan: {err_msg}")

        with Image.open(out_tmp) as up_rgb:
            up_rgb_loaded = up_rgb.copy()

        if has_alpha and a_upscaled is not None:
            r_up, g_up, b_up = up_rgb_loaded.convert("RGB").split()
            result = Image.merge("RGBA", (r_up, g_up, b_up, a_upscaled))
        else:
            result = up_rgb_loaded.convert("RGB")

    gc.collect()

    if result.size != (new_w, new_h):
        raise RuntimeError(f"Internal error: Ukuran upscale mismatch ({result.size} vs {new_w}x{new_h})")

    return result


def process_file(src, dst, mode, threshold, fringe, edge_smooth, aggressive,
                 model_name="birefnet-massive", alpha_matting=False, erode_size=0,
                 tool=TOOL_REMOVE_BG, scale=2):
    """Process a single file preserving rules for Remove BG or Upscale."""
    src, dst = Path(src), Path(dst)
    with Image.open(src) as img:
        original_size = img.size
        meta = metadata_for_save(img)

        if tool == TOOL_UPSCALE:
            result = upscale_image_alpha_safe(img, scale=scale)
            expected_size = (original_size[0] * scale, original_size[1] * scale)
        else:
            if mode == MODE_WHITE:
                result = flood_remove_bg(img, threshold, fringe, edge_smooth, aggressive)
            else:
                result = ai_remove_bg(img, edge_smooth=edge_smooth, erode_size=erode_size, model_name=model_name, alpha_matting=alpha_matting)
            expected_size = original_size

        if result.size != expected_size:
            raise RuntimeError(f"Resolusi tidak cocok: Ekspektasi {expected_size} -> {result.size}")

        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            result.save(dst, format="PNG", optimize=False, **meta)
        except Exception:
            result.save(dst, format="PNG", optimize=False)

        with Image.open(dst) as check:
            if check.size != expected_size:
                raise RuntimeError(f"Mismatch resolusi tersimpan: Ekspektasi {expected_size} -> {check.size}")
            if check.size != expected_size:
                raise RuntimeError(f"Mismatch resolusi tersimpan: Ekspektasi {expected_size} -> {check.size}")


# ═══════════════════════════════════════════════════════════
#  Application Main UI
# ═══════════════════════════════════════════════════════════

class WhiteFloodApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")

        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("1100x760")
        self.minsize(960, 680)
        self.configure(fg_color=C["bg"])

        self._set_app_icon()

        # State Variables
        self.active_tool = TOOL_REMOVE_BG
        self.mode_var = ctk.StringVar(value=MODE_FURNITURE)
        self.refine_var = ctk.StringVar(value=REFINE_ORIGINAL)
        self.scale_var = ctk.IntVar(value=2)
        self.threshold_var = ctk.IntVar(value=220)
        self.fringe_var = ctk.IntVar(value=30)
        self.aggressive_var = ctk.BooleanVar(value=False)
        self.output_dir = ctk.StringVar(value="")
        self.batch_name_var = ctk.StringVar(value="kursi-panjang")
        self.status_text = ctk.StringVar(
            value="Siap. Pilih alat 'Hapus Background' atau 'Upscale'."
        )

        self._src_path = None
        self._original = None
        self._original_meta = {}
        self._result = None
        self._processing = False
        self._batch_cancelled = False

        self._build_ui()

    def _set_app_icon(self):
        """Set window icon from logo.ico or logo.png."""
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).parent

        ico_path = base / "logo.ico"
        png_path = base / "logo.png"

        def _apply_icon():
            try:
                if ico_path.exists():
                    self.iconbitmap(default=str(ico_path))
                    self.iconbitmap(str(ico_path))
            except Exception:
                pass

        self.after(100, _apply_icon)

    # ───────────────────────────────────────
    #  Build UI Layout
    # ───────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=0, minsize=290)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ════════════════════════════════════════════════════
        #  LEFT SIDEBAR PANEL (~290px)
        # ════════════════════════════════════════════════════
        sidebar_bg = ctk.CTkFrame(self, width=290, fg_color=C["card"], corner_radius=0)
        sidebar_bg.grid(row=0, column=0, sticky="nsew")
        sidebar_bg.pack_propagate(False)

        sidebar = ctk.CTkScrollableFrame(
            sidebar_bg, fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["accent"],
        )
        sidebar.pack(fill="both", expand=True, padx=12, pady=12)

        # Header Title & Version
        tf = ctk.CTkFrame(sidebar, fg_color="transparent")
        tf.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            tf, text="◆ WhiteFlood",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=C["accent"],
        ).pack(side="left")
        ctk.CTkLabel(
            tf, text=f"v{VERSION}",
            font=ctk.CTkFont(size=10), text_color=C["dim"],
        ).pack(side="left", padx=(6, 0), pady=(4, 0))

        # Tool Navigation Tabs (Remove BG vs Upscale)
        self._section_label(sidebar, "PILIH ALAT")
        nav_f = ctk.CTkFrame(sidebar, fg_color=C["card_alt"], corner_radius=6)
        nav_f.pack(fill="x", pady=(0, 10))
        nav_f.columnconfigure((0, 1), weight=1)

        self.btn_tool_rmbg = ctk.CTkButton(
            nav_f, text="✂️ Hapus BG", command=lambda: self._switch_tool(TOOL_REMOVE_BG),
            fg_color=C["accent"], hover_color=C["accent_hover"],
            font=ctk.CTkFont(size=11, weight="bold"), height=32, corner_radius=6,
        )
        self.btn_tool_rmbg.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        self.btn_tool_upscale = ctk.CTkButton(
            nav_f, text="🔍 Upscale", command=lambda: self._switch_tool(TOOL_UPSCALE),
            fg_color="transparent", text_color=C["dim"], hover_color=C["border"],
            font=ctk.CTkFont(size=11, weight="bold"), height=32, corner_radius=6,
        )
        self.btn_tool_upscale.grid(row=0, column=1, sticky="ew", padx=2, pady=2)

        # ── Tool 1: Remove BG Settings Frame ────────────────
        self.frame_rmbg_settings = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.frame_rmbg_settings.pack(fill="x")

        self._section_label(self.frame_rmbg_settings, "MODE PROSES AI")
        modes = [MODE_FURNITURE, MODE_FAST, MODE_PERSON, MODE_HIGH_DETAIL, MODE_WHITE]
        self.mode_dropdown = ctk.CTkOptionMenu(
            self.frame_rmbg_settings, values=modes, variable=self.mode_var,
            command=self._on_mode_change,
            fg_color=C["card_alt"], button_color=C["accent"],
            button_hover_color=C["accent_hover"],
            dropdown_fg_color=C["card"], dropdown_hover_color=C["border"],
            dropdown_text_color=C["text"], text_color=C["text"],
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=6, height=32,
        )
        self.mode_dropdown.pack(fill="x", pady=(0, 4))

        self.mode_desc = ctk.CTkLabel(
            self.frame_rmbg_settings, text="", font=ctk.CTkFont(size=10),
            text_color=C["dim"], wraplength=260, justify="left",
        )
        self.mode_desc.pack(anchor="w", pady=(0, 8))
        self._update_mode_desc()

        self.lbl_refine = self._section_label(self.frame_rmbg_settings, "KETAJAMAN TEPI")
        self.refine_dropdown = ctk.CTkOptionMenu(
            self.frame_rmbg_settings, values=[REFINE_ORIGINAL, REFINE_SOFT, REFINE_ALPHA_MATTE],
            variable=self.refine_var,
            fg_color=C["card_alt"], button_color=C["blue"],
            button_hover_color=C["blue_hover"],
            dropdown_fg_color=C["card"], dropdown_hover_color=C["border"],
            dropdown_text_color=C["text"], text_color=C["text"],
            font=ctk.CTkFont(size=11), corner_radius=6, height=30,
        )
        self.refine_dropdown.pack(fill="x", pady=(0, 8))

        self.adv_section = CollapsibleFrame(self.frame_rmbg_settings, title="Pengaturan Lanjutan")
        self.adv_section.pack(fill="x", pady=(0, 8))
        adv_f = self.adv_section.content_frame

        ctk.CTkLabel(adv_f, text="White Threshold", text_color=C["text"], font=ctk.CTkFont(size=11)).pack(anchor="w")
        sl_t = ctk.CTkSlider(
            adv_f, from_=180, to=254, variable=self.threshold_var,
            fg_color=C["border"], progress_color=C["accent"],
            button_color=C["accent"], button_hover_color=C["accent_hover"],
            command=self._on_threshold, height=14,
        )
        sl_t.pack(fill="x", pady=(2, 0))
        self._lbl_white_threshold = ctk.CTkLabel(adv_f, text="220", text_color=C["accent"], font=ctk.CTkFont(size=10, weight="bold"))
        self._lbl_white_threshold.pack(anchor="e", pady=(0, 4))

        ctk.CTkLabel(adv_f, text="Fringe Cleanup", text_color=C["text"], font=ctk.CTkFont(size=11)).pack(anchor="w")
        sl_f = ctk.CTkSlider(
            adv_f, from_=0, to=80, variable=self.fringe_var,
            fg_color=C["border"], progress_color=C["accent"],
            button_color=C["accent"], button_hover_color=C["accent_hover"],
            command=self._on_fringe, height=14,
        )
        sl_f.pack(fill="x", pady=(2, 0))
        self._lbl_fringe_cleanup = ctk.CTkLabel(adv_f, text="30", text_color=C["accent"], font=ctk.CTkFont(size=10, weight="bold"))
        self._lbl_fringe_cleanup.pack(anchor="e", pady=(0, 4))

        self.aggressive_cb = ctk.CTkCheckBox(
            adv_f, text="Mode Agresif", variable=self.aggressive_var,
            font=ctk.CTkFont(size=11), text_color=C["text"],
            fg_color=C["accent"], hover_color=C["accent_hover"],
            border_color=C["border"], corner_radius=4,
        )
        self.aggressive_cb.pack(anchor="w", pady=(2, 0))

        # ── Tool 2: Upscale Settings Frame ──────────────────
        self.frame_upscale_settings = ctk.CTkFrame(sidebar, fg_color="transparent")

        self._section_label(self.frame_upscale_settings, "SKALA PEMBESARAN")
        scale_f = ctk.CTkFrame(self.frame_upscale_settings, fg_color=C["card_alt"], corner_radius=6)
        scale_f.pack(fill="x", pady=(0, 8))
        scale_f.columnconfigure((0, 1), weight=1)

        self.btn_scale_2x = ctk.CTkButton(
            scale_f, text="2x (Rekomendasi)", command=lambda: self._set_scale(2),
            fg_color=C["accent"], hover_color=C["accent_hover"],
            font=ctk.CTkFont(size=11, weight="bold"), height=32, corner_radius=6,
        )
        self.btn_scale_2x.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        self.btn_scale_4x = ctk.CTkButton(
            scale_f, text="4x", command=lambda: self._set_scale(4),
            fg_color="transparent", text_color=C["dim"], hover_color=C["border"],
            font=ctk.CTkFont(size=11, weight="bold"), height=32, corner_radius=6,
        )
        self.btn_scale_4x.grid(row=0, column=1, sticky="ew", padx=2, pady=2)

        ctk.CTkLabel(
            self.frame_upscale_settings,
            text="🔒 Transparansi Alpha-Safe: Siluet kaki meja tipis & ukiran dipertahankan presisi 100%.",
            font=ctk.CTkFont(size=10), text_color=C["dim"], wraplength=260, justify="left",
        ).pack(anchor="w", pady=(0, 10))

        # Single Image Actions
        self._lbl_single_section = self._section_label(sidebar, "GAMBAR TUNGGAL")
        
        self.btn_pick = ctk.CTkButton(
            sidebar, text="Pilih Gambar", command=self.load_and_process,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold"), height=36, corner_radius=6,
        )
        self.btn_pick.pack(fill="x", pady=(0, 6))

        act_sub = ctk.CTkFrame(sidebar, fg_color="transparent")
        act_sub.pack(fill="x", pady=(0, 10))
        act_sub.columnconfigure((0, 1), weight=1)

        self.btn_repreview = ctk.CTkButton(
            act_sub, text="Preview Ulang", command=self.repreview,
            fg_color=C["blue"], hover_color=C["blue_hover"],
            font=ctk.CTkFont(size=11, weight="bold"), height=32, corner_radius=6,
            state="disabled",
        )
        self.btn_repreview.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        self.btn_save = ctk.CTkButton(
            act_sub, text="Simpan PNG", command=self.save_result,
            fg_color=C["border"], hover_color=C["blue_hover"],
            font=ctk.CTkFont(size=11, weight="bold"), height=32, corner_radius=6,
            state="disabled",
        )
        self.btn_save.grid(row=0, column=1, sticky="ew", padx=(3, 0))

        # Batch Section
        self._section_label(sidebar, "PROSES BATCH (FOLDER)")

        ctk.CTkLabel(sidebar, text="Nama Batch", text_color=C["dim"], font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.entry_batch_name = ctk.CTkEntry(
            sidebar, textvariable=self.batch_name_var,
            fg_color=C["card_alt"], border_color=C["border"],
            text_color=C["text"], font=ctk.CTkFont(size=11), height=30,
        )
        self.entry_batch_name.pack(fill="x", pady=(2, 6))
        self.entry_batch_name.bind("<KeyRelease>", self._update_batch_preview)

        ctk.CTkLabel(sidebar, text="Folder Output", text_color=C["dim"], font=ctk.CTkFont(size=11)).pack(anchor="w")
        out_sub = ctk.CTkFrame(sidebar, fg_color="transparent")
        out_sub.pack(fill="x", pady=(2, 6))
        out_sub.columnconfigure(0, weight=1)

        ctk.CTkEntry(
            out_sub, textvariable=self.output_dir,
            fg_color=C["card_alt"], border_color=C["border"],
            text_color=C["text"], font=ctk.CTkFont(size=11), height=30,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(
            out_sub, text="Pilih", width=50, height=30,
            fg_color=C["border"], hover_color=C["blue"],
            command=self._choose_output, corner_radius=6,
        ).grid(row=0, column=1)

        self.lbl_batch_preview = ctk.CTkLabel(
            sidebar, text="Contoh: kursi-panjang-1.png...",
            font=ctk.CTkFont(size=10), text_color=C["dim"], anchor="w"
        )
        self.lbl_batch_preview.pack(fill="x", pady=(0, 8))

        b_sub = ctk.CTkFrame(sidebar, fg_color="transparent")
        b_sub.pack(fill="x", pady=(0, 10))
        b_sub.columnconfigure(0, weight=3)
        b_sub.columnconfigure(1, weight=1)

        self.btn_batch = ctk.CTkButton(
            b_sub, text="Start Batch", command=self.process_folder,
            fg_color=C["blue"], hover_color=C["blue_hover"],
            font=ctk.CTkFont(size=11, weight="bold"), height=34, corner_radius=6,
        )
        self.btn_batch.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_cancel_batch = ctk.CTkButton(
            b_sub, text="Batal", command=self.cancel_batch,
            fg_color=C["border"], hover_color=C["red_hover"],
            font=ctk.CTkFont(size=11, weight="bold"), height=34, corner_radius=6,
            state="disabled",
        )
        self.btn_cancel_batch.grid(row=0, column=1, sticky="ew")

        # Visual Developer Credit Footer (UI attribution only)
        lbl_credit = ctk.CTkLabel(
            sidebar, text=DEVELOPER_CREDIT,
            font=ctk.CTkFont(size=10, weight="bold"), text_color=C["dim"],
            justify="center",
        )
        lbl_credit.pack(anchor="center", pady=(16, 4))

        # ════════════════════════════════════════════════════
        #  RIGHT PREVIEW AREA (MAXIMIZED 75-80% SPACE)
        # ════════════════════════════════════════════════════
        preview_area = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        preview_area.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        preview_area.rowconfigure(0, weight=1)
        preview_area.columnconfigure(0, weight=1)

        self.preview_canvas = SplitSliderPreview(preview_area)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")

        self.spinner_frame = ctk.CTkFrame(preview_area, fg_color=C["card_alt"], corner_radius=10)
        self.spinner = LoadingSpinner(self.spinner_frame, size=46, color=C["accent"], bg_color=C["card_alt"])
        self.spinner.pack(pady=(20, 8), padx=40)
        self.spinner_label = ctk.CTkLabel(
            self.spinner_frame, text="Memproses gambar...",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=C["accent"]
        )
        self.spinner_label.pack(pady=(0, 20), padx=40)

        # Compact Bottom Status Bar
        status_bar = ctk.CTkFrame(preview_area, fg_color="transparent")
        status_bar.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self.progress = ctk.CTkProgressBar(
            status_bar, fg_color=C["border"], progress_color=C["accent"],
            height=4, corner_radius=2,
        )
        self.progress.pack(fill="x", pady=(0, 4))
        self.progress.set(0)

        ctk.CTkLabel(
            status_bar, textvariable=self.status_text,
            font=ctk.CTkFont(size=11), text_color=C["dim"], anchor="w",
        ).pack(fill="x")

    # ───────────────────────────────────────
    #  Tool Switch & UI State Management
    # ───────────────────────────────────────

    def _switch_tool(self, tool):
        if self._processing:
            messagebox.showwarning(APP_NAME, "Harap tunggu hingga proses saat ini selesai.")
            return

        if self.active_tool == tool:
            return

        # Release previous heavy engine from RAM
        if self.active_tool == TOOL_REMOVE_BG:
            global _rembg_session, _rembg_model_name
            if _rembg_session is not None:
                old_session = _rembg_session
                _rembg_session = None
                _rembg_model_name = None
                try:
                    del old_session
                    gc.collect()
                except Exception:
                    pass

        self.active_tool = tool

        if tool == TOOL_REMOVE_BG:
            self.btn_tool_rmbg.configure(fg_color=C["accent"], text_color=C["text"])
            self.btn_tool_upscale.configure(fg_color="transparent", text_color=C["dim"])
            self.frame_upscale_settings.pack_forget()
            self.frame_rmbg_settings.pack(fill="x", before=self._lbl_single_section)
            self.status_text.set(f"Alat aktif: Hapus Background. [RAM: {get_process_memory_mb()} MB]")
        else:
            self.btn_tool_upscale.configure(fg_color=C["accent"], text_color=C["text"])
            self.btn_tool_rmbg.configure(fg_color="transparent", text_color=C["dim"])
            self.frame_rmbg_settings.pack_forget()
            self.frame_upscale_settings.pack(fill="x", before=self._lbl_single_section)
            self.btn_repreview.configure(text="Proses Upscale")
            self.status_text.set(f"Alat aktif: Upscale ({self.scale_var.get()}x). [RAM: {get_process_memory_mb()} MB]")

    def _set_scale(self, scale):
        self.scale_var.set(scale)
        if scale == 2:
            self.btn_scale_2x.configure(fg_color=C["accent"], text_color=C["text"])
            self.btn_scale_4x.configure(fg_color="transparent", text_color=C["dim"])
        else:
            self.btn_scale_4x.configure(fg_color=C["accent"], text_color=C["text"])
            self.btn_scale_2x.configure(fg_color="transparent", text_color=C["dim"])

    def _section_label(self, parent, text):
        lbl = ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=10, weight="bold"), text_color=C["dim"],
        )
        lbl.pack(anchor="w", pady=(8, 4))
        return lbl

    def _on_threshold(self, v):
        v = round(float(v)); self.threshold_var.set(v); self._lbl_white_threshold.configure(text=str(v))

    def _on_fringe(self, v):
        v = round(float(v)); self.fringe_var.set(v); self._lbl_fringe_cleanup.configure(text=str(v))

    def _choose_output(self):
        folder = filedialog.askdirectory(title="Pilih folder output batch")
        if folder:
            self.output_dir.set(folder)

    def _update_batch_preview(self, _=None):
        name = sanitize_filename(self.batch_name_var.get())
        self.lbl_batch_preview.configure(
            text=f"Contoh: {name}-1.png, {name}-2.png..."
        )

    def _on_mode_change(self, _=None):
        self._toggle_flood_settings()
        self._update_mode_desc()

    def _update_mode_desc(self):
        mode = self.mode_var.get()
        desc = MODE_DESC_MAP.get(mode, "")
        self.mode_desc.configure(text=desc)

    def _toggle_flood_settings(self):
        is_flood = self.mode_var.get() == MODE_WHITE
        if is_flood:
            self.lbl_refine.pack_forget()
            self.refine_dropdown.pack_forget()
            self.adv_section.pack(fill="x", pady=(0, 8))
        else:
            self.lbl_refine.pack(anchor="w", pady=(8, 4))
            self.refine_dropdown.pack(fill="x", pady=(0, 8))

    def _get_refinement_params(self):
        r = self.refine_var.get()
        if r == REFINE_SOFT:
            return 2, False, 0
        elif r == REFINE_ALPHA_MATTE:
            return 0, True, 0
        else:
            return 0, False, 0  # Original mode: edge_smooth=0, alpha_matting=False, erode_size=0

    def _update_button_states(self):
        """Reconstruct UI button states based on actual app state."""
        if self._processing:
            self.btn_pick.configure(state="disabled")
            self.btn_batch.configure(state="disabled")
            self.btn_repreview.configure(state="disabled")
            self.btn_save.configure(state="disabled", fg_color=C["border"], text_color=C["text"])
        else:
            self.btn_pick.configure(state="normal")
            self.btn_batch.configure(state="normal")
            self.btn_cancel_batch.configure(state="disabled", fg_color=C["border"])

            if self._original is not None:
                self.btn_repreview.configure(state="normal")
            else:
                self.btn_repreview.configure(state="disabled")

            if self._result is not None:
                self.btn_save.configure(
                    state="normal", fg_color=C["green"],
                    hover_color=C["green_dark"], text_color="#000000",
                )
            else:
                self.btn_save.configure(
                    state="disabled", fg_color=C["border"], text_color=C["text"],
                )

    def _set_buttons(self, state):
        """Deprecated helper routing to _update_button_states."""
        self._update_button_states()

    def _switch_tool(self, tool):
        if self._processing:
            messagebox.showwarning(APP_NAME, "Harap tunggu hingga proses saat ini selesai.")
            return

        if self.active_tool == tool:
            return

        # Release previous heavy engine from RAM
        if self.active_tool == TOOL_REMOVE_BG:
            global _rembg_session, _rembg_model_name
            if _rembg_session is not None:
                old_session = _rembg_session
                _rembg_session = None
                _rembg_model_name = None
                try:
                    del old_session
                    gc.collect()
                except Exception:
                    pass

        self.active_tool = tool
        self._result = None

        if tool == TOOL_REMOVE_BG:
            self.btn_tool_rmbg.configure(fg_color=C["accent"], text_color=C["text"])
            self.btn_tool_upscale.configure(fg_color="transparent", text_color=C["dim"])
            self.frame_upscale_settings.pack_forget()
            self.frame_rmbg_settings.pack(fill="x", before=self._lbl_single_section)
            self.btn_repreview.configure(text="Preview Ulang")
            self.status_text.set(f"Alat aktif: Hapus Background. [RAM: {get_process_memory_mb()} MB]")
        else:
            self.btn_tool_upscale.configure(fg_color=C["accent"], text_color=C["text"])
            self.btn_tool_rmbg.configure(fg_color="transparent", text_color=C["dim"])
            self.frame_rmbg_settings.pack_forget()
            self.frame_upscale_settings.pack(fill="x", before=self._lbl_single_section)
            self.btn_repreview.configure(text="Proses Upscale")
            self.status_text.set(f"Alat aktif: Upscale ({self.scale_var.get()}x). [RAM: {get_process_memory_mb()} MB]")

        # Retain original image in preview if available
        if self._original is not None:
            self.preview_canvas.set_images(self._original, None)

        self._update_button_states()

    # ───────────────────────────────────────
    #  Single-Image Processing Workflow
    # ───────────────────────────────────────

    def load_and_process(self):
        src = filedialog.askopenfilename(
            title="Pilih gambar produk",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All", "*.*")],
        )
        if not src:
            return
        self._src_path = src
        self._original = None
        self._result = None

        try:
            with Image.open(self._src_path) as img:
                has_alpha = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
                self._original = img.convert("RGBA") if has_alpha else img.convert("RGB")
                self._original_meta = metadata_for_save(img)

            # Immediately show original image in preview canvas BEFORE worker processing
            self.preview_canvas.set_images(self._original, None)
            self._update_button_states()

            orig_sz = self._original.size
            if self.active_tool == TOOL_UPSCALE:
                self.status_text.set(
                    f"Gambar dimuat: {orig_sz[0]}×{orig_sz[1]} px. "
                    f"Pilih skala lalu klik 'Proses Upscale'. [RAM: {get_process_memory_mb()} MB]"
                )
            else:
                self.status_text.set(
                    f"Gambar dimuat: {orig_sz[0]}×{orig_sz[1]} px. Menghapus background... [RAM: {get_process_memory_mb()} MB]"
                )
        except Exception as e:
            self.status_text.set(f"Gagal memuat gambar: {e}")
            messagebox.showerror(APP_NAME, f"Gagal memuat gambar:\n{e}")
            return

        if self.active_tool == TOOL_REMOVE_BG:
            self._do_process()

    def repreview(self):
        if self._original is None and self._src_path:
            try:
                with Image.open(self._src_path) as img:
                    has_alpha = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
                    self._original = img.convert("RGBA") if has_alpha else img.convert("RGB")
                    self._original_meta = metadata_for_save(img)
                self.preview_canvas.set_images(self._original, None)
            except Exception:
                pass
        if self._original is None:
            return
        self._do_process()

    def _do_process(self):
        if self._processing or self._original is None:
            return
        self._processing = True
        self._update_button_states()

        tool = self.active_tool
        mode = self.mode_var.get()
        scale = self.scale_var.get()
        is_ai = mode != MODE_WHITE and tool == TOOL_REMOVE_BG
        internal_model = MODE_MAP.get(mode, "birefnet-massive")

        if is_ai and not is_model_downloaded(internal_model):
            ans = messagebox.askyesno(
                APP_NAME,
                f"Model AI '{internal_model}' belum terinstal di komputer.\n\n"
                f"Apakah kamu ingin mengunduh model ini sekarang?\n"
                f"(Ukuran file ±150–250 MB, mengunduh via internet).",
            )
            if not ans:
                self.status_text.set("Pengunduhan model dibatalkan pengguna.")
                self._processing = False
                self._update_button_states()
                self.progress.set(0)
                return

        self.spinner_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.spinner.start()

        if tool == TOOL_UPSCALE:
            self.spinner_label.configure(text=f"Memperbesar foto ({scale}x)...")
            self.status_text.set(f"Memperbesar foto ({scale}x)... [RAM: {get_process_memory_mb()} MB]")
        else:
            self.spinner_label.configure(text="Menghapus background...")
            self.status_text.set(f"Menghapus background ({mode})... [RAM: {get_process_memory_mb()} MB]")

        self.progress.set(0.15)

        th = self.threshold_var.get()
        fr = self.fringe_var.get()
        ag = self.aggressive_var.get()
        es, am, er = self._get_refinement_params()

        def _status_cb(msg):
            self.after(0, lambda m=msg: self.status_text.set(f"{m} [RAM: {get_process_memory_mb()} MB]"))
            self.after(0, lambda: self.progress.configure(
                progress_color=C["purple"] if "⬇" in msg else C["accent"]
            ))
            self.after(0, lambda: self.progress.set(0.3))

        def _worker():
            try:
                self.after(0, lambda: self.progress.set(0.4))

                if tool == TOOL_UPSCALE:
                    result = upscale_image_alpha_safe(self._original, scale=scale, status_cb=_status_cb)
                else:
                    if is_ai:
                        result = ai_remove_bg(
                            self._original, edge_smooth=es, erode_size=er,
                            model_name=internal_model, alpha_matting=am,
                            status_cb=_status_cb,
                        )
                    else:
                        result = flood_remove_bg(self._original, th, fr, es, ag)

                self._result = result
                self.after(0, lambda: self._on_process_ok())
            except Exception as e:
                err_msg = str(e)
                if "allocate" in err_msg.lower():
                    err_msg = "Memori RAM tidak cukup untuk Alpha Matting. Silakan gunakan mode ketajaman Original."
                self.after(0, lambda err=err_msg: self._on_process_err(err))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_process_ok(self):
        self.spinner.stop()
        self.spinner_frame.place_forget()

        self._processing = False
        self.progress.set(1.0)
        self.progress.configure(progress_color=C["accent"])

        self.preview_canvas.set_images(self._original, self._result)
        self._update_button_states()

        orig_sz = self._original.size
        res_sz = self._result.size
        ram_mb = get_process_memory_mb()

        if self.active_tool == TOOL_UPSCALE:
            self.status_text.set(
                f"[Upscale {self.scale_var.get()}x] Selesai: {orig_sz[0]}×{orig_sz[1]} → {res_sz[0]}×{res_sz[1]} px. "
                f"[RAM: {ram_mb} MB] → Klik 'Simpan PNG'."
            )
        else:
            self.status_text.set(
                f"[{self.mode_var.get()}] Selesai: {res_sz[0]}×{res_sz[1]} px. "
                f"[RAM: {ram_mb} MB] → Klik 'Simpan PNG'."
            )

    def _on_process_err(self, err):
        self.spinner.stop()
        self.spinner_frame.place_forget()

        self._processing = False
        self.progress.set(0)
        self.progress.configure(progress_color=C["accent"])

        # Preserve original image preview on error
        if self._original is not None:
            self.preview_canvas.set_images(self._original, None)

        self._update_button_states()
        self.status_text.set(f"Gagal memproses: {err}")
        messagebox.showerror(APP_NAME, f"Gagal memproses gambar:\n\n{err}")

    def save_result(self):
        if self._result is None:
            return
        stem = Path(self._src_path).stem if self._src_path else "output"
        suffix = f"_upscale_{self.scale_var.get()}x.png" if self.active_tool == TOOL_UPSCALE else "_transparent.png"

        dst = filedialog.asksaveasfilename(
            title="Simpan hasil PNG", defaultextension=".png",
            initialfile=f"{stem}{suffix}",
            filetypes=[("PNG Transparan", "*.png")],
        )
        if not dst:
            return
        try:
            try:
                self._result.save(dst, format="PNG", optimize=False, **self._original_meta)
            except Exception:
                self._result.save(dst, format="PNG", optimize=False)

            with Image.open(dst) as check:
                sz = check.size
                res_sz = self._result.size
                if sz != res_sz:
                    raise RuntimeError(f"Resolusi tersimpan tidak cocok: {res_sz} -> {sz}")

            self.status_text.set(f"Disimpan: {sz[0]}×{sz[1]} px → {Path(dst).name} [RAM: {get_process_memory_mb()} MB]")
            messagebox.showinfo(
                APP_NAME,
                f"Tersimpan!\n\nResolusi Output: {sz[0]}×{sz[1]} px\n"
                f"Lokasi File: {dst}\n\nBuilt by Bima Chakti.",
            )
        except Exception as e:
            self.status_text.set(f"Error simpan: {e}")
            messagebox.showerror(APP_NAME, f"Gagal menyimpan file:\n{e}")

    # ───────────────────────────────────────
    #  Batch Workflow & Collision Avoidance
    # ───────────────────────────────────────

    def _get_next_sequence_name(self, out_dir, base_name, start_idx=1):
        sanitized = sanitize_filename(base_name)
        idx = start_idx
        while True:
            candidate = out_dir / f"{sanitized}-{idx}.png"
            if not candidate.exists():
                return candidate, idx
            idx += 1

    def cancel_batch(self):
        if self._processing:
            self._batch_cancelled = True
            self.status_text.set("Membatalkan batch... (menunggu gambar saat ini selesai)")
            self.btn_cancel_batch.configure(state="disabled")

    def process_folder(self):
        src_dir = filedialog.askdirectory(title="Pilih folder sumber gambar")
        if not src_dir:
            return
        out_dir = self.output_dir.get().strip()
        if not out_dir:
            out_dir = filedialog.askdirectory(title="Pilih folder output batch")
            if not out_dir:
                return
            self.output_dir.set(out_dir)

        src_dir, out_dir = Path(src_dir), Path(out_dir)
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        files = sorted(p for p in src_dir.iterdir() if p.is_file() and p.suffix.lower() in exts)
        if not files:
            messagebox.showwarning(APP_NAME, "Tidak ada gambar yang didukung di folder tersebut.")
            return

        tool = self.active_tool
        mode = self.mode_var.get()
        scale = self.scale_var.get()
        internal_model = MODE_MAP.get(mode, "birefnet-massive")
        is_ai = mode != MODE_WHITE and tool == TOOL_REMOVE_BG

        if is_ai and not is_model_downloaded(internal_model):
            ans = messagebox.askyesno(
                APP_NAME,
                f"Model AI '{internal_model}' belum terinstal di komputer.\n\n"
                f"Apakah kamu ingin mengunduh model ini sekarang?\n"
                f"(Ukuran file ±150–250 MB, mengunduh via internet).",
            )
            if not ans:
                self.status_text.set("Pengunduhan model dibatalkan pengguna.")
                return

        th, fr, ag = self.threshold_var.get(), self.fringe_var.get(), self.aggressive_var.get()
        es, am, er = self._get_refinement_params()
        base_batch_name = self.batch_name_var.get()

        total = len(files)
        self._processing = True
        self._batch_cancelled = False
        self._update_button_states()
        self.btn_cancel_batch.configure(state="normal", fg_color=C["red"])

        def _batch():
            ok, errors = 0, []
            current_seq = 1
            for idx, src in enumerate(files, 1):
                if self._batch_cancelled:
                    break

                dst_path, next_seq = self._get_next_sequence_name(out_dir, base_batch_name, current_seq)
                current_seq = next_seq + 1

                self.after(0, lambda i=idx, n=src.name, d=dst_path.name: self._batch_tick(i, total, n, d))
                try:
                    process_file(
                        src, dst_path, mode, th, fr, es, ag,
                        model_name=internal_model, alpha_matting=am, erode_size=er,
                        tool=tool, scale=scale,
                    )
                    ok += 1
                except Exception as e:
                    errors.append(f"{src.name}: {e}")

            self.after(0, lambda: self._batch_done(ok, total, errors, cancelled=self._batch_cancelled))

        threading.Thread(target=_batch, daemon=True).start()

    def _batch_tick(self, idx, total, src_name, dst_name):
        self.status_text.set(
            f"Memproses {idx}/{total}: {src_name} → {dst_name} [RAM: {get_process_memory_mb()} MB]"
        )
        self.progress.set(idx / total)

    def _batch_done(self, ok, total, errors, cancelled=False):
        self.progress.set(0)
        self._processing = False
        self._update_button_states()
        self.btn_cancel_batch.configure(state="disabled", fg_color=C["border"])

        ram_mb = get_process_memory_mb()
        if cancelled:
            msg = f"Batch dibatalkan. {ok} dari {total} gambar selesai diproses. [RAM: {ram_mb} MB]"
            self.status_text.set(msg)
            messagebox.showinfo(APP_NAME, msg)
        elif errors:
            self.status_text.set(f"Selesai {ok}/{total}. Ada {len(errors)} error. [RAM: {ram_mb} MB]")
            messagebox.showwarning(
                APP_NAME,
                f"Selesai: {ok}/{total} file.\nAda error pada {len(errors)} file:\n\n"
                + "\n".join(errors[:10]),
            )
        else:
            self.status_text.set(f"Selesai: {ok} file diproses. [RAM: {ram_mb} MB]")
            messagebox.showinfo(
                APP_NAME,
                f"Selesai memproses {ok} file!\n\n"
                f"Hasil tersimpan di folder tujuan.\nBuilt by Bima Chakti.",
            )


# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = WhiteFloodApp()
    app.withdraw()
    splash = show_splash(app)

    def _reveal():
        try:
            splash.destroy()
        except Exception:
            pass
        app.deiconify()

    app.after(800, _reveal)
    app.mainloop()
