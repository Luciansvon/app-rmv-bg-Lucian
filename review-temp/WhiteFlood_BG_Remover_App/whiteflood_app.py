"""
WhiteFlood BG Remover v2.2
Hapus background -> PNG transparan.
Dua mode:
  - AI  : pakai rembg (neural network), bisa semua warna background
  - Flood: flood-fill khusus background putih / near-white
"""

import os
import sys
import threading
import importlib.util
from pathlib import Path
from collections import deque

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageFilter, ImageDraw
import numpy as np

# ── Fix taskbar icon on Windows ──────────────────────────
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "whiteflood.bgremover.v2"
    )
except Exception:
    pass

# ── Check if rembg is available (lightweight, no heavy import) ──
REMBG_OK = importlib.util.find_spec("rembg") is not None

# Cache for rembg session (lazy loaded)
_rembg_session = None
_rembg_model_name = None

# ═══════════════════════════════════════════════════════════
#  Theme & Constants
# ═══════════════════════════════════════════════════════════

APP_NAME = "WhiteFlood BG Remover"
VERSION = "2.2"

MODE_AI = "🤖  AI (Semua BG)"
MODE_FLOOD = "🌊  WhiteFlood (BG Putih)"

C = {
    "bg":           "#0f0f1a",
    "card":         "#1a1a2e",
    "card_alt":     "#12121f",
    "border":       "#2a2a4a",
    "accent":       "#e94560",
    "accent_hover": "#d63851",
    "blue":         "#0f3460",
    "blue_hover":   "#163d6b",
    "text":         "#eaeaea",
    "dim":          "#8d8d8d",
    "green":        "#4ade80",
    "green_dark":   "#16a34a",
    "purple":       "#a855f7",
    "purple_hover": "#9333ea",
}

PREVIEW_MAX = (340, 240)
NEIGHBORS_8 = [(-1, -1), (-1, 0), (-1, 1),
               (0, -1),           (0, 1),
               (1, -1),  (1, 0),  (1, 1)]


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
#  AI Background Removal  (rembg / U2-Net)
# ═══════════════════════════════════════════════════════════

def _get_rembg_session(model_name="birefnet-massive", status_cb=None):
    """Lazy-load rembg and cache the session. Only imports on first call."""
    global _rembg_session, _rembg_model_name

    if _rembg_session is not None and _rembg_model_name == model_name:
        return _rembg_session

    if status_cb:
        status_cb(f"⬇  Mengunduh model '{model_name}'… (cuma sekali, sabar ya)")

    from rembg import new_session
    _rembg_session = new_session(model_name)
    _rembg_model_name = model_name

    if status_cb:
        status_cb(f"✅  Model '{model_name}' siap!")

    return _rembg_session


def ai_remove_bg(img, edge_smooth=2, model_name="birefnet-massive",
                 alpha_matting=False, status_cb=None):
    """
    Remove background using rembg (neural network).
    Works on ANY background color.
    First call downloads the model (cached afterwards).
    Pixel dimensions are NEVER changed.

    model_name: "u2net", "isnet-general-use", or "birefnet-general"
    alpha_matting: if True, uses alpha matting for smoother edges
    """
    if not REMBG_OK:
        raise RuntimeError(
            "Library 'rembg' belum terinstall.\n"
            "Jalankan: pip install rembg[cpu]"
        )

    from rembg import remove as rembg_remove

    original_size = img.size
    rgba = img.convert("RGBA")

    session = _get_rembg_session(model_name, status_cb=status_cb)

    # rembg returns RGBA with transparent background.
    result = rembg_remove(
        rgba,
        session=session,
        post_process_mask=True,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10,
    )

    # Optional edge smoothing.
    if edge_smooth > 0 and edge_smooth <= 6:
        arr = np.array(result, dtype=np.uint8)
        alpha = arr[:, :, 3]

        # Only blur at edges (where alpha transitions from 0 to 255).
        alpha_pil = Image.fromarray(alpha, "L")
        alpha_blur = alpha_pil.filter(
            ImageFilter.GaussianBlur(radius=edge_smooth)
        )
        alpha_b = np.array(alpha_blur)

        # Blend: keep interior alpha, smooth edge alpha.
        is_full = alpha == 255
        is_zero = alpha == 0
        is_edge = ~is_full & ~is_zero
        alpha_out = alpha.copy()
        alpha_out[is_edge] = alpha_b[is_edge]
        arr[:, :, 3] = alpha_out

        result = Image.fromarray(arr, "RGBA")

    if result.size != original_size:
        raise RuntimeError("Internal error: output dimensions changed.")
    return result


