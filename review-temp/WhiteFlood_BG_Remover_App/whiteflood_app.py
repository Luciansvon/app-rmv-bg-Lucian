"""
WhiteFlood BG Remover v2.4.0
Aplikasi Windows Desktop untuk Menghapus Background Gambar Produk Furnitur (PNG Transparan).
Non-negotiable rules: Tanpa Crop, Tanpa Resize, Dimensi Asli 100% Dipertahankan.
"""

import os
import sys
import threading
import importlib.util
import re
import math
from pathlib import Path
from collections import deque

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageFilter, ImageDraw
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
        "whiteflood.bgremover.v2.4"
    )
except Exception:
    pass

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
    # Replace invalid chars < > : " / \ | ? * with -
    cleaned = re.sub(r'[<>:"/\\|?*]', '-', name.strip())
    # Collapse multiple dashes or spaces
    cleaned = re.sub(r'[\s\-]+', '-', cleaned).strip('.- ')
    return cleaned if cleaned else "output"

# ── Check if rembg is available (lightweight check) ──────
REMBG_OK = importlib.util.find_spec("rembg") is not None

# Cache for rembg session (lazy loaded)
_rembg_session = None
_rembg_model_name = None

# ═══════════════════════════════════════════════════════════
#  Theme & Constants
# ═══════════════════════════════════════════════════════════

APP_NAME = "WhiteFlood BG Remover"
VERSION = "2.4.0"

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
    MODE_FURNITURE: "🪑 Furniture Quality (Rekomendasi Utama — Hasil Paling Rapi untuk Produk Furnitur, Kayu, & Katalog)",
    MODE_FAST: "⚡ Fast (Proses Cepat untuk Gambar Biasa)",
    MODE_PERSON: "👤 Person (Khusus Foto Orang, Manusia, Pakaian, & Rambut)",
    MODE_HIGH_DETAIL: "🔍 High Detail (Khusus Resolusi Tinggi & Ukiran Halus)",
    MODE_WHITE: "🌊 White Background (Instan Tanpa AI / Tanpa Internet untuk Background Polos)",
}

REFINE_ORIGINAL = "Original (Rekomendasi)"
REFINE_SOFT = "Soft (Pinggiran Halus)"
REFINE_ALPHA_MATTE = "Alpha Matte (Deteksi Rambut)"

C = {
    "bg":           "#10101c",
    "card":         "#18182a",
    "card_alt":     "#121220",
    "border":       "#262640",
    "accent":       "#e94560",
    "accent_hover": "#d63851",
    "blue":         "#1e3a8a",
    "blue_hover":   "#1d4ed8",
    "text":         "#f1f5f9",
    "dim":          "#94a3b8",
    "green":        "#22c55e",
    "green_dark":   "#16a34a",
    "purple":       "#a855f7",
    "purple_hover": "#9333ea",
    "red":          "#ef4444",
    "red_hover":    "#dc2626",
}

