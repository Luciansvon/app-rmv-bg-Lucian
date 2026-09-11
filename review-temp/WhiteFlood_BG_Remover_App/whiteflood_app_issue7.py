import customtkinter as ctk

from whiteflood_app import APP_NAME, C, SplitSliderPreview, WhiteFloodApp, show_splash
from features.watermark_creator.ui import WatermarkCreatorDialog

ISSUE7_VERSION = "2.7.0-rc1"


class WhiteFloodIssue7App(WhiteFloodApp):
    def __init__(self):
        self._creator_dialog = None
        super().__init__()
        self.title(f"{APP_NAME} v{ISSUE7_VERSION}")

    def _build_ui(self):
        super()._build_ui()
        nav = self.btn_tool_watermark_image.master
        self.btn_tool_creator = ctk.CTkButton(
            nav, text="Create Watermark", command=self._open_creator,
            fg_color="transparent", text_color=C["dim"], hover_color=C["border"],
            font=ctk.CTkFont(size=10, weight="bold"), height=32, corner_radius=7,
        )
        self.btn_tool_creator.grid(row=3, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
        ctk.CTkButton(
            self.workspace_view,
            text="Watermark Creator\n\nTambah visible + invisible watermark",
            command=self._open_creator, fg_color=C["card_alt"], hover_color=C["border"],
            border_width=1, border_color=C["border"], text_color=C["text"],
            font=ctk.CTkFont(size=11, weight="bold"), height=112, corner_radius=8,
        ).grid(row=3, column=2, sticky="nsew", padx=6, pady=6)

    def _open_creator(self):
        dialog = self._creator_dialog
        if dialog is not None:
            try:
                if dialog.winfo_exists():
                    dialog.lift(); dialog.focus_force(); return
            except Exception:
                pass
        self._creator_dialog = WatermarkCreatorDialog(self, C, SplitSliderPreview, APP_NAME)
        self._creator_dialog.focus_force()

    def _finish_close(self):
        dialog = self._creator_dialog
        if dialog is not None:
            try:
                if dialog.winfo_exists() and dialog.worker:
                    dialog.cancel.set(); self.after(100, self._finish_close); return
                if dialog.winfo_exists(): dialog.destroy()
            except Exception:
                pass
        super()._finish_close()


if __name__ == "__main__":
    app = WhiteFloodIssue7App()
    app.withdraw()
    splash = show_splash(app)
    def reveal():
        try: splash.destroy()
        except Exception: pass
        app.deiconify()
    app.after(800, reveal)
    app.mainloop()
