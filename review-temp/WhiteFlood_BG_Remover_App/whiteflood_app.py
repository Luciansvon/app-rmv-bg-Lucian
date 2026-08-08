"""
WhiteFlood BG Remover & Upscaler v2.5.0
Built by Bima Chakti © 2026 Bima Chakti
Aplikasi Windows Desktop untuk Foto Produk Furnitur (PNG Transparan).
Dual Tools: Remove Background (Dimensi 100% Presisi) & Upscale (2x/4x/8x via Upscayl NCNN).
Layout: Upscayl-Style Interactive Split-Slider Preview + Narrow Sidebar (~290px).
"""

import os
import sys
import gc
import threading
import importlib.util
import re
import math
import time
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
DEVELOPER_CREDIT = "Built by Bima Chakti\n\u00a9 2026 Bima Chakti"

TOOL_REMOVE_BG = "remove_bg"
TOOL_UPSCALE = "upscale"
UPSCAYL_MODEL = "realesrgan-x4plus"
UPSCAYL_AI_MAX_SCALE = 4

MODE_FURNITURE = "Furniture Quality"
MODE_FAST = "Fast"
MODE_PERSON = "Person"
MODE_HIGH_DETAIL = "High Detail"
MODE_WHITE = "White Background"

MODE_MAP = {
    MODE_FURNITURE: "birefnet-massive",
    MODE_FAST: "birefnet-general",
    MODE_PERSON: "birefnet-portrait",
    MODE_HIGH_DETAIL: "birefnet-hrsod",
}

MODE_DESC_MAP = {
    MODE_FURNITURE: "Rekomendasi utama untuk foto furnitur, kayu, dan katalog.",
    MODE_FAST: "Proses lebih cepat untuk gambar biasa.",
    MODE_PERSON: "Untuk foto orang, pakaian, dan rambut.",
    MODE_HIGH_DETAIL: "Untuk resolusi tinggi dan ukiran halus.",
    MODE_WHITE: "Lokal tanpa AI untuk background putih atau abu-abu polos.",
}

REFINE_ORIGINAL = "Original (Rekomendasi)"
REFINE_SOFT = "Soft (Pinggiran Halus)"
REFINE_ALPHA_MATTE = "Alpha Matte (Deteksi Rambut)"