PREVIEW_MAX = (340, 240)
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
    splash.geometry("400x200")
    splash.configure(fg_color=C["card_alt"])

    # Center splash on screen
    try:
        ws = splash.winfo_screenwidth()
        hs = splash.winfo_screenheight()
        x = max(0, (ws // 2) - 200)
        y = max(0, (hs // 2) - 100)
        splash.geometry(f"400x200+{x}+{y}")
    except Exception:
        pass

    lbl_title = ctk.CTkLabel(
        splash, text="◆  WhiteFlood BG Remover",
        font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
        text_color=C["accent"],
    )
    lbl_title.pack(pady=(45, 6))

    lbl_sub = ctk.CTkLabel(
        splash, text=f"Memuat aplikasi v{VERSION}...",
        font=ctk.CTkFont(size=12), text_color=C["dim"],
    )
    lbl_sub.pack(pady=(0, 20))

    progress = ctk.CTkProgressBar(splash, width=300, height=4, progress_color=C["accent"])
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
#  AI Background Removal  (rembg / BiRefNet / U2-Net)
# ═══════════════════════════════════════════════════════════

def _get_rembg_session(model_name="birefnet-massive", status_cb=None):
    """Lazy-load rembg and cache session. Automatically frees old model RAM when switching."""
    global _rembg_session, _rembg_model_name

    if _rembg_session is not None:
        if _rembg_model_name == model_name:
            return _rembg_session
        else:
            # Model changed: explicitly release previous session to prevent RAM accumulation
            try:
                del _rembg_session
                import gc
                gc.collect()
            except Exception:
                pass
            _rembg_session = None
            _rembg_model_name = None

    from rembg import new_session
    max_retries = 3
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            if status_cb:
                if attempt > 1:
                    status_cb(f"⬇  Mencoba ulang unduhan model AI '{model_name}' (Percobaan {attempt}/{max_retries})…")
                else:
                    status_cb(f"⬇  Mengunduh model AI '{model_name}'… (cuma sekali, mohon tunggu)")

            _rembg_session = new_session(model_name)
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


def refine_alpha_mask(alpha_img, edge_smooth=0, erode_size=1):
    """
    Community Mask Refinement:
    1. Erode (shrink) 1px to strip white background color bleed along the outer edge.
    2. Apply GaussianBlur for smooth anti-aliased edge when requested.
    """
    if erode_size > 0:
        alpha_img = alpha_img.filter(ImageFilter.MinFilter(3))

    if edge_smooth > 0:
        alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=edge_smooth))

    return alpha_img


def ai_remove_bg(img, edge_smooth=0, model_name="birefnet-massive",
                 alpha_matting=False, status_cb=None):
    """
    Remove background using rembg (neural network).
    Works on ANY background color.
    Pixel dimensions are NEVER changed.
    """
    if not REMBG_OK:
        raise RuntimeError(
            "Pustaka 'rembg' belum terinstall.\n"
            "Silakan install dengan: pip install rembg[cpu]"
        )

    from rembg import remove as rembg_remove

    original_size = img.size
    rgba = img.convert("RGBA")

    session = _get_rembg_session(model_name, status_cb=status_cb)

    # Use post_process_mask=False so neural network returns continuous smooth alpha
    result = rembg_remove(
        rgba,
        session=session,
        post_process_mask=False,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10,
    )

    arr = np.array(result, dtype=np.uint8)
    alpha = arr[:, :, 3]
    alpha_pil = Image.fromarray(alpha, "L")

    # Apply 1px erode to strip white fringe bleed + optional feathering
    refined_alpha = refine_alpha_mask(alpha_pil, edge_smooth=edge_smooth, erode_size=1)
    arr[:, :, 3] = np.array(refined_alpha)

    result = Image.fromarray(arr, "RGBA")

    if result.size != original_size:
        raise RuntimeError("Internal error: Ukuran piksel berubah.")
    return result


# ═══════════════════════════════════════════════════════════
#  WhiteFlood Background Removal  (flood-fill, BG putih)
# ═══════════════════════════════════════════════════════════

def flood_remove_bg(img, threshold=220, fringe=30,
                    edge_smooth=0, aggressive=False):
    """
    Remove near-white background connected to image borders.
    Pixel dimensions are NEVER changed.
    """
    original_size = img.size
    rgba = img.convert("RGBA")
    arr = np.array(rgba, dtype=np.uint8)
    h, w = arr.shape[:2]

    rgb = arr[:, :, :3].astype(np.float32)
    alpha = arr[:, :, 3].copy()
    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

    near_white = (lum > threshold) & (alpha > 0)

    # BFS from borders.
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

    # Aggressive: second pass with relaxed threshold.
    if aggressive:
        rlx = max(threshold - 35, 140)
        relaxed = (lum > rlx) & (alpha > 0)

        boundary = np.zeros_like(visited)
        for dy, dx in NEIGHBORS_8:
            sy = slice(max(0, -dy), min(h, h - dy))
            sx = slice(max(0, -dx), min(w, w - dx))
            dy2 = slice(max(0, dy), min(h, h + dy))
            dx2 = slice(max(0, dx), min(w, w + dx))
            boundary[dy2, dx2] |= visited[sy, sx]
        boundary &= ~visited

        seeds = np.argwhere(boundary & relaxed)
        q2 = deque()
        for yx in seeds:
            yy, xx = int(yx[0]), int(yx[1])
            if not visited[yy, xx]:
                visited[yy, xx] = True
                q2.append((yy, xx))
        while q2:
            y, x = q2.popleft()
            for dy, dx in NEIGHBORS_8:
                ny, nx = y + dy, x + dx
                if (0 <= ny < h and 0 <= nx < w
                        and not visited[ny, nx] and relaxed[ny, nx]):
                    visited[ny, nx] = True
                    q2.append((ny, nx))

    # Morphological dilation.
    mask_pil = Image.fromarray((visited.astype(np.uint8) * 255), "L")
    dilated_pil = mask_pil.copy()
    for _ in range(2):
        dilated_pil = dilated_pil.filter(ImageFilter.MaxFilter(3))
    dilated = np.array(dilated_pil) > 128
    bright_enough = lum > (threshold - 25)
    visited = visited | (dilated & bright_enough & (alpha > 0))

    # Edge feathering.
    bg_float = visited.astype(np.float32)
    if edge_smooth > 0:
        m = Image.fromarray((bg_float * 255).astype(np.uint8), "L")
        m = m.filter(ImageFilter.GaussianBlur(radius=edge_smooth))
        bg_smooth = np.array(m).astype(np.float32) / 255.0
    else:
        bg_smooth = bg_float

    new_alpha = arr[:, :, 3].astype(np.float32) * (1.0 - bg_smooth)

    # Fringe cleanup.
    if fringe > 0:
        edge_adj = np.zeros_like(visited)
        for dy, dx in NEIGHBORS_8:
            sy = slice(max(0, -dy), min(h, h - dy))
            sx = slice(max(0, -dx), min(w, w - dx))
            dy2 = slice(max(0, dy), min(h, h + dy))
            dx2 = slice(max(0, dx), min(w, w + dx))
            edge_adj[dy2, dx2] |= visited[sy, sx]
        candidate = edge_adj & (~visited) & (new_alpha > 0)
        ws = np.clip(
            (lum - (threshold - 30)) / max(1, 255 - (threshold - 30)), 0, 1,
        )
        amt = np.clip(fringe / 80.0, 0.0, 0.85)
        red = ws * amt * 255.0
        new_alpha[candidate] = np.maximum(
            0, new_alpha[candidate] - red[candidate],
        )

    arr[:, :, 3] = new_alpha.astype(np.uint8)
    result = Image.fromarray(arr, "RGBA")
    if result.size != original_size:
        raise RuntimeError("Internal error: Ukuran piksel berubah.")
    return result


def process_file(src, dst, mode, threshold, fringe, edge_smooth, aggressive,
                 model_name="birefnet-massive", alpha_matting=False):
    """Process a single file end-to-end preserving pixel dimensions."""
    src, dst = Path(src), Path(dst)
    with Image.open(src) as img:
        original_size = img.size
        meta = metadata_for_save(img)

        if mode == MODE_WHITE:
            result = flood_remove_bg(
                img, threshold, fringe, edge_smooth, aggressive,
            )
        else:
            result = ai_remove_bg(
                img, edge_smooth=edge_smooth,
                model_name=model_name, alpha_matting=alpha_matting,
            )

        if result.size != original_size:
            raise RuntimeError(
                f"Resolusi berubah: {original_size} -> {result.size}"
            )
        dst.parent.mkdir(parents=True, exist_ok=True)
        result.save(dst, format="PNG", optimize=False, **meta)

        with Image.open(dst) as check:
            if check.size != original_size:
                raise RuntimeError(
                    f"Mismatch resolusi tersimpan: {original_size} -> {check.size}"
                )


# ═══════════════════════════════════════════════════════════
#  Application UI
# ═══════════════════════════════════════════════════════════

class WhiteFloodApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")

        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("940x820")
        self.minsize(880, 740)
        self.configure(fg_color=C["bg"])

        # ── Set window icon ──
        self._set_app_icon()

        # State Variables
        self.mode_var = ctk.StringVar(value=MODE_FURNITURE)
        self.refine_var = ctk.StringVar(value=REFINE_ORIGINAL)
        self.threshold_var = ctk.IntVar(value=220)
        self.fringe_var = ctk.IntVar(value=30)
        self.aggressive_var = ctk.BooleanVar(value=False)
        self.output_dir = ctk.StringVar(value="")
        self.batch_name_var = ctk.StringVar(value="kursi-panjang")
        self.status_text = ctk.StringVar(
            value="Siap. Ukuran piksel output selalu 100% sama dengan input."
        )

        self._src_path = None
        self._original = None
        self._original_meta = {}
        self._result = None
        self._processing = False
        self._batch_cancelled = False

        self._img_before = None
        self._img_after = None

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

                    try:
                        hwnd = self.winfo_id()
                        WM_SETICON = 0x0080
                        LR_LOADFROMFILE = 0x0010
                        IMAGE_ICON = 1
                        h_small = ctypes.windll.user32.LoadImageW(0, str(ico_path), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                        h_big = ctypes.windll.user32.LoadImageW(0, str(ico_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                        if h_small:
                            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, h_small)
                        if h_big:
                            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, h_big)
                    except Exception:
                        pass

                if png_path.exists():
                    from PIL import ImageTk
                    icon_img = Image.open(png_path)
                    sizes = []
                    for s in [16, 32, 48, 64, 128, 256]:
                        resized = icon_img.copy()
                        resized = resized.resize((s, s), Image.LANCZOS)
                        sizes.append(ImageTk.PhotoImage(resized))
                    self._app_icons = sizes
                    self.iconphoto(True, *sizes)
            except Exception:
                pass

        self.after(100, _apply_icon)

    # ───────────────────────────────────────
    #  Build UI
    # ───────────────────────────────────────

    def _build_ui(self):
        root = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["accent"],
        )
        root.pack(fill="both", expand=True)

        main = ctk.CTkFrame(root, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24, pady=16)

        # ── Header Title ──
        tf = ctk.CTkFrame(main, fg_color="transparent")
        tf.pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(
            tf, text="◆ WhiteFlood",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=C["accent"],
        ).pack(side="left")
        ctk.CTkLabel(
            tf, text="BG Remover",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=C["text"],
        ).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(
            tf, text=f"v{VERSION}",
            font=ctk.CTkFont(size=11), text_color=C["dim"],
        ).pack(side="left", padx=(8, 0), pady=(8, 0))

        ctk.CTkLabel(
            main,
            text="Aplikasi Pemotong Background Foto Produk Furnitur. Tanpa Resize, Tanpa Crop.",
            font=ctk.CTkFont(size=12), text_color=C["dim"],
        ).pack(anchor="w", pady=(0, 14))

        # ── Preview Card ──────────────────
        prev_card = self._card(main, "PREVIEW GAMBAR")

        prev_row = ctk.CTkFrame(prev_card, fg_color="transparent")
        prev_row.pack(fill="x", padx=16, pady=(0, 14))
        prev_row.columnconfigure(0, weight=1)
        prev_row.columnconfigure(1, weight=1)

        # Original Preview Box
        bf = ctk.CTkFrame(prev_row, fg_color=C["card_alt"], corner_radius=10, height=270)
        bf.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        bf.pack_propagate(False)
        ctk.CTkLabel(bf, text="GAMBAR ASLI", font=ctk.CTkFont(size=10, weight="bold"), text_color=C["dim"]).pack(pady=(8, 2))
        self.lbl_before = ctk.CTkLabel(bf, text="Belum ada gambar", text_color=C["dim"], font=ctk.CTkFont(size=12))
        self.lbl_before.pack(expand=True)

        # Result Preview Box
        af = ctk.CTkFrame(prev_row, fg_color=C["card_alt"], corner_radius=10, height=270)
        af.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        af.pack_propagate(False)
        ctk.CTkLabel(af, text="HASIL TRANSPARAN", font=ctk.CTkFont(size=10, weight="bold"), text_color=C["dim"]).pack(pady=(8, 2))
        
        self.lbl_after = ctk.CTkLabel(af, text="Belum diproses", text_color=C["dim"], font=ctk.CTkFont(size=12))
        self.lbl_after.pack(expand=True)

        # Spinner Frame (Overlay when processing)
        self.spinner_frame = ctk.CTkFrame(af, fg_color="transparent")
        self.spinner = LoadingSpinner(self.spinner_frame, size=48, color=C["accent"], bg_color=C["card_alt"])
        self.spinner.pack(pady=(0, 8))
        self.spinner_label = ctk.CTkLabel(
            self.spinner_frame, text="Menghapus background...",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=C["accent"]
        )
        self.spinner_label.pack()

        # ── Mode & Settings Card ─────────
        settings_card = self._card(main, "PENGATURAN MODE PROSES")

        sg = ctk.CTkFrame(settings_card, fg_color="transparent")
        sg.pack(fill="x", padx=16, pady=(0, 14))
        sg.columnconfigure(1, weight=1)

        # 1. Mode Dropdown
        ctk.CTkLabel(sg, text="Mode Proses", text_color=C["text"], font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w")
        
        modes = [MODE_FURNITURE, MODE_FAST, MODE_PERSON, MODE_HIGH_DETAIL, MODE_WHITE]
        self.mode_dropdown = ctk.CTkOptionMenu(
            sg, values=modes, variable=self.mode_var,
            command=self._on_mode_change,
            fg_color=C["card_alt"], button_color=C["accent"],
            button_hover_color=C["accent_hover"],
            dropdown_fg_color=C["card"], dropdown_hover_color=C["border"],
            dropdown_text_color=C["text"], text_color=C["text"],
            font=ctk.CTkFont(size=12, weight="bold"), corner_radius=8, height=34,
        )
        self.model_dropdown = self.mode_dropdown # alias
        self.mode_dropdown.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(14, 0))

        # Mode Description
        self.mode_desc = ctk.CTkLabel(
            sg, text="", font=ctk.CTkFont(size=11),
            text_color=C["dim"], wraplength=800, justify="left",
        )
        self.mode_desc.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 10))
        self._update_mode_desc()

        # 2. Edge Refinement Dropdown
        self.lbl_refine = ctk.CTkLabel(sg, text="Ketajaman Tepi", text_color=C["text"], font=ctk.CTkFont(size=13))
        self.lbl_refine.grid(row=2, column=0, sticky="w", pady=(4, 0))
        
        self.refine_dropdown = ctk.CTkOptionMenu(
            sg, values=[REFINE_ORIGINAL, REFINE_SOFT, REFINE_ALPHA_MATTE],
            variable=self.refine_var,
            fg_color=C["card_alt"], button_color=C["blue"],
            button_hover_color=C["blue_hover"],
            dropdown_fg_color=C["card"], dropdown_hover_color=C["border"],
            dropdown_text_color=C["text"], text_color=C["text"],
            font=ctk.CTkFont(size=12), corner_radius=8, height=32,
        )
        self.refine_dropdown.grid(row=2, column=1, columnspan=2, sticky="ew", padx=(14, 0), pady=(4, 0))

        # 3. WhiteFlood Specific Settings
        self.flood_widgets = []

        lbl_t = ctk.CTkLabel(sg, text="White Threshold", text_color=C["text"], font=ctk.CTkFont(size=13))
        lbl_t.grid(row=3, column=0, sticky="w", pady=(10, 0))
        sl_t = ctk.CTkSlider(
            sg, from_=180, to=254, variable=self.threshold_var,
            fg_color=C["border"], progress_color=C["accent"],
            button_color=C["accent"], button_hover_color=C["accent_hover"],
            command=self._on_threshold,
        )
        sl_t.grid(row=3, column=1, sticky="ew", padx=14, pady=(10, 0))
        self._lbl_white_threshold = ctk.CTkLabel(
            sg, text="220", width=36,
            text_color=C["accent"], font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._lbl_white_threshold.grid(row=3, column=2, pady=(10, 0))
        self.flood_widgets.extend([lbl_t, sl_t, self._lbl_white_threshold])

        lbl_f = ctk.CTkLabel(sg, text="Fringe Cleanup", text_color=C["text"], font=ctk.CTkFont(size=13))
        lbl_f.grid(row=4, column=0, sticky="w", pady=(10, 0))
        sl_f = ctk.CTkSlider(
            sg, from_=0, to=80, variable=self.fringe_var,
            fg_color=C["border"], progress_color=C["accent"],
            button_color=C["accent"], button_hover_color=C["accent_hover"],
            command=self._on_fringe,
        )
        sl_f.grid(row=4, column=1, sticky="ew", padx=14, pady=(10, 0))
        self._lbl_fringe_cleanup = ctk.CTkLabel(
            sg, text="30", width=36,
            text_color=C["accent"], font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._lbl_fringe_cleanup.grid(row=4, column=2, pady=(10, 0))
        self.flood_widgets.extend([lbl_f, sl_f, self._lbl_fringe_cleanup])

        self.aggressive_cb = ctk.CTkCheckBox(
            sg, text="Mode Agresif (untuk background bergradasi / shadow)",
            variable=self.aggressive_var, font=ctk.CTkFont(size=12),
            text_color=C["text"], fg_color=C["accent"],
            hover_color=C["accent_hover"], border_color=C["border"],
            corner_radius=4,
        )
        self.aggressive_cb.grid(row=5, column=0, columnspan=3, sticky="w", pady=(12, 0))
        self.flood_widgets.append(self.aggressive_cb)

        self._toggle_flood_settings()

        # ── Single Actions Card ────────────
        act_card = self._card(main, "PROSES GAMBAR TUNGGAL")

        btn_row = ctk.CTkFrame(act_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 14))
        btn_row.columnconfigure((0, 1, 2), weight=1)

        self.btn_pick = ctk.CTkButton(
            btn_row, text="Pilih Gambar", command=self.load_and_process,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            font=ctk.CTkFont(size=13, weight="bold"), height=40, corner_radius=8,
        )
        self.btn_pick.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_repreview = ctk.CTkButton(
            btn_row, text="Preview Ulang", command=self.repreview,
            fg_color=C["blue"], hover_color=C["blue_hover"],
            font=ctk.CTkFont(size=13, weight="bold"), height=40, corner_radius=8,
            state="disabled",
        )
        self.btn_repreview.grid(row=0, column=1, sticky="ew", padx=4)

        self.btn_save = ctk.CTkButton(
            btn_row, text="Simpan Hasil", command=self.save_result,
            fg_color=C["border"], hover_color=C["blue_hover"],
            font=ctk.CTkFont(size=13, weight="bold"), height=40, corner_radius=8,
            state="disabled",
        )
        self.btn_save.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        # ── Batch Card ────────────────────
        batch_card = self._card(main, "PROSES BATCH (BANYAK GAMBAR)")

        bg_frame = ctk.CTkFrame(batch_card, fg_color="transparent")
        bg_frame.pack(fill="x", padx=16, pady=(0, 14))
        bg_frame.columnconfigure(1, weight=1)

        # Batch Name Entry
        ctk.CTkLabel(bg_frame, text="Nama Batch", text_color=C["text"], font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w")
        self.entry_batch_name = ctk.CTkEntry(
            bg_frame, textvariable=self.batch_name_var,
            fg_color=C["card_alt"], border_color=C["border"],
            text_color=C["text"], font=ctk.CTkFont(size=12), height=32,
        )
        self.entry_batch_name.grid(row=0, column=1, sticky="ew", padx=12)
        self.entry_batch_name.bind("<KeyRelease>", self._update_batch_preview)

        # Output Folder Entry
        ctk.CTkLabel(bg_frame, text="Folder Output", text_color=C["dim"], font=ctk.CTkFont(size=12)).grid(row=1, column=0, sticky="w", pady=(10, 0))
        ctk.CTkEntry(
            bg_frame, textvariable=self.output_dir,
            fg_color=C["card_alt"], border_color=C["border"],
            text_color=C["text"], font=ctk.CTkFont(size=12), height=32,
        ).grid(row=1, column=1, sticky="ew", padx=12, pady=(10, 0))
        ctk.CTkButton(
            bg_frame, text="Pilih...", width=70, height=32,
            fg_color=C["border"], hover_color=C["blue"],
            command=self._choose_output, corner_radius=8,
        ).grid(row=1, column=2, pady=(10, 0))

        # Batch Naming Preview
        self.lbl_batch_preview = ctk.CTkLabel(
            bg_frame, text="Contoh hasil: kursi-panjang-1.png, kursi-panjang-2.png...",
            font=ctk.CTkFont(size=11), text_color=C["dim"], anchor="w"
        )
        self.lbl_batch_preview.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 10))

        # Batch Action Buttons
        b_btns = ctk.CTkFrame(bg_frame, fg_color="transparent")
        b_btns.grid(row=3, column=0, columnspan=3, sticky="ew")
        b_btns.columnconfigure(0, weight=3)
        b_btns.columnconfigure(1, weight=1)

        self.btn_batch = ctk.CTkButton(
            b_btns, text="Start Batch (Pilih Folder Asal)", command=self.process_folder,
            fg_color=C["blue"], hover_color=C["blue_hover"],
            font=ctk.CTkFont(size=13, weight="bold"), height=38, corner_radius=8,
        )
        self.btn_batch.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_cancel_batch = ctk.CTkButton(
            b_btns, text="Batal Batch", command=self.cancel_batch,
            fg_color=C["border"], hover_color=C["red_hover"],
            font=ctk.CTkFont(size=12, weight="bold"), height=38, corner_radius=8,
            state="disabled",
        )
        self.btn_cancel_batch.grid(row=0, column=1, sticky="ew")

        # ── Progress & Status Footer ──────
        self.progress = ctk.CTkProgressBar(
            main, fg_color=C["border"], progress_color=C["accent"],
            height=6, corner_radius=3,
        )
        self.progress.pack(fill="x", pady=(4, 6))
        self.progress.set(0)

        ctk.CTkLabel(
            main, textvariable=self.status_text,
            font=ctk.CTkFont(size=12), text_color=C["dim"], anchor="w",
        ).pack(fill="x")

    # ───────────────────────────────────────
    #  UI Helpers
    # ───────────────────────────────────────

    def _card(self, parent, label):
        card = ctk.CTkFrame(
            parent, fg_color=C["card"], corner_radius=12,
            border_width=1, border_color=C["border"],
        )
        card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(size=11, weight="bold"), text_color=C["dim"],
        ).pack(anchor="w", padx=16, pady=(12, 6))
        return card

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
            text=f"Contoh hasil: {name}-1.png, {name}-2.png, {name}-3.png..."
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
        # Refinement option only for AI
        if is_flood:
            self.lbl_refine.grid_remove()
            self.refine_dropdown.grid_remove()
            for w in self.flood_widgets:
                w.grid()
        else:
            self.lbl_refine.grid()
            self.refine_dropdown.grid()
            for w in self.flood_widgets:
                w.grid_remove()

    def _get_refinement_params(self):
        r = self.refine_var.get()
        if r == REFINE_SOFT:
            return 2, False
        elif r == REFINE_ALPHA_MATTE:
            return 0, True
        else: # REFINE_ORIGINAL
            return 0, False

    def _show_preview(self, original, result):
        thumb_b = original.copy()
        thumb_b.thumbnail(PREVIEW_MAX, Image.LANCZOS)
        self._img_before = ctk.CTkImage(light_image=thumb_b, dark_image=thumb_b, size=thumb_b.size)
        self.lbl_before.configure(image=self._img_before, text="")

        thumb_a = result.copy()
        thumb_a.thumbnail(PREVIEW_MAX, Image.LANCZOS)
        checker = make_checkerboard(thumb_a.width, thumb_a.height, cell=8)
        checker.paste(thumb_a, (0, 0), thumb_a)
        self._img_after = ctk.CTkImage(light_image=checker, dark_image=checker, size=checker.size)
        self.lbl_after.configure(image=self._img_after, text="")

    def _set_buttons(self, state):
        self.btn_pick.configure(state=state)
        self.btn_batch.configure(state=state)
        if state == "disabled":
            self.btn_repreview.configure(state="disabled")
            self.btn_save.configure(state="disabled")

    # ───────────────────────────────────────
    #  Single-Image Workflow
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
        self._do_process()

    def repreview(self):
        if self._original is None:
            return
        self._do_process()

    def _do_process(self):
        if self._processing:
            return
        self._processing = True
        self._set_buttons("disabled")

        mode = self.mode_var.get()
        is_ai = mode != MODE_WHITE
        internal_model = MODE_MAP.get(mode, "birefnet-massive")

        # Pop-up confirmation if model needs download
        if is_ai and not is_model_downloaded(internal_model):
            ans = messagebox.askyesno(
                APP_NAME,
                f"Model AI '{internal_model}' belum terinstal di komputer.\n\n"
                f"Apakah kamu ingin mengunduh model ini sekarang?\n"
                f"(Ukuran file ±150–250 MB, mengunduh via internet).",
            )
            if not ans:
                self.status_text.set("Pengunduhan model dibatalkan pengguna.")
                self._set_buttons("normal")
                self._processing = False
                self.progress.set(0)
                return

        # Show visual spinner & progress
        self.lbl_after.pack_forget()
        self.spinner_frame.pack(expand=True)
        self.spinner.start()

        if is_ai:
            self.status_text.set(f"Menghapus background ({mode})...")
        else:
            self.status_text.set("Menghapus background (WhiteFlood)...")
        self.progress.set(0.15)

        # Snapshot parameters
        th = self.threshold_var.get()
        fr = self.fringe_var.get()
        ag = self.aggressive_var.get()
        es, am = self._get_refinement_params()

        def _status_cb(msg):
            self.after(0, lambda m=msg: self.status_text.set(m))
            self.after(0, lambda: self.progress.configure(
                progress_color=C["purple"] if "⬇" in msg else C["accent"]
            ))
            self.after(0, lambda: self.progress.set(0.3))

        def _worker():
            try:
                if self._original is None:
                    with Image.open(self._src_path) as img:
                        self._original = img.copy()
                        self._original_meta = metadata_for_save(img)

                self.after(0, lambda: self.progress.set(0.4))

                if is_ai:
                    result = ai_remove_bg(
                        self._original, edge_smooth=es,
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
        self.spinner_frame.pack_forget()
        self.lbl_after.pack(expand=True)

        self._processing = False
        self.progress.set(1.0)
        self.progress.configure(progress_color=C["accent"])
        self._show_preview(self._original, self._result)

        self._set_buttons("normal")
        self.btn_repreview.configure(state="normal")
        self.btn_save.configure(
            state="normal", fg_color=C["green"],
            hover_color=C["green_dark"], text_color="#000000",
        )

        sz = self._original.size
        mode = self.mode_var.get()
        self.status_text.set(
            f"[{mode}] Selesai: {sz[0]}×{sz[1]} px. "
            f"Klik 'Simpan Hasil' untuk menyimpan PNG transparan."
        )

    def _on_process_err(self, err):
        self.spinner.stop()
        self.spinner_frame.pack_forget()
        self.lbl_after.pack(expand=True)

        self._processing = False
        self.progress.set(0)
        self.progress.configure(progress_color=C["accent"])
        self._set_buttons("normal")
        self.status_text.set(f"Gagal memproses: {err}")
        messagebox.showerror(APP_NAME, f"Gagal memproses gambar:\n\n{err}")

    def save_result(self):
        if self._result is None:
            return
        stem = Path(self._src_path).stem if self._src_path else "output"
        dst = filedialog.asksaveasfilename(
            title="Simpan hasil PNG transparan", defaultextension=".png",
            initialfile=f"{stem}_transparent.png",
            filetypes=[("PNG Transparan", "*.png")],
        )
        if not dst:
            return
        try:
            self._result.save(dst, format="PNG", optimize=False, **self._original_meta)
            with Image.open(dst) as check:
                sz = check.size
                orig = self._original.size
                if sz != orig:
                    raise RuntimeError(f"Resolusi tersimpan tidak cocok: {orig} -> {sz}")
            self.status_text.set(f"Disimpan: {sz[0]}×{sz[1]} px → {Path(dst).name}")
            messagebox.showinfo(
                APP_NAME,
                f"Tersimpan!\n\nResolusi Output: {sz[0]}×{sz[1]} px\n"
                f"Lokasi File: {dst}\n\nTanpa resize atau crop.",
            )
        except Exception as e:
            self.status_text.set(f"Error simpan: {e}")
            messagebox.showerror(APP_NAME, f"Gagal menyimpan file:\n{e}")

    # ───────────────────────────────────────
    #  Batch Workflow & Collision Avoidance
    # ───────────────────────────────────────

    def _get_next_sequence_name(self, out_dir, base_name, start_idx=1):
        """Calculate non-conflicting sequence filename so existing outputs are never overwritten."""
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

        mode = self.mode_var.get()
        internal_model = MODE_MAP.get(mode, "birefnet-massive")
        is_ai = mode != MODE_WHITE

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

        th, fr, ag = (
            self.threshold_var.get(), self.fringe_var.get(), self.aggressive_var.get(),
        )
        es, am = self._get_refinement_params()
        base_batch_name = self.batch_name_var.get()

        total = len(files)
        self._processing = True
        self._batch_cancelled = False
        self._set_buttons("disabled")
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
                    process_file(src, dst_path, mode, th, fr, es, ag,
                                 model_name=internal_model, alpha_matting=am)
                    ok += 1
                except Exception as e:
                    errors.append(f"{src.name}: {e}")

            self.after(0, lambda: self._batch_done(ok, total, errors, cancelled=self._batch_cancelled))

        threading.Thread(target=_batch, daemon=True).start()

    def _batch_tick(self, idx, total, src_name, dst_name):
        self.status_text.set(f"Memproses {idx}/{total}: {src_name} → {dst_name}")
        self.progress.set(idx / total)

    def _batch_done(self, ok, total, errors, cancelled=False):
        self.progress.set(0)
        self._processing = False
        self._set_buttons("normal")
        self.btn_cancel_batch.configure(state="disabled", fg_color=C["border"])

        if cancelled:
            msg = f"Batch dibatalkan. {ok} dari {total} gambar selesai diproses."
            self.status_text.set(msg)
            messagebox.showinfo(APP_NAME, msg)
        elif errors:
            self.status_text.set(f"Selesai {ok}/{total}. Ada {len(errors)} error.")
            messagebox.showwarning(
                APP_NAME,
                f"Selesai: {ok}/{total} file.\nAda error pada {len(errors)} file:\n\n"
                + "\n".join(errors[:10]),
            )
        else:
            self.status_text.set(f"Selesai: {ok} file diproses tanpa merubah resolusi.")
            messagebox.showinfo(
                APP_NAME,
                f"Selesai memproses {ok} file!\n\n"
                f"Semua output mempertahankan 100% ukuran piksel asli.",
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

    app.after(300, _reveal)
    app.mainloop()
