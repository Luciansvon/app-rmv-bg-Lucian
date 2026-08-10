"""Source-pixel mask editor used by image and static-video workflows."""

from dataclasses import dataclass
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk


@dataclass(frozen=True)
class _MaskOperation:
    kind: str
    points: tuple
    width: int = 1
    erase: bool = False


class MaskCanvas(ctk.CTkFrame):
    """Canvas that keeps mask coordinates in original-image pixels."""

    def __init__(self, parent, change_callback=None, **kwargs):
        super().__init__(parent, fg_color="#10151a", **kwargs)
        self._change_callback = change_callback
        self.canvas = tk.Canvas(
            self,
            bg="#10151a",
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        self._image = None
        self._mask = None
        self._photo = None
        self._overlay_photo = None
        self._display_box = (0, 0, 0, 0)
        self._display_scale = 1.0
        self._zoom = 1.0
        self._tool = "brush"
        self._brush_size = 50
        self._active_points = []
        self._active_start = None
        self._operations = []
        self._history = []
        self._redo_stack = []
        self._render_job = None

    def set_image(self, image):
        if image is None:
            self._image = None
            self._mask = None
            self._operations = []
            self._history = []
            self._redo_stack = []
            self._render()
            self._notify_change()
            return
        if not isinstance(image, Image.Image):
            raise TypeError("MaskCanvas membutuhkan PIL.Image.")
        self._image = image.copy()
        self._mask = Image.new("L", self._image.size, 0)
        self._operations = []
        self._history = []
        self._redo_stack = []
        self._zoom = 1.0
        self._schedule_render()
        self._notify_change()

    def set_tool(self, tool):
        if tool not in {"brush", "rectangle", "eraser"}:
            raise ValueError("Tool mask harus brush, rectangle, atau eraser.")
        self._tool = tool
        self.canvas.configure(cursor="crosshair" if tool != "eraser" else "circle")

    def set_brush_size(self, size):
        self._brush_size = max(1, int(size))

    def set_zoom(self, zoom):
        self._zoom = max(0.25, min(4.0, float(zoom)))
        self._schedule_render()

    def zoom_in(self):
        self.set_zoom(self._zoom * 1.25)

    def zoom_out(self):
        self.set_zoom(self._zoom / 1.25)

    def clear_mask(self):
        if not self._operations:
            return
        self._history.append(list(self._operations))
        self._redo_stack = []
        self._operations = []
        self._rebuild_mask()
        self._schedule_render()
        self._notify_change()

    reset_mask = clear_mask

    def undo(self):
        if not self._history:
            return
        self._redo_stack.append(list(self._operations))
        self._operations = self._history.pop()
        self._rebuild_mask()
        self._schedule_render()
        self._notify_change()

    def redo(self):
        if not self._redo_stack:
            return
        self._history.append(list(self._operations))
        self._operations = self._redo_stack.pop()
        self._rebuild_mask()
        self._schedule_render()
        self._notify_change()

    def get_source_mask(self):
        if self._mask is None:
            return Image.new("L", (1, 1), 0)
        return self._mask.copy()

    def has_mask(self):
        return self._mask is not None and self._mask.getbbox() is not None

    def region_count(self):
        return sum(1 for operation in self._operations if operation.kind in {"brush", "rectangle"})

    def _notify_change(self):
        if self._change_callback is not None:
            self._change_callback()

    def _on_resize(self, _event):
        self._schedule_render()

    def _schedule_render(self):
        if self._render_job is None:
            self._render_job = self.after(30, self._render)

    def _render(self):
        self._render_job = None
        self.canvas.delete("all")
        if self._image is None:
            self.canvas.create_text(
                max(1, self.canvas.winfo_width() // 2),
                max(1, self.canvas.winfo_height() // 2),
                text="Pilih gambar atau video untuk membuat mask",
                fill="#8f9aa3",
                font=("Segoe UI", 12),
            )
            return
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        source_width, source_height = self._image.size
        fit = min(width / source_width, height / source_height)
        scale = max(0.05, fit * self._zoom)
        display_width = max(1, int(source_width * scale))
        display_height = max(1, int(source_height * scale))
        offset_x = (width - display_width) // 2
        offset_y = (height - display_height) // 2
        self._display_box = (offset_x, offset_y, display_width, display_height)
        self._display_scale = scale

        source = self._image.convert("RGBA").resize(
            (display_width, display_height), Image.Resampling.LANCZOS
        )
        if self._mask is not None and self._mask.getbbox() is not None:
            overlay = Image.new("RGBA", (display_width, display_height), (239, 91, 115, 0))
            alpha = self._mask.resize((display_width, display_height), Image.Resampling.NEAREST)
            overlay.putalpha(alpha.point(lambda value: int(value * 0.55)))
            source = Image.alpha_composite(source, overlay)
        self._photo = ImageTk.PhotoImage(source)
        self.canvas.create_image(offset_x, offset_y, image=self._photo, anchor="nw")
        if self._tool == "rectangle" and len(self._active_points) >= 2:
            start = self._source_to_canvas(self._active_points[0])
            end = self._source_to_canvas(self._active_points[-1])
            if start is not None and end is not None:
                self.canvas.create_rectangle(
                    *start, *end, outline="#ef5b73", width=2, dash=(5, 3)
                )

    def _canvas_to_source(self, x, y):
        offset_x, offset_y, display_width, display_height = self._display_box
        if display_width <= 0 or display_height <= 0 or self._image is None:
            return None
        source_x = (x - offset_x) / self._display_scale
        source_y = (y - offset_y) / self._display_scale
        if source_x < 0 or source_y < 0 or source_x >= self._image.width or source_y >= self._image.height:
            return None
        return (
            max(0, min(self._image.width - 1, int(source_x))),
            max(0, min(self._image.height - 1, int(source_y))),
        )

    def _source_to_canvas(self, point):
        if self._image is None or point is None:
            return None
        offset_x, offset_y, _display_width, _display_height = self._display_box
        return (
            offset_x + point[0] * self._display_scale,
            offset_y + point[1] * self._display_scale,
        )

    def _on_press(self, event):
        point = self._canvas_to_source(event.x, event.y)
        if point is None:
            return
        self._active_start = point
        self._active_points = [point]
        if self._tool in {"brush", "eraser"}:
            self._paint_segment(point, point, erase=self._tool == "eraser")
            self._schedule_render()

    def _on_motion(self, event):
        point = self._canvas_to_source(event.x, event.y)
        if point is None or self._active_start is None:
            return
        if self._tool in {"brush", "eraser"}:
            previous = self._active_points[-1]
            self._active_points.append(point)
            self._paint_segment(previous, point, erase=self._tool == "eraser")
            self._schedule_render()
        else:
            self._active_points = [self._active_start, point]
            self._schedule_render()

    def _on_release(self, event):
        point = self._canvas_to_source(event.x, event.y)
        if point is None and self._active_points:
            point = self._active_points[-1]
        if point is not None and self._active_start is not None:
            if self._tool == "rectangle":
                self._active_points = [self._active_start, point]
                operation = _MaskOperation("rectangle", tuple(self._active_points), self._brush_size, False)
                self._commit_operation(operation)
            elif self._tool in {"brush", "eraser"} and self._active_points:
                operation = _MaskOperation(
                    "brush",
                    tuple(self._active_points),
                    self._brush_size,
                    self._tool == "eraser",
                )
                self._commit_operation(operation)
        self._active_start = None
        self._active_points = []
        self._schedule_render()

    def _paint_segment(self, start, end, erase=False):
        if self._mask is None:
            return
        draw = ImageDraw.Draw(self._mask)
        fill = 0 if erase else 255
        width = max(1, int(self._brush_size))
        draw.line([start, end], fill=fill, width=width, joint="curve")
        radius = width // 2
        for x, y in (start, end):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)

    def _commit_operation(self, operation):
        self._history.append(list(self._operations))
        self._redo_stack = []
        self._operations.append(operation)
        self._rebuild_mask()
        self._notify_change()

    def _rebuild_mask(self):
        if self._image is None:
            return
        self._mask = Image.new("L", self._image.size, 0)
        for operation in self._operations:
            draw = ImageDraw.Draw(self._mask)
            fill = 0 if operation.erase else 255
            if operation.kind == "rectangle" and len(operation.points) >= 2:
                draw.rectangle((*operation.points[0], *operation.points[-1]), fill=fill)
            elif operation.kind == "brush" and operation.points:
                width = max(1, int(operation.width))
                if len(operation.points) == 1:
                    x, y = operation.points[0]
                    radius = width // 2
                    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)
                else:
                    draw.line(operation.points, fill=fill, width=width, joint="curve")
                    radius = width // 2
                    for x, y in (operation.points[0], operation.points[-1]):
                        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)