# ═══════════════════════════════════════════════════════════
#  WhiteFlood Background Removal  (flood-fill, BG putih)
# ═══════════════════════════════════════════════════════════

def flood_remove_bg(img, threshold=220, fringe=30,
                    edge_smooth=2, aggressive=False):
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
        raise RuntimeError("Internal error: output dimensions changed.")
    return result


def process_file(src, dst, mode, threshold, fringe, edge_smooth, aggressive,
                 model_name="u2net", alpha_matting=False):
    """Process a single file end-to-end."""
    src, dst = Path(src), Path(dst)
    with Image.open(src) as img:
        original_size = img.size
        meta = metadata_for_save(img)

        if mode == MODE_AI:
            result = ai_remove_bg(
                img, edge_smooth=edge_smooth,
                model_name=model_name, alpha_matting=alpha_matting,
            )
        else:
            result = flood_remove_bg(
                img, threshold, fringe, edge_smooth, aggressive,
            )

        if result.size != original_size:
            raise RuntimeError(
                f"Resolution changed: {original_size} -> {result.size}"
            )
        dst.parent.mkdir(parents=True, exist_ok=True)
        result.save(dst, format="PNG", optimize=False, **meta)

        with Image.open(dst) as check:
            if check.size != original_size:
                raise RuntimeError(
                    f"Saved resolution mismatch: {original_size} -> {check.size}"
                )


# ═══════════════════════════════════════════════════════════
#  Application UI
# ═══════════════════════════════════════════════════════════

class WhiteFloodApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")

        self.title(APP_NAME)
        self.geometry("920x780")
        self.minsize(860, 720)
        self.configure(fg_color=C["bg"])

        # ── Set window icon ──
        self._set_app_icon()

        # State
        self.mode_var = ctk.StringVar(value=MODE_AI if REMBG_OK else MODE_FLOOD)
        self.threshold_var = ctk.IntVar(value=220)
        self.fringe_var = ctk.IntVar(value=30)
        self.smooth_var = ctk.IntVar(value=2)
        self.aggressive_var = ctk.BooleanVar(value=False)
        self.model_var = ctk.StringVar(value="birefnet-massive")
        self.alpha_matting_var = ctk.BooleanVar(value=False)
        self.output_dir = ctk.StringVar(value="")
        self.status_text = ctk.StringVar(
            value="Siap. Ukuran piksel output selalu = input."
        )

        self._src_path = None
        self._original = None
        self._original_meta = {}
        self._result = None
        self._processing = False

        self._img_before = None
        self._img_after = None

        self._build_ui()

    def _set_app_icon(self):
        """Set the window icon from logo.ico or logo.png."""
        # Support PyInstaller bundled path.
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).parent

        ico_path = base / "logo.ico"
        png_path = base / "logo.png"

        def _apply_icon():
            try:
                if ico_path.exists():
                    # Set both titlebar and taskbar icon
                    self.iconbitmap(default=str(ico_path))
                    self.iconbitmap(str(ico_path))
                if png_path.exists():
                    from PIL import ImageTk
                    icon_img = Image.open(png_path)
                    # Multiple sizes for taskbar + titlebar
                    sizes = []
                    for s in [16, 32, 48, 64, 128, 256]:
                        resized = icon_img.copy()
                        resized = resized.resize((s, s), Image.LANCZOS)
                        sizes.append(ImageTk.PhotoImage(resized))
                    self._app_icons = sizes  # keep reference!
                    self.iconphoto(True, *sizes)
            except Exception:
                pass

        # Delay icon setting to ensure window is fully initialized
        self.after(50, _apply_icon)

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
        main.pack(fill="both", expand=True, padx=26, pady=18)

        # ── Title ──
        tf = ctk.CTkFrame(main, fg_color="transparent")
        tf.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            tf, text="◆  WhiteFlood",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=C["accent"],
        ).pack(side="left")
        ctk.CTkLabel(
            tf, text="BG Remover",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=C["text"],
        ).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(
            tf, text=f"v{VERSION}",
            font=ctk.CTkFont(size=11), text_color=C["dim"],
        ).pack(side="left", padx=(10, 0), pady=(10, 0))

        ctk.CTkLabel(
            main,
            text="Hapus background → PNG transparan.  Tanpa resize, tanpa crop.",
            font=ctk.CTkFont(size=13), text_color=C["dim"],
        ).pack(anchor="w", pady=(0, 16))

        # ── Mode Selector ─────────────────
        mode_card = self._card(main, "MODE")

        mode_frame = ctk.CTkFrame(mode_card, fg_color="transparent")
        mode_frame.pack(fill="x", padx=18, pady=(0, 16))

        modes = [MODE_AI, MODE_FLOOD]
        if not REMBG_OK:
            modes = [MODE_FLOOD]

        self.mode_seg = ctk.CTkSegmentedButton(
            mode_frame,
            values=modes,
            variable=self.mode_var,
            command=self._on_mode_change,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["border"],
            selected_color=C["accent"],
            selected_hover_color=C["accent_hover"],
            unselected_color=C["card"],
            unselected_hover_color=C["border"],
            corner_radius=10,
            height=40,
        )
        self.mode_seg.pack(fill="x")

        if not REMBG_OK:
            ctk.CTkLabel(
                mode_frame,
                text="⚠  Mode AI tidak tersedia. Install: pip install rembg[cpu]",
                text_color="#fbbf24", font=ctk.CTkFont(size=11),
            ).pack(anchor="w", pady=(8, 0))

        self.mode_desc = ctk.CTkLabel(
            mode_frame, text="", font=ctk.CTkFont(size=11),
            text_color=C["dim"], wraplength=800, justify="left",
        )
        self.mode_desc.pack(anchor="w", pady=(8, 0))
        self._update_mode_desc()

        # ── Preview Card ──────────────────
        prev_card = self._card(main, "PREVIEW")

        prev_row = ctk.CTkFrame(prev_card, fg_color="transparent")
        prev_row.pack(fill="x", padx=18, pady=(0, 16))
        prev_row.columnconfigure(0, weight=1)
        prev_row.columnconfigure(1, weight=1)

        bf = ctk.CTkFrame(prev_row, fg_color=C["card_alt"], corner_radius=10, height=280)
        bf.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        bf.pack_propagate(False)
        ctk.CTkLabel(bf, text="ORIGINAL", font=ctk.CTkFont(size=10, weight="bold"), text_color=C["dim"]).pack(pady=(10, 4))
        self.lbl_before = ctk.CTkLabel(bf, text="Belum ada gambar", text_color=C["dim"], font=ctk.CTkFont(size=12))
        self.lbl_before.pack(expand=True)

        af = ctk.CTkFrame(prev_row, fg_color=C["card_alt"], corner_radius=10, height=280)
        af.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        af.pack_propagate(False)
        ctk.CTkLabel(af, text="HASIL", font=ctk.CTkFont(size=10, weight="bold"), text_color=C["dim"]).pack(pady=(10, 4))
        self.lbl_after = ctk.CTkLabel(af, text="Belum diproses", text_color=C["dim"], font=ctk.CTkFont(size=12))
        self.lbl_after.pack(expand=True)

        # ── Settings Card ─────────────────
        self.settings_card = self._card(main, "PENGATURAN")

        self.settings_grid = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        self.settings_grid.pack(fill="x", padx=18, pady=(0, 16))
        self.settings_grid.columnconfigure(1, weight=1)

        # Edge Smoothing (shared between modes)
        self._add_slider(self.settings_grid, 0, "Edge Smoothing", 0, 6, self.smooth_var, self._on_smooth)

        # ── AI-specific settings ──
        self.ai_widgets = []

        lbl_model = ctk.CTkLabel(
            self.settings_grid, text="Model AI",
            text_color=C["text"], font=ctk.CTkFont(size=13),
        )
        lbl_model.grid(row=1, column=0, sticky="w", pady=(14, 0))

        self.model_dropdown = ctk.CTkOptionMenu(
            self.settings_grid,
            values=[
                "birefnet-massive",
                "birefnet-general",
                "birefnet-portrait",
                "birefnet-hrsod",
                "isnet-general-use",
                "bria-rmbg",
                "u2net",
            ],
            variable=self.model_var,
            fg_color=C["card_alt"], button_color=C["accent"],
            button_hover_color=C["accent_hover"],
            dropdown_fg_color=C["card"], dropdown_hover_color=C["border"],
            dropdown_text_color=C["text"],
            text_color=C["text"], font=ctk.CTkFont(size=12),
            corner_radius=8, height=32,
        )
        self.model_dropdown.grid(row=1, column=1, columnspan=2, sticky="ew", padx=16, pady=(14, 0))
        self.ai_widgets.extend([lbl_model, self.model_dropdown])

        lbl_model_hint = ctk.CTkLabel(
            self.settings_grid,
            text="⭐ massive = terbaik  |  portrait = foto orang  |  hrsod = resolusi tinggi",
            text_color=C["dim"], font=ctk.CTkFont(size=10),
        )
        lbl_model_hint.grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))
        self.ai_widgets.append(lbl_model_hint)

        self.alpha_matting_cb = ctk.CTkCheckBox(
            self.settings_grid,
            text="Alpha Matting (pinggiran lebih halus, cocok untuk rambut/detail)",
            variable=self.alpha_matting_var, font=ctk.CTkFont(size=12),
            text_color=C["text"], fg_color=C["purple"],
            hover_color=C["purple_hover"], border_color=C["border"],
            corner_radius=4,
        )
        self.alpha_matting_cb.grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 0))
        self.ai_widgets.append(self.alpha_matting_cb)

        # ── WhiteFlood-specific settings ──
        self.flood_widgets = []

        lbl_t = ctk.CTkLabel(self.settings_grid, text="White Threshold", text_color=C["text"], font=ctk.CTkFont(size=13))
        lbl_t.grid(row=4, column=0, sticky="w", pady=(14, 0))
        sl_t = ctk.CTkSlider(
            self.settings_grid, from_=180, to=254, variable=self.threshold_var,
            fg_color=C["border"], progress_color=C["accent"],
            button_color=C["accent"], button_hover_color=C["accent_hover"],
            command=self._on_threshold,
        )
        sl_t.grid(row=4, column=1, sticky="ew", padx=16, pady=(14, 0))
        self._lbl_white_threshold = ctk.CTkLabel(
            self.settings_grid, text="220", width=36,
            text_color=C["accent"], font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._lbl_white_threshold.grid(row=4, column=2, pady=(14, 0))
        self.flood_widgets.extend([lbl_t, sl_t, self._lbl_white_threshold])

        lbl_f = ctk.CTkLabel(self.settings_grid, text="Fringe Cleanup", text_color=C["text"], font=ctk.CTkFont(size=13))
        lbl_f.grid(row=5, column=0, sticky="w", pady=(14, 0))
        sl_f = ctk.CTkSlider(
            self.settings_grid, from_=0, to=80, variable=self.fringe_var,
            fg_color=C["border"], progress_color=C["accent"],
            button_color=C["accent"], button_hover_color=C["accent_hover"],
            command=self._on_fringe,
        )
        sl_f.grid(row=5, column=1, sticky="ew", padx=16, pady=(14, 0))
        self._lbl_fringe_cleanup = ctk.CTkLabel(
            self.settings_grid, text="30", width=36,
            text_color=C["accent"], font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._lbl_fringe_cleanup.grid(row=5, column=2, pady=(14, 0))
        self.flood_widgets.extend([lbl_f, sl_f, self._lbl_fringe_cleanup])

        self.aggressive_cb = ctk.CTkCheckBox(
            self.settings_grid,
            text="Mode Agresif (untuk background bergradasi / shadow)",
            variable=self.aggressive_var, font=ctk.CTkFont(size=12),
            text_color=C["text"], fg_color=C["accent"],
            hover_color=C["accent_hover"], border_color=C["border"],
            corner_radius=4,
        )
        self.aggressive_cb.grid(row=6, column=0, columnspan=3, sticky="w", pady=(16, 0))
        self.flood_widgets.append(self.aggressive_cb)

        # Apply initial visibility.
        self._toggle_flood_settings()

        # ── Actions Card ──────────────────
        act_card = self._card(main, "PROSES")

        btn_row = ctk.CTkFrame(act_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=18)
        btn_row.columnconfigure((0, 1, 2), weight=1)

        self.btn_pick = ctk.CTkButton(
            btn_row, text="🖼  Pilih Gambar", command=self.load_and_process,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            font=ctk.CTkFont(size=13, weight="bold"), height=42, corner_radius=10,
        )
        self.btn_pick.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_repreview = ctk.CTkButton(
            btn_row, text="🔄  Preview Ulang", command=self.repreview,
            fg_color=C["blue"], hover_color=C["blue_hover"],
            font=ctk.CTkFont(size=13, weight="bold"), height=42, corner_radius=10,
            state="disabled",
        )
        self.btn_repreview.grid(row=0, column=1, sticky="ew", padx=4)

        self.btn_save = ctk.CTkButton(
            btn_row, text="💾  Simpan Hasil", command=self.save_result,
            fg_color=C["border"], hover_color=C["blue_hover"],
            font=ctk.CTkFont(size=13, weight="bold"), height=42, corner_radius=10,
            state="disabled",
        )
        self.btn_save.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        # Batch
        batch_row = ctk.CTkFrame(act_card, fg_color="transparent")
        batch_row.pack(fill="x", padx=18, pady=(10, 0))

        self.btn_batch = ctk.CTkButton(
            batch_row, text="📁  Batch 1 Folder", command=self.process_folder,
            fg_color=C["blue"], hover_color=C["blue_hover"],
            font=ctk.CTkFont(size=13, weight="bold"), height=40, corner_radius=10,
        )
        self.btn_batch.pack(fill="x")

        out_row = ctk.CTkFrame(act_card, fg_color="transparent")
        out_row.pack(fill="x", padx=18, pady=(10, 16))
        ctk.CTkLabel(out_row, text="Folder Output Batch:", text_color=C["dim"], font=ctk.CTkFont(size=12)).pack(side="left")
        ctk.CTkEntry(
            out_row, textvariable=self.output_dir,
            fg_color=C["card_alt"], border_color=C["border"],
            text_color=C["text"], font=ctk.CTkFont(size=12), height=32,
        ).pack(side="left", fill="x", expand=True, padx=(8, 8))
        ctk.CTkButton(
            out_row, text="Pilih…", width=70, height=32,
            fg_color=C["border"], hover_color=C["blue"],
            command=self._choose_output, corner_radius=8,
        ).pack(side="left")

        # ── Progress & Status ─────────────
        self.progress = ctk.CTkProgressBar(
            main, fg_color=C["border"], progress_color=C["accent"],
            height=6, corner_radius=3,
        )
        self.progress.pack(fill="x", pady=(4, 8))
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
            parent, fg_color=C["card"], corner_radius=14,
            border_width=1, border_color=C["border"],
        )
        card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(size=11, weight="bold"), text_color=C["dim"],
        ).pack(anchor="w", padx=18, pady=(14, 8))
        return card

    def _add_slider(self, parent, row, label, lo, hi, var, cb):
        pad_top = (14, 0) if row > 0 else 0
        ctk.CTkLabel(parent, text=label, text_color=C["text"], font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", pady=pad_top)
        ctk.CTkSlider(
            parent, from_=lo, to=hi, variable=var,
            fg_color=C["border"], progress_color=C["accent"],
            button_color=C["accent"], button_hover_color=C["accent_hover"],
            command=cb,
        ).grid(row=row, column=1, sticky="ew", padx=16, pady=pad_top)
        lbl = ctk.CTkLabel(parent, text=str(var.get()), width=36, text_color=C["accent"], font=ctk.CTkFont(size=13, weight="bold"))
        lbl.grid(row=row, column=2, pady=pad_top)
        setattr(self, f"_lbl_{label.lower().replace(' ', '_')}", lbl)

    # ── Slider callbacks ──
    def _on_threshold(self, v):
        v = round(float(v)); self.threshold_var.set(v); self._lbl_white_threshold.configure(text=str(v))

    def _on_fringe(self, v):
        v = round(float(v)); self.fringe_var.set(v); self._lbl_fringe_cleanup.configure(text=str(v))

    def _on_smooth(self, v):
        v = round(float(v)); self.smooth_var.set(v); self._lbl_edge_smoothing.configure(text=str(v))

    def _choose_output(self):
        folder = filedialog.askdirectory(title="Pilih folder output")
        if folder:
            self.output_dir.set(folder)

    # ── Mode toggle ──
    def _on_mode_change(self, _=None):
        self._toggle_flood_settings()
        self._update_mode_desc()

    def _update_mode_desc(self):
        mode = self.mode_var.get()
        if mode == MODE_AI:
            self.mode_desc.configure(
                text="AI menggunakan neural network untuk mendeteksi objek. "
                     "Bisa hapus background warna apapun. "
                     "Pilih model di Pengaturan. Model diunduh otomatis saat pertama dipakai."
            )
        else:
            self.mode_desc.configure(
                text="WhiteFlood menggunakan flood-fill dari tepi gambar. "
                     "Hanya untuk background putih / near-white / abu-abu muda."
            )

    def _toggle_flood_settings(self):
        is_ai = self.mode_var.get() == MODE_AI
        # Show/hide AI widgets
        for w in self.ai_widgets:
            if is_ai:
                w.grid()
            else:
                w.grid_remove()
        # Show/hide Flood widgets
        for w in self.flood_widgets:
            if not is_ai:
                w.grid()
            else:
                w.grid_remove()

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
        """Enable / disable action buttons."""
        self.btn_pick.configure(state=state)
        self.btn_batch.configure(state=state)
        if state == "disabled":
            self.btn_repreview.configure(state="disabled")
            self.btn_save.configure(state="disabled")

    # ───────────────────────────────────────
    #  Single-image workflow  (threaded)
    # ───────────────────────────────────────

    def load_and_process(self):
        src = filedialog.askopenfilename(
            title="Pilih gambar",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All", "*.*")],
        )
        if not src:
            return
        self._src_path = src
        self._original = None          # force reload
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
        is_ai = mode == MODE_AI

        if is_ai:
            self.status_text.set(f"AI [{self.model_var.get()}] sedang memproses…")
        else:
            self.status_text.set("Memproses…")
        self.progress.set(0.15)

        # Snapshot settings.
        th = self.threshold_var.get()
        fr = self.fringe_var.get()
        es = self.smooth_var.get()
        ag = self.aggressive_var.get()
        mn = self.model_var.get()
        am = self.alpha_matting_var.get()

        def _status_cb(msg):
            """Update status bar from worker thread."""
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
                        model_name=mn, alpha_matting=am,
                        status_cb=_status_cb,
                    )
                else:
                    result = flood_remove_bg(self._original, th, fr, es, ag)

                self._result = result
                self.after(0, lambda: self._on_process_ok())
            except Exception as e:
                self.after(0, lambda err=str(e): self._on_process_err(err))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_process_ok(self):
        self._processing = False
        self.progress.set(1.0)
        self._show_preview(self._original, self._result)

        self._set_buttons("normal")
        self.btn_repreview.configure(state="normal")
        self.btn_save.configure(
            state="normal", fg_color=C["green"],
            hover_color=C["green_dark"], text_color="#000000",
        )

        sz = self._original.size
        mode = self.mode_var.get()
        tag = "AI" if mode == MODE_AI else "WhiteFlood"
        self.status_text.set(
            f"[{tag}] Selesai: {sz[0]}×{sz[1]} px.  "
            f"Klik 'Simpan Hasil' atau ubah setting → 'Preview Ulang'."
        )

    def _on_process_err(self, err):
        self._processing = False
        self.progress.set(0)
        self._set_buttons("normal")
        self.status_text.set(f"Error: {err}")
        messagebox.showerror(APP_NAME, err)

    def save_result(self):
        if self._result is None:
            return
        stem = Path(self._src_path).stem if self._src_path else "output"
        dst = filedialog.asksaveasfilename(
            title="Simpan hasil", defaultextension=".png",
            initialfile=f"{stem}_transparent.png",
            filetypes=[("PNG", "*.png")],
        )
        if not dst:
            return
        try:
            self._result.save(dst, format="PNG", optimize=False, **self._original_meta)
            with Image.open(dst) as check:
                sz = check.size
                orig = self._original.size
                if sz != orig:
                    raise RuntimeError(f"Saved resolution mismatch: {orig} -> {sz}")
            self.status_text.set(f"Disimpan: {sz[0]}×{sz[1]} px → {Path(dst).name}")
            messagebox.showinfo(
                APP_NAME,
                f"Tersimpan!\n\nOutput: {sz[0]}×{sz[1]} px\n"
                f"File: {dst}\n\nTidak ada resize atau crop.",
            )
        except Exception as e:
            self.status_text.set(f"Error simpan: {e}")
            messagebox.showerror(APP_NAME, str(e))

    # ───────────────────────────────────────
    #  Batch workflow  (threaded)
    # ───────────────────────────────────────

    def process_folder(self):
        src_dir = filedialog.askdirectory(title="Pilih folder gambar")
        if not src_dir:
            return
        out_dir = self.output_dir.get().strip()
        if not out_dir:
            out_dir = filedialog.askdirectory(title="Pilih folder output")
            if not out_dir:
                return
            self.output_dir.set(out_dir)

        src_dir, out_dir = Path(src_dir), Path(out_dir)
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        files = sorted(p for p in src_dir.iterdir() if p.is_file() and p.suffix.lower() in exts)
        if not files:
            messagebox.showwarning(APP_NAME, "Tidak ada gambar yang didukung di folder itu.")
            return

        mode = self.mode_var.get()
        th, fr, es, ag = (
            self.threshold_var.get(), self.fringe_var.get(),
            self.smooth_var.get(), self.aggressive_var.get(),
        )
        mn = self.model_var.get()
        am = self.alpha_matting_var.get()
        total = len(files)
        self._set_buttons("disabled")

        def _batch():
            ok, errors = 0, []
            for idx, src in enumerate(files, 1):
                self.after(0, lambda i=idx, n=src.name: self._batch_tick(i, total, n))
                try:
                    dst = out_dir / f"{src.stem}.png"
                    process_file(src, dst, mode, th, fr, es, ag,
                                 model_name=mn, alpha_matting=am)
                    ok += 1
                except Exception as e:
                    errors.append(f"{src.name}: {e}")
            self.after(0, lambda: self._batch_done(ok, total, errors))

        threading.Thread(target=_batch, daemon=True).start()

    def _batch_tick(self, idx, total, name):
        self.status_text.set(f"Memproses {idx}/{total}: {name}")
        self.progress.set(idx / total)

    def _batch_done(self, ok, total, errors):
        self.progress.set(0)
        self._set_buttons("normal")
        if errors:
            self.status_text.set(f"Selesai {ok}/{total}. Ada {len(errors)} error.")
            messagebox.showwarning(
                APP_NAME,
                f"Selesai: {ok}/{total} file.\nError: {len(errors)} file.\n\n"
                + "\n".join(errors[:10]),
            )
        else:
            self.status_text.set(f"Selesai: {ok} file. Semua ukuran piksel dipertahankan.")
            messagebox.showinfo(
                APP_NAME,
                f"Selesai memproses {ok} file.\n\n"
                f"Semua output mempertahankan ukuran piksel asli.",
            )


# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = WhiteFloodApp()
    app.mainloop()
