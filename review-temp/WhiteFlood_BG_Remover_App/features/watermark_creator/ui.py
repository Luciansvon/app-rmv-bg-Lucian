from __future__ import annotations

import queue
import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image

from .benchmark import benchmark_invisible, save_benchmark_report
from .invisible import InvisiblePayload
from .presets import CreatorPreset, InvisiblePresetConfig, load_preset, save_preset
from .service import WatermarkCreatorService, short_file_hash
from .visible import VisibleWatermarkConfig

MODE = {"Visible": "visible", "Invisible*": "invisible", "Hybrid*": "hybrid"}
KIND = {"Text": "text", "Logo": "image"}
PATTERN = {
    "Single": "single", "Tile H": "tile_horizontal", "Tile V": "tile_vertical",
    "Full Tile": "full_tile", "Diagonal": "diagonal_repeat",
}


class WatermarkCreatorDialog(ctk.CTkToplevel):
    def __init__(self, parent, colors, preview_class, app_name="WhiteFlood"):
        super().__init__(parent)
        self.C, self.app_name = colors, app_name
        self.service = WatermarkCreatorService()
        self.source_path = None
        self.source_image = None
        self.source_metadata = {}
        self.logo = None
        self.result = None
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = False
        self.title("WhiteFlood Watermark Creator · v2.7.0-rc1")
        self.geometry("1160x760")
        self.minsize(980, 650)
        self.configure(fg_color=self.C["bg"])
        self.transient(parent)

        self.vars = {
            "mode": ctk.StringVar(value="Visible"), "kind": ctk.StringVar(value="Text"),
            "text": ctk.StringVar(value="BIMA"), "font": ctk.IntVar(value=52),
            "opacity": ctk.IntVar(value=60), "rotation": ctk.IntVar(value=-30),
            "stroke": ctk.IntVar(value=0), "shadow": ctk.BooleanVar(value=False),
            "scale": ctk.IntVar(value=18), "anchor": ctk.StringVar(value="CC"),
            "pattern": ctk.StringVar(value="Single"), "margin": ctk.IntVar(value=24),
            "spacing": ctk.IntVar(value=80), "offset_x": ctk.IntVar(value=0),
            "offset_y": ctk.IntVar(value=0), "owner": ctk.StringVar(value="BIMA"),
            "file_id": ctk.StringVar(value="FILE"), "strength": ctk.StringVar(value="balanced"),
            "status": ctk.StringVar(value="Pilih gambar. Source tidak akan ditimpa."),
        }
        self.columnconfigure(1, weight=1); self.rowconfigure(0, weight=1)
        self.side = ctk.CTkScrollableFrame(self, width=330, fg_color=self.C["card"], corner_radius=0)
        self.side.grid(row=0, column=0, sticky="nsew")
        shell = ctk.CTkFrame(self, fg_color=self.C["card"])
        shell.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        shell.rowconfigure(0, weight=1); shell.columnconfigure(0, weight=1)
        self.preview = preview_class(shell); self.preview.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(shell, textvariable=self.vars["status"], anchor="w", justify="left", wraplength=760,
                     text_color=self.C["text"]).grid(row=1, column=0, sticky="ew", padx=10, pady=8)
        self._controls()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(80, self._drain)

    def _label(self, text):
        ctk.CTkLabel(self.side, text=text, text_color=self.C["dim"],
                     font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=14, pady=(9, 3))

    def _slider(self, key, text, low, high):
        label = ctk.CTkLabel(self.side, text=f"{text}: {self.vars[key].get()}", text_color=self.C["dim"])
        label.pack(anchor="w", padx=14)
        def changed(v):
            n = round(float(v)); self.vars[key].set(n); label.configure(text=f"{text}: {n}")
        ctk.CTkSlider(self.side, from_=low, to=high, variable=self.vars[key], command=changed,
                      fg_color=self.C["border"], progress_color=self.C["accent"],
                      button_color=self.C["accent"]).pack(fill="x", padx=14, pady=(0, 4))

    def _controls(self):
        ctk.CTkLabel(self.side, text="WATERMARK CREATOR", text_color=self.C["accent"],
                     font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=14, pady=(16, 2))
        ctk.CTkButton(self.side, text="Pilih Gambar", command=self._source,
                      fg_color=self.C["accent"], hover_color=self.C["accent_hover"]).pack(fill="x", padx=14, pady=8)
        ctk.CTkSegmentedButton(self.side, values=list(MODE), variable=self.vars["mode"],
                               selected_color=self.C["accent"]).pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(self.side, text="* Invisible/Hybrid masih experimental sampai benchmark corpus nyata lolos.",
                     wraplength=295, justify="left", text_color=self.C["purple"]).pack(anchor="w", padx=14, pady=4)
        self._label("VISIBLE")
        ctk.CTkSegmentedButton(self.side, values=list(KIND), variable=self.vars["kind"]).pack(fill="x", padx=14, pady=3)
        ctk.CTkEntry(self.side, textvariable=self.vars["text"], placeholder_text="Watermark text").pack(fill="x", padx=14, pady=3)
        ctk.CTkButton(self.side, text="Pilih Logo PNG", command=self._logo,
                      fg_color=self.C["blue"], hover_color=self.C["blue_hover"]).pack(fill="x", padx=14, pady=3)
        for args in (("font", "Font", 8, 220), ("scale", "Logo scale %", 1, 80),
                     ("opacity", "Opacity %", 0, 100), ("rotation", "Rotation", -180, 180),
                     ("stroke", "Stroke px", 0, 12), ("margin", "Margin", 0, 300),
                     ("spacing", "Spacing", 0, 400), ("offset_x", "Offset X", -500, 500),
                     ("offset_y", "Offset Y", -500, 500)):
            self._slider(*args)
        ctk.CTkCheckBox(self.side, text="Shadow", variable=self.vars["shadow"],
                        fg_color=self.C["accent"]).pack(anchor="w", padx=14, pady=4)
        row = ctk.CTkFrame(self.side, fg_color="transparent"); row.pack(fill="x", padx=14, pady=3)
        ctk.CTkOptionMenu(row, values=["UL","UC","UR","CL","CC","CR","LL","LC","LR"],
                          variable=self.vars["anchor"]).pack(side="left", fill="x", expand=True, padx=(0,2))
        ctk.CTkOptionMenu(row, values=list(PATTERN), variable=self.vars["pattern"]).pack(side="left", fill="x", expand=True, padx=(2,0))
        self._label("INVISIBLE · EXPERIMENTAL")
        ctk.CTkEntry(self.side, textvariable=self.vars["owner"], placeholder_text="Owner ID").pack(fill="x", padx=14, pady=3)
        ctk.CTkEntry(self.side, textvariable=self.vars["file_id"], placeholder_text="File ID").pack(fill="x", padx=14, pady=3)
        ctk.CTkOptionMenu(self.side, values=["light","balanced","strong"], variable=self.vars["strength"]).pack(fill="x", padx=14, pady=3)
        for labels, funcs in [
            (("Preview","Export"),(self._preview,self._export)),
            (("Verify","Benchmark"),(self._verify,self._benchmark)),
            (("Batch Folder","Batal Batch"),(self._batch,self._cancel)),
            (("Save Preset","Load Preset"),(self._save_preset,self._load_preset)),
        ]:
            r=ctk.CTkFrame(self.side, fg_color="transparent"); r.pack(fill="x", padx=14, pady=3)
            for i,(label,func) in enumerate(zip(labels,funcs)):
                b=ctk.CTkButton(r,text=label,command=func,fg_color=self.C["card_alt"],hover_color=self.C["border"])
                b.pack(side="left",fill="x",expand=True,padx=(0,2) if i==0 else (2,0))
                if label=="Batal Batch": self.cancel_btn=b; b.configure(state="disabled")

    def _source(self):
        p=filedialog.askopenfilename(filetypes=[("Images","*.png *.jpg *.jpeg *.webp *.bmp")])
        if not p:return
        try:
            with Image.open(p) as im:
                alpha=im.mode in {"RGBA","LA","PA"} or (im.mode=="P" and "transparency" in im.info)
                self.source_image=im.convert("RGBA") if alpha else im.convert("RGB")
                self.source_metadata={k:im.info[k] for k in ("dpi","icc_profile","exif") if im.info.get(k)}
            self.source_path=Path(p); self.vars["file_id"].set(self.source_path.stem[:16] or "FILE")
            self.result=None; self.preview.set_images(self.source_image,None)
            self.vars["status"].set(f"{self.source_path.name} · {self.source_image.width}x{self.source_image.height}px")
        except Exception as e: messagebox.showerror(self.app_name,str(e))

    def _logo(self):
        p=filedialog.askopenfilename(filetypes=[("Images","*.png *.webp *.jpg *.jpeg")])
        if p:
            try:
                with Image.open(p) as im:self.logo=im.convert("RGBA")
            except Exception as e: messagebox.showerror(self.app_name,str(e))

    def _visible(self):
        v=self.vars
        return VisibleWatermarkConfig(kind=KIND[v["kind"].get()],text=v["text"].get(),font_size=v["font"].get(),
            opacity=v["opacity"].get(),rotation=v["rotation"].get(),stroke_width=v["stroke"].get(),shadow=v["shadow"].get(),
            image_scale_percent=v["scale"].get(),anchor=v["anchor"].get(),offset_x=v["offset_x"].get(),offset_y=v["offset_y"].get(),
            margin=v["margin"].get(),pattern=PATTERN[v["pattern"].get()],spacing_x=v["spacing"].get(),spacing_y=v["spacing"].get())

    def _payload(self):
        if not self.source_path: raise ValueError("Pilih gambar dulu.")
        return InvisiblePayload.now(self.vars["owner"].get().strip(),self.vars["file_id"].get().strip(),short_file_hash(self.source_path))

    def _create(self):
        if self.source_image is None: raise ValueError("Pilih gambar dulu.")
        mode=MODE[self.vars["mode"].get()]; vis=self._visible() if mode in {"visible","hybrid"} else None
        if vis and vis.kind=="image" and self.logo is None: raise ValueError("Pilih logo dulu.")
        payload=self._payload() if mode in {"invisible","hybrid"} else None
        return self.service.create(self.source_image,mode,vis,self.logo,payload,self.vars["strength"].get())

    def _preview(self):
        try:self.result=self._create();self.preview.set_images(self.source_image,self.result.image);self.vars["status"].set(f"Preview {self.result.mode} · dimensi tetap {self.result.image.size}")
        except Exception as e:messagebox.showerror(self.app_name,str(e))

    def _export(self):
        try:
            if self.result is None:self.result=self._create()
            p=filedialog.asksaveasfilename(defaultextension=".png",initialfile=f"{self.source_path.stem}_watermarked.png",filetypes=[("PNG","*.png"),("JPEG","*.jpg *.jpeg")])
            if p:self.vars["status"].set(f"Tersimpan: {self.service.save(self.result,p,self.source_metadata)}")
        except Exception as e:messagebox.showerror(self.app_name,str(e))

    def _verify(self):
        try:
            target=self.result.image if self.result else self.source_image
            if target is None:raise ValueError("Pilih gambar dulu.")
            r=self.service.verify(target,True)
            self.vars["status"].set(f"Detected YES · Owner {r.payload.owner_id} · File {r.payload.file_id} · confidence {r.confidence:.2f}" if r.detected else "Not detected / unreadable")
        except Exception as e:messagebox.showerror(self.app_name,str(e))

    def _benchmark(self):
        if self.worker or self.source_image is None:return
        try:payload=self._payload()
        except Exception as e:messagebox.showerror(self.app_name,str(e));return
        self.worker=True;self.vars["status"].set("Benchmark attack matrix...")
        source=self.source_image.copy();strength=self.vars["strength"].get()
        def run():
            try:self.events.put(("bench",benchmark_invisible(source,payload,strength)))
            except Exception as e:self.events.put(("error",str(e)))
        threading.Thread(target=run,daemon=True).start()

    def _batch(self):
        if self.worker:return
        src=filedialog.askdirectory(title="Folder sumber");out=filedialog.askdirectory(title="Folder output") if src else ""
        if not out:return
        mode=MODE[self.vars["mode"].get()];vis=self._visible() if mode in {"visible","hybrid"} else None
        self.cancel.clear();self.worker=True;self.cancel_btn.configure(state="normal")
        def progress(i,n,p):self.events.put(("status",f"Batch {i}/{n}: {p.name}"))
        def run():
            try:
                outputs=self.service.process_batch(src,out,mode,vis,self.vars["owner"].get().strip(),self.vars["strength"].get(),self.logo,True,progress,self.cancel)
                self.events.put(("batch",(len(outputs),self.cancel.is_set())))
            except Exception as e:self.events.put(("error",str(e)))
        threading.Thread(target=run,daemon=True).start()

    def _cancel(self):self.cancel.set();self.cancel_btn.configure(state="disabled");self.vars["status"].set("Membatalkan setelah file aktif selesai...")

    def _preset(self):
        mode=MODE[self.vars["mode"].get()]
        return CreatorPreset(mode=mode,visible=self._visible(),invisible=InvisiblePresetConfig(mode in {"invisible","hybrid"},self.vars["owner"].get().strip(),self.vars["strength"].get()))

    def _save_preset(self):
        p=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")])
        if p:save_preset(self._preset(),p);self.vars["status"].set(f"Preset tersimpan: {Path(p).name}")

    def _load_preset(self):
        p=filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not p:return
        try:
            x=load_preset(p);rv={v:k for k,v in MODE.items()};rk={v:k for k,v in KIND.items()};rp={v:k for k,v in PATTERN.items()};v=x.visible
            for k,val in {"mode":rv[x.mode],"kind":rk[v.kind],"text":v.text,"font":v.font_size,"opacity":v.opacity,"rotation":round(v.rotation),"stroke":v.stroke_width,
                "shadow":v.shadow,"scale":round(v.image_scale_percent),"anchor":v.anchor,"pattern":rp[v.pattern],"margin":v.margin,"spacing":v.spacing_x,"offset_x":v.offset_x,"offset_y":v.offset_y,
                "owner":x.invisible.owner_id,"strength":x.invisible.strength}.items():self.vars[k].set(val)
            self.vars["status"].set(f"Preset dimuat: {Path(p).name}")
        except Exception as e:messagebox.showerror(self.app_name,str(e))

    def _drain(self):
        if not self.winfo_exists():return
        for _ in range(50):
            try:kind,data=self.events.get_nowait()
            except queue.Empty:break
            if kind=="status":self.vars["status"].set(data)
            elif kind=="error":self.worker=False;self.cancel_btn.configure(state="disabled");messagebox.showerror(self.app_name,data)
            elif kind=="batch":
                self.worker=False;self.cancel_btn.configure(state="disabled");n,c=data;self.vars["status"].set(f"Batch {'dibatalkan aman' if c else 'selesai'}: {n} file")
            elif kind=="bench":
                self.worker=False;r=data;self.vars["status"].set(f"Benchmark fixture: recovery {r.recovery_rate*100:.0f}% · PSNR {r.psnr_db:.2f} dB · {'PASS' if r.benchmark_passed else 'BELUM PASS'}; tetap experimental sampai corpus nyata.")
                p=filedialog.asksaveasfilename(defaultextension=".json",initialfile="watermark-benchmark.json",filetypes=[("JSON","*.json")])
                if p:save_benchmark_report(r,p)
        self.after(80,self._drain)

    def _close(self):
        if self.worker:self.cancel.set();messagebox.showwarning(self.app_name,"Proses masih berjalan; pembatalan sudah diminta.");return
        self.destroy()