C = {
    "bg":           "#0d1014",
    "card":         "#151a20",
    "card_alt":     "#10151a",
    "border":       "#283039",
    "accent":       "#ef5b73",
    "accent_hover": "#d94d64",
    "blue":         "#27323d",
    "blue_hover":   "#354451",
    "text":         "#f3f1ed",
    "dim":          "#8f9aa3",
    "green":        "#61bd9b",
    "green_dark":   "#469579",
    "purple":       "#d39a78",
    "purple_hover": "#b77e61",
    "red":          "#d85e6a",
    "red_hover":    "#b94b57",
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
        splash, text="WHITEFLOOD",
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
    """Cached split-slider preview that keeps mouse drag work lightweight."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["card_alt"], highlightthickness=0, **kwargs)
        self.slider_pos = 0.5
        self.original_img = None
        self.result_img = None
        self._dragging = False
        self._display_original = None
        self._display_result = None
        self._display_size = None
        self._display_offset = (0, 0)
        self._redraw_job = None
        self._resize_job = None
        self._comp_tk = None

        self.bind("<Configure>", self._on_resize)
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    def set_images(self, original, result):
        self.original_img = original
        self.result_img = result
        self._invalidate_display_cache()
        self.redraw()

    def _on_resize(self, event):
        if self._resize_job is None:
            self._resize_job = self.after(60, self._flush_resize)

    def _flush_resize(self):
        self._resize_job = None
        self._invalidate_display_cache()
        self.redraw()

    def _on_click(self, event):
        self._dragging = True
        self._update_slider_from_mouse(event.x)

    def _on_drag(self, event):
        if self._dragging:
            self._update_slider_from_mouse(event.x)

    def _on_release(self, event):
        self._dragging = False
        self._schedule_redraw(delay=0)

    def _update_slider_from_mouse(self, mouse_x):
        w = self.winfo_width()
        if w > 20:
            self.slider_pos = max(0.02, min(0.98, mouse_x / float(w)))
            self._schedule_redraw()

    def _schedule_redraw(self, delay=16):
        if self._redraw_job is None:
            self._redraw_job = self.after(delay, self._flush_redraw)

    def _flush_redraw(self):
        self._redraw_job = None
        self.redraw()

    def _invalidate_display_cache(self):
        self._display_original = None
        self._display_result = None
        self._display_size = None
        self._display_offset = (0, 0)

    def _prepare_display_cache(self, width, height):
        if not self.original_img or width < 30 or height < 30:
            return False

        ref_img = self.result_img if self.result_img else self.original_img
        ref_w, ref_h = ref_img.size
        scale = min(width / ref_w, height / ref_h)
        disp_w = max(1, int(ref_w * scale))
        disp_h = max(1, int(ref_h * scale))
        offset_x = (width - disp_w) // 2
        offset_y = (height - disp_h) // 2

        original_display = self.original_img.resize((disp_w, disp_h), Image.LANCZOS)
        if original_display.mode != "RGBA":
            original_display = original_display.convert("RGBA")

        if self.result_img:
            result_display = self.result_img.resize((disp_w, disp_h), Image.LANCZOS)
            if result_display.mode != "RGBA":
                result_display = result_display.convert("RGBA")
            checker = make_checkerboard(disp_w, disp_h, cell=10)
            checker.paste(result_display, (0, 0), result_display)
            result_display = checker
        else:
            result_display = original_display

        self._display_original = original_display
        self._display_result = result_display
        self._display_size = (disp_w, disp_h)
        self._display_offset = (offset_x, offset_y)
        return True

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

        if self._display_size is None:
            if not self._prepare_display_cache(w, h):
                return

        disp_w, disp_h = self._display_size
        offset_x, offset_y = self._display_offset
        orig_disp = self._display_original
        res_disp = self._display_result

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
        self.create_rectangle(line_x - 20, handle_y - 18, line_x + 20, handle_y + 18, fill=C["accent"], outline=C["text"], width=1)
        self.create_text(line_x, handle_y, text="DRAG", fill="#ffffff", font=("Segoe UI", 8, "bold"))

        self.create_rectangle(offset_x + 10, offset_y + 10, offset_x + 108, offset_y + 32, fill="#12171c", outline=C["border"], width=1)
        self.create_text(offset_x + 59, offset_y + 21, text="ASLI", fill="#ffffff", font=("Segoe UI", 9, "bold"))

        self.create_rectangle(offset_x + disp_w - 108, offset_y + 10, offset_x + disp_w - 10, offset_y + 32, fill="#12171c", outline=C["border"], width=1)
        self.create_text(offset_x + disp_w - 59, offset_y + 21, text="HASIL", fill="#ffffff", font=("Segoe UI", 9, "bold"))

    def destroy(self):
        for job in (self._redraw_job, self._resize_job):
            if job is not None:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
        super().destroy()


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


class _ModelDownloadProgress:
    """Small pooch progress adapter that reports download bytes to the UI."""

    def __init__(self, callback, model_name):
        self.callback = callback
        self.model_name = model_name
        self.total = 0
        self.downloaded = 0
        self._last_percent = -1
        self._last_emit_at = 0.0
        self._lock = threading.Lock()

    def _emit(self, force=False):
        if not self.callback or self.total <= 0:
            return

        percent = min(100, max(0, int((self.downloaded / self.total) * 100)))
        now = time.monotonic()
        if not force and percent == self._last_percent and now - self._last_emit_at < 0.15:
            return
        if not force and now - self._last_emit_at < 0.15:
            return

        self._last_percent = percent
        self._last_emit_at = now
        self.callback({
            "kind": "model_download",
            "model": self.model_name,
            "percent": percent,
            "downloaded": self.downloaded,
            "total": self.total,
        })

    def update(self, amount):
        with self._lock:
            self.downloaded = min(
                self.total,
                self.downloaded + max(0, int(amount)),
            )
            self._emit()

    def reset(self):
        with self._lock:
            self.downloaded = 0
            self._emit(force=True)

    def close(self):
        with self._lock:
            if self.total > 0:
                self.downloaded = self.total
            self._emit(force=True)


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
    import pooch

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
                    status_cb(f"Mencoba ulang unduhan model '{model_name}' ({attempt}/{max_retries})")
                else:
                    status_cb(f"Menyiapkan unduhan model '{model_name}'")

            original_retrieve = pooch.retrieve

            def retrieve_with_ui_progress(*args, **kwargs):
                if status_cb and kwargs.get("progressbar") is True:
                    kwargs = dict(kwargs)
                    kwargs["progressbar"] = _ModelDownloadProgress(status_cb, model_name)
                return original_retrieve(*args, **kwargs)

            pooch.retrieve = retrieve_with_ui_progress
            try:
                _rembg_session = new_session(model_name, sess_opts=opts)
            finally:
                pooch.retrieve = original_retrieve

            _rembg_model_name = model_name

            if status_cb:
                status_cb(f"Model '{model_name}' siap")

            return _rembg_session
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(1.5)

    err_msg = str(last_err)
    if any(k in err_msg for k in ("Connection", "RemoteDisconnected", "time out", "timed out", "Disconnected")):
        raise RuntimeError(
            f"Koneksi internet terputus saat mengunduh model '{model_name}'.\n\n"
            f"Silakan pastikan koneksi internet stabil lalu klik 'Proses Ulang' untuk mencoba lagi."
        )
    raise RuntimeError(f"Gagal memuat model '{model_name}': {err_msg}")


def _get_realesrgan_paths():
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent

    engine_dir = base / "realesrgan"
    exe_path = engine_dir / "realesrgan-ncnn-vulkan.exe"
    models_dir = engine_dir / "models"

    if not exe_path.is_file():
        import shutil as _shutil
        found = _shutil.which("realesrgan-ncnn-vulkan")
        if found:
            exe_path = Path(found)
            engine_dir = exe_path.parent
            candidate_models = engine_dir / "models"
            if candidate_models.is_dir():
                models_dir = candidate_models

    if not exe_path.is_file():
        raise RuntimeError(
            "Engine Real-ESRGAN tidak ditemukan.\n\n"
            f"Dicari di:\n{engine_dir / 'realesrgan-ncnn-vulkan.exe'}"
        )

    if not models_dir.is_dir():
        raise RuntimeError(
            "Folder model Real-ESRGAN tidak ditemukan.\n\n"
            f"Dicari di:\n{models_dir}"
        )

    required = [
        models_dir / f"{UPSCAYL_MODEL}.param",
        models_dir / f"{UPSCAYL_MODEL}.bin",
    ]
    missing = [p.name for p in required if not p.is_file()]
    if missing:
        raise RuntimeError(
            "Model Real-ESRGAN tidak lengkap:\n"
            + "\n".join(missing)
        )

    return engine_dir, exe_path, models_dir


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
#  Alpha-Safe Upscayl NCNN Vulkan Upscaler Engine (2x / 4x / 8x)
# ═══════════════════════════════════════════════════════════

def upscale_image_alpha_safe(img, scale=2, status_cb=None):
    """Upscale through Upscayl while preserving PNG alpha.

    8x uses the supported 4x AI pass, then a Lanczos 2x resize for the
    final output size.
    """
    if scale not in (2, 4, 8):
        raise ValueError("Scale hanya boleh 2x, 4x, atau 8x.")

    original_size = img.size
    new_size = (original_size[0] * scale, original_size[1] * scale)
    ai_scale = UPSCAYL_AI_MAX_SCALE if scale == 8 else scale
    ai_size = (original_size[0] * ai_scale, original_size[1] * ai_scale)

    engine_dir, exe_path, models_dir = _get_realesrgan_paths()

    if status_cb:
        status_cb(0.0)

    import tempfile
    import subprocess

    has_alpha = (
        img.mode in ("RGBA", "LA")
        or (img.mode == "P" and "transparency" in img.info)
    )

    with tempfile.TemporaryDirectory(prefix="whiteflood_upscale_") as tmpdir:
        tmpdir = Path(tmpdir)
        input_path = tmpdir / "input.png"
        output_path = tmpdir / "output.png"

        if has_alpha:
            save_img = img.convert("RGBA")
        else:
            save_img = img.convert("RGB")

        save_img.save(input_path, format="PNG", optimize=False)

        cmd = [
            str(exe_path),
            "-i", str(input_path.resolve()),
            "-o", str(output_path.resolve()),
            "-m", str(models_dir.resolve()),
            "-n", UPSCAYL_MODEL,
            "-s", str(ai_scale),
            "-f", "png",
        ]

        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(engine_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )

            progress_pattern = re.compile(r'(\d+(?:\.\d+)?)%')
            stderr_logs = []

            for line in proc.stderr:
                stderr_logs.append(line)
                match = progress_pattern.search(line)
                if match and status_cb:
                    pct = float(match.group(1))
                    status_cb(pct if scale != 8 else min(95.0, pct * 0.95))

            proc.wait()
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "Real-ESRGAN tidak merespons. Proses dihentikan."
            )
        except OSError as e:
            raise RuntimeError(
                "Real-ESRGAN gagal dijalankan.\n\n"
                f"{e}"
            )

        if proc.returncode != 0 or not output_path.is_file():
            details = "".join(stderr_logs).strip() or f"Exit code {proc.returncode}"
            low = details.lower()

            if "vulkan" in low or "gpu" in low or "device" in low:
                raise RuntimeError(
                    "Real-ESRGAN gagal mengakses GPU/Vulkan.\n\n"
                    "Pastikan driver GPU mendukung Vulkan.\n\n"
                    f"Detail:\n{details}"
                )

            raise RuntimeError(
                "Real-ESRGAN gagal memproses gambar.\n\n"
                f"Detail:\n{details}"
            )

        if output_path.stat().st_size <= 0:
            raise RuntimeError("File output Real-ESRGAN kosong.")

        with Image.open(output_path) as out_img:
            raw_result = out_img.copy()

        result = raw_result.convert("RGBA" if has_alpha else "RGB")
        del raw_result

        if result.size != ai_size:
            raise RuntimeError(
                f"Internal error: Ukuran Upscayl mismatch ({result.size} vs {ai_size})"
            )

        if scale == 8:
            if status_cb:
                status_cb(96.0)
            resized = result.resize(new_size, Image.LANCZOS)
            del result
            result = resized
            if status_cb:
                status_cb(100.0)

        if result.size != new_size:
            raise RuntimeError(
                f"Internal error: Ukuran output mismatch ({result.size} vs {new_size})"
            )

    gc.collect()
    return result


def process_file(src, dst, mode, threshold, fringe, edge_smooth, aggressive,
                 model_name="birefnet-massive", alpha_matting=False, erode_size=0,
                 tool=TOOL_REMOVE_BG, scale=2, status_cb=None):
    """Process a single file preserving rules for Remove BG or Upscale."""
    src, dst = Path(src), Path(dst)
    with Image.open(src) as img:
        original_size = img.size
        meta = metadata_for_save(img)

        if tool == TOOL_UPSCALE:
            result = upscale_image_alpha_safe(img, scale=scale, status_cb=status_cb)
            expected_size = (original_size[0] * scale, original_size[1] * scale)
        else:
            if mode == MODE_WHITE:
                result = flood_remove_bg(img, threshold, fringe, edge_smooth, aggressive)
            else:
                result = ai_remove_bg(
                    img, edge_smooth=edge_smooth, erode_size=erode_size,
                    model_name=model_name, alpha_matting=alpha_matting,
                    status_cb=status_cb,
                )
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
        self.preview_file_var = ctk.StringVar(value="Belum ada file")
        self.preview_state_var = ctk.StringVar(value="SIAP  /  LOKAL")
        self.progress_phase_var = ctk.StringVar(value="Belum ada proses")
        self.progress_percent_var = ctk.StringVar(value="0%")

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
        self.columnconfigure(0, weight=0, minsize=304)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ════════════════════════════════════════════════════
        #  LEFT SIDEBAR PANEL (~290px)
        # ════════════════════════════════════════════════════
        sidebar_bg = ctk.CTkFrame(self, width=304, fg_color=C["card"], corner_radius=0)
        sidebar_bg.grid(row=0, column=0, sticky="nsew")
        sidebar_bg.pack_propagate(False)

        sidebar = ctk.CTkScrollableFrame(
            sidebar_bg, fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["accent"],
        )
        sidebar.pack(fill="both", expand=True, padx=18, pady=18)

        # Header Title & Version
        tf = ctk.CTkFrame(sidebar, fg_color="transparent")
        tf.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            tf, text="WHITEFLOOD",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=C["accent"],
        ).pack(side="left")
        ctk.CTkLabel(
            tf, text=f"v{VERSION}",
            font=ctk.CTkFont(size=10), text_color=C["dim"],
        ).pack(side="left", padx=(6, 0), pady=(4, 0))

        ctk.CTkLabel(
            sidebar, text="Studio foto produk lokal",
            font=ctk.CTkFont(size=10), text_color=C["dim"], anchor="w",
        ).pack(fill="x", pady=(0, 12))

        # Tool Navigation Tabs (Remove BG vs Upscale)
        self._section_label(sidebar, "ALAT AKTIF")
        nav_f = ctk.CTkFrame(sidebar, fg_color=C["card_alt"], corner_radius=6)
        nav_f.pack(fill="x", pady=(0, 10))
        nav_f.columnconfigure((0, 1), weight=1)

        self.btn_tool_rmbg = ctk.CTkButton(
            nav_f, text="Hapus Background", command=lambda: self._switch_tool(TOOL_REMOVE_BG),
            fg_color=C["accent"], hover_color=C["accent_hover"],
            font=ctk.CTkFont(size=11, weight="bold"), height=34, corner_radius=7,
        )
        self.btn_tool_rmbg.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        self.btn_tool_upscale = ctk.CTkButton(
            nav_f, text="Upscale", command=lambda: self._switch_tool(TOOL_UPSCALE),
            fg_color="transparent", text_color=C["dim"], hover_color=C["border"],
            font=ctk.CTkFont(size=11, weight="bold"), height=34, corner_radius=7,
        )
        self.btn_tool_upscale.grid(row=0, column=1, sticky="ew", padx=2, pady=2)

        # ── Tool 1: Remove BG Settings Frame ────────────────
        self.frame_rmbg_settings = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.frame_rmbg_settings.pack(fill="x")

        self._section_label(self.frame_rmbg_settings, "MODE REMOVE BACKGROUND")
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

        self.lbl_refine = self._section_label(self.frame_rmbg_settings, "KONTROL TEPI")
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

        self._section_label(self.frame_upscale_settings, "SKALA UPSCALE")
        scale_f = ctk.CTkFrame(self.frame_upscale_settings, fg_color=C["card_alt"], corner_radius=6)
        scale_f.pack(fill="x", pady=(0, 8))
        scale_f.columnconfigure((0, 1, 2), weight=1)

        self.btn_scale_2x = ctk.CTkButton(
            scale_f, text="2x", command=lambda: self._set_scale(2),
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

        self.btn_scale_8x = ctk.CTkButton(
            scale_f, text="8x", command=lambda: self._set_scale(8),
            fg_color="transparent", text_color=C["dim"], hover_color=C["border"],
            font=ctk.CTkFont(size=11, weight="bold"), height=32, corner_radius=6,
        )
        self.btn_scale_8x.grid(row=0, column=2, sticky="ew", padx=2, pady=2)

        ctk.CTkLabel(
            self.frame_upscale_settings,
            text="PNG/RGBA tetap aman. 2x paling ringan. 8x memakai 4x AI lalu resize Lanczos 2x.",
            font=ctk.CTkFont(size=10), text_color=C["dim"], wraplength=260, justify="left",
        ).pack(anchor="w", pady=(0, 10))

        # Single Image Actions
        self._lbl_single_section = self._section_label(sidebar, "FILE & HASIL")

        self.file_state_label = ctk.CTkLabel(
            sidebar, text="Belum ada file dipilih",
            font=ctk.CTkFont(size=10), text_color=C["dim"], anchor="w",
        )
        self.file_state_label.pack(fill="x", pady=(0, 6))
        
        self.btn_pick = ctk.CTkButton(
            sidebar, text="Pilih Gambar", command=self.load_and_process,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold"), height=40, corner_radius=8,
        )
        self.btn_pick.pack(fill="x", pady=(0, 6))

        act_sub = ctk.CTkFrame(sidebar, fg_color="transparent")
        act_sub.pack(fill="x", pady=(0, 10))
        act_sub.columnconfigure((0, 1), weight=1)

        self.btn_repreview = ctk.CTkButton(
            act_sub, text="Proses Ulang", command=self.repreview,
            fg_color=C["blue"], hover_color=C["blue_hover"],
            font=ctk.CTkFont(size=11, weight="bold"), height=34, corner_radius=7,
            state="disabled",
        )
        self.btn_repreview.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        self.btn_save = ctk.CTkButton(
            act_sub, text="Simpan Hasil", command=self.save_result,
            fg_color=C["border"], hover_color=C["blue_hover"],
            font=ctk.CTkFont(size=11, weight="bold"), height=34, corner_radius=7,
            state="disabled",
        )
        self.btn_save.grid(row=0, column=1, sticky="ew", padx=(3, 0))

        # Batch Section
        self._section_label(sidebar, "BATCH FOLDER")

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
            b_sub, text="Mulai Batch", command=self.process_folder,
            fg_color=C["blue"], hover_color=C["blue_hover"],
            font=ctk.CTkFont(size=11, weight="bold"), height=36, corner_radius=7,
        )
        self.btn_batch.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_cancel_batch = ctk.CTkButton(
            b_sub, text="Batal", command=self.cancel_batch,
            fg_color=C["border"], hover_color=C["red_hover"],
            font=ctk.CTkFont(size=11, weight="bold"), height=36, corner_radius=7,
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
        preview_area.grid(row=0, column=1, sticky="nsew", padx=(14, 18), pady=14)
        preview_area.rowconfigure(1, weight=1)
        preview_area.columnconfigure(0, weight=1)

        preview_header = ctk.CTkFrame(preview_area, fg_color="transparent", height=34)
        preview_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        preview_header.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            preview_header, textvariable=self.preview_file_var,
            font=ctk.CTkFont(size=13, weight="bold"), text_color=C["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            preview_header, textvariable=self.preview_state_var,
            font=ctk.CTkFont(size=10, weight="bold"), text_color=C["dim"], anchor="e",
        ).grid(row=0, column=1, sticky="e")

        preview_shell = ctk.CTkFrame(
            preview_area, fg_color=C["card"], corner_radius=11,
            border_width=1, border_color=C["border"],
        )
        preview_shell.grid(row=1, column=0, sticky="nsew")
        preview_shell.rowconfigure(0, weight=1)
        preview_shell.columnconfigure(0, weight=1)

        self.preview_canvas = SplitSliderPreview(preview_shell)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        self.spinner_frame = ctk.CTkFrame(preview_shell, fg_color=C["card_alt"], corner_radius=10)
        self.spinner = LoadingSpinner(self.spinner_frame, size=46, color=C["accent"], bg_color=C["card_alt"])
        self.spinner.pack(pady=(20, 8), padx=40)
        self.spinner_label = ctk.CTkLabel(
            self.spinner_frame, text="Memproses gambar...",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=C["accent"]
        )
        self.spinner_label.pack(pady=(0, 20), padx=40)

        # Bottom status area keeps phase and percentage visible without a terminal.
        status_bar = ctk.CTkFrame(preview_area, fg_color=C["card"], corner_radius=8)
        status_bar.grid(row=2, column=0, sticky="ew", pady=(10, 0), padx=1)
        status_bar.columnconfigure(0, weight=1)

        progress_meta = ctk.CTkFrame(status_bar, fg_color="transparent")
        progress_meta.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 0))
        progress_meta.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            progress_meta, textvariable=self.progress_phase_var,
            font=ctk.CTkFont(size=10, weight="bold"), text_color=C["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            progress_meta, textvariable=self.progress_percent_var,
            font=ctk.CTkFont(size=10, weight="bold"), text_color=C["accent"], anchor="e",
        ).grid(row=0, column=1, sticky="e")

        self.progress = ctk.CTkProgressBar(
            status_bar, fg_color=C["border"], progress_color=C["accent"],
            height=4, corner_radius=2,
        )
        self.progress.grid(row=1, column=0, sticky="ew", padx=12, pady=(5, 4))
        self.progress.set(0)

        ctk.CTkLabel(
            status_bar, textvariable=self.status_text,
            font=ctk.CTkFont(size=10), text_color=C["dim"], anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 9))

    # ───────────────────────────────────────
    #  Tool Switch & UI State Management
    # ───────────────────────────────────────

    def _set_scale(self, scale):
        if scale not in (2, 4, 8):
            raise ValueError("Scale hanya boleh 2x, 4x, atau 8x.")
        self.scale_var.set(scale)
        for selected_scale, button in (
            (2, self.btn_scale_2x),
            (4, self.btn_scale_4x),
            (8, self.btn_scale_8x),
        ):
            is_active = selected_scale == scale
            button.configure(
                fg_color=C["accent"] if is_active else "transparent",
                text_color=C["text"] if is_active else C["dim"],
            )
        if self.active_tool == TOOL_UPSCALE:
            self.preview_state_var.set(f"SIAP  /  UPSCALE {scale}X")

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

    def _apply_status_event(self, event, tool, scale):
        """Render worker/download progress on the Tk main thread."""
        if isinstance(event, dict) and event.get("kind") == "model_download":
            model_name = event.get("model", "AI")
            percent = int(event.get("percent", 0))
            phase = f"Mengunduh model {model_name}"
            self.progress_phase_var.set(phase)
            self.progress_percent_var.set(f"{percent}%")
            self.progress.configure(progress_color=C["accent"])
            self.progress.set(max(0.01, min(1.0, percent / 100.0)))
            self.spinner_label.configure(text=f"Mengunduh model... {percent}%")
            self.status_text.set(
                f"{phase}: {percent}% [RAM: {get_process_memory_mb()} MB]"
            )
            return

        if isinstance(event, (int, float)):
            percent = max(0, min(100, int(event)))
            if tool == TOOL_UPSCALE:
                phase = f"Upscale {scale}x"
                spinner_text = f"Memperbesar foto ({scale}x)... {percent}%"
            else:
                phase = "Remove Background"
                spinner_text = f"Menghapus background... {percent}%"
            self.progress_phase_var.set(phase)
            self.progress_percent_var.set(f"{percent}%")
            self.progress.set(max(0.01, percent / 100.0))
            self.spinner_label.configure(text=spinner_text)
            self.status_text.set(
                f"{phase}: {percent}% [RAM: {get_process_memory_mb()} MB]"
            )
            return

        message = str(event)
        self.progress_phase_var.set(message)
        self.spinner_label.configure(text=message)
        if "siap" in message.lower():
            self.progress.set(0.4)
            self.progress_percent_var.set("Menyiapkan")
        self.status_text.set(f"{message} [RAM: {get_process_memory_mb()} MB]")

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
            self.btn_repreview.configure(text="Proses Ulang")
            self.preview_state_var.set("SIAP  /  REMOVE BACKGROUND")
            self.status_text.set(f"Alat aktif: Hapus Background. [RAM: {get_process_memory_mb()} MB]")
        else:
            self.btn_tool_upscale.configure(fg_color=C["accent"], text_color=C["text"])
            self.btn_tool_rmbg.configure(fg_color="transparent", text_color=C["dim"])
            self.frame_rmbg_settings.pack_forget()
            self.frame_upscale_settings.pack(fill="x", before=self._lbl_single_section)
            self.btn_repreview.configure(text="Proses Upscale")
            self.preview_state_var.set(f"SIAP  /  UPSCALE {self.scale_var.get()}X")
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
        self.preview_file_var.set(Path(src).name)
        self.file_state_label.configure(text=f"File aktif: {Path(src).name}")
        self.preview_state_var.set("MEMUAT  /  LOKAL")

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
                self.preview_state_var.set(f"SIAP  /  UPSCALE {self.scale_var.get()}X")
                self.status_text.set(
                    f"Gambar dimuat: {orig_sz[0]}x{orig_sz[1]} px. "
                    f"Pilih skala lalu klik 'Proses Upscale'. [RAM: {get_process_memory_mb()} MB]"
                )
            else:
                self.preview_state_var.set("MEMPROSES  /  REMOVE BACKGROUND")
                self.status_text.set(
                    f"Gambar dimuat: {orig_sz[0]}x{orig_sz[1]} px. Menghapus background... [RAM: {get_process_memory_mb()} MB]"
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
                self.preview_state_var.set(
                    "SIAP  /  UPSCALE" if tool == TOOL_UPSCALE
                    else "SIAP  /  REMOVE BACKGROUND"
                )
                self.status_text.set("Pengunduhan model dibatalkan pengguna.")
                self._processing = False
                self._update_button_states()
                self.progress.set(0)
                return

        self.spinner_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.spinner_frame.lift()
        self.spinner.start()

        if tool == TOOL_UPSCALE:
            self.spinner_label.configure(text=f"Memperbesar foto ({scale}x)...")
            self.status_text.set(f"Memperbesar foto ({scale}x)... [RAM: {get_process_memory_mb()} MB]")
            self.progress_phase_var.set(f"Upscale {scale}x")
        else:
            self.spinner_label.configure(text="Menghapus background...")
            self.status_text.set(f"Menghapus background ({mode})... [RAM: {get_process_memory_mb()} MB]")
            self.progress_phase_var.set("Remove Background")

        self.progress.set(0.15)
        self.progress_percent_var.set("Menyiapkan")

        th = self.threshold_var.get()
        fr = self.fringe_var.get()
        ag = self.aggressive_var.get()
        es, am, er = self._get_refinement_params()

        def _status_cb(val):
            self.after(0, lambda event=val: self._apply_status_event(event, tool, scale))

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
        self.progress_phase_var.set("Selesai")
        self.progress_percent_var.set("100%")
        self.preview_state_var.set(
            "SELESAI  /  UPSCALE" if self.active_tool == TOOL_UPSCALE
            else "SELESAI  /  REMOVE BACKGROUND"
        )

        self.preview_canvas.set_images(self._original, self._result)
        self._update_button_states()

        orig_sz = self._original.size
        res_sz = self._result.size
        ram_mb = get_process_memory_mb()

        if self.active_tool == TOOL_UPSCALE:
            self.status_text.set(
                f"[Upscale {self.scale_var.get()}x] Selesai: {orig_sz[0]}x{orig_sz[1]} -> {res_sz[0]}x{res_sz[1]} px. "
                f"[RAM: {ram_mb} MB] -> Klik 'Simpan Hasil'."
            )
        else:
            self.status_text.set(
                f"[{self.mode_var.get()}] Selesai: {res_sz[0]}x{res_sz[1]} px. "
                f"[RAM: {ram_mb} MB] -> Klik 'Simpan Hasil'."
            )

    def _on_process_err(self, err):
        self.spinner.stop()
        self.spinner_frame.place_forget()

        self._processing = False
        self.progress.set(0)
        self.progress.configure(progress_color=C["accent"])
        self.progress_phase_var.set("Gagal")
        self.progress_percent_var.set("0%")
        self.preview_state_var.set("ERROR  /  PERLU DICEK")

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

            self.status_text.set(f"Disimpan: {sz[0]}x{sz[1]} px -> {Path(dst).name} [RAM: {get_process_memory_mb()} MB]")
            messagebox.showinfo(
                APP_NAME,
                f"Tersimpan!\n\nResolusi Output: {sz[0]}x{sz[1]} px\n"
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

        def _batch_status(event):
            self.after(
                0,
                lambda value=event: self._apply_status_event(value, tool, scale),
            )

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
                        tool=tool, scale=scale, status_cb=_batch_status,
                    )
                    ok += 1
                except Exception as e:
                    errors.append(f"{src.name}: {e}")

            self.after(0, lambda: self._batch_done(ok, total, errors, cancelled=self._batch_cancelled))

        threading.Thread(target=_batch, daemon=True).start()

    def _batch_tick(self, idx, total, src_name, dst_name):
        self.status_text.set(
            f"Memproses {idx}/{total}: {src_name} -> {dst_name} [RAM: {get_process_memory_mb()} MB]"
        )
        self.progress.set(idx / total)
        self.progress_phase_var.set(f"Batch {idx}/{total}")
        self.progress_percent_var.set(f"{int((idx / total) * 100)}%")

    def _batch_done(self, ok, total, errors, cancelled=False):
        self.progress.set(0)
        self.progress_percent_var.set("0%")
        self._processing = False
        self._update_button_states()
        self.btn_cancel_batch.configure(state="disabled", fg_color=C["border"])

        ram_mb = get_process_memory_mb()
        if cancelled:
            self.progress_phase_var.set("Batch dibatalkan")
            msg = f"Batch dibatalkan. {ok} dari {total} gambar selesai diproses. [RAM: {ram_mb} MB]"
            self.status_text.set(msg)
            messagebox.showinfo(APP_NAME, msg)
        elif errors:
            self.progress_phase_var.set("Batch selesai dengan error")
            self.status_text.set(f"Selesai {ok}/{total}. Ada {len(errors)} error. [RAM: {ram_mb} MB]")
            messagebox.showwarning(
                APP_NAME,
                f"Selesai: {ok}/{total} file.\nAda error pada {len(errors)} file:\n\n"
                + "\n".join(errors[:10]),
            )
        else:
            self.progress_phase_var.set("Batch selesai")
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
