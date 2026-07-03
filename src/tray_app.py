"""System tray icon (pystray) plus a small always-on-top recording indicator (Tkinter)."""
import threading

import pystray
from PIL import Image, ImageDraw


def _make_icon_image(color: str) -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 8
    draw.ellipse((margin, margin, size - margin, size - margin), fill=color)
    return img


class TrayApp:
    def __init__(self, on_quit=None):
        self._on_quit = on_quit
        self._idle_image = _make_icon_image("#4a90d9")
        self._recording_image = _make_icon_image("#d94a4a")
        self._icon = pystray.Icon(
            "wisper_clone",
            self._idle_image,
            "Local Dictation (idle)",
            menu=pystray.Menu(pystray.MenuItem("Quit", self._quit)),
        )
        self._indicator = _RecordingIndicator()

    def _quit(self, _icon=None, _item=None) -> None:
        self._indicator.stop()
        self._icon.stop()
        if self._on_quit:
            self._on_quit()

    def set_recording(self, recording: bool) -> None:
        self._icon.icon = self._recording_image if recording else self._idle_image
        self._icon.title = "Local Dictation (recording...)" if recording else "Local Dictation (idle)"
        if recording:
            self._indicator.show()
        else:
            self._indicator.hide()

    def run(self) -> None:
        self._indicator.start()
        self._icon.run()


class _RecordingIndicator:
    """A tiny always-on-top borderless window shown only while recording."""

    def __init__(self):
        self._root = None
        self._label = None
        self._ready = threading.Event()

    def start(self) -> None:
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        self._ready.wait(timeout=2)

    def _run_loop(self) -> None:
        import tkinter as tk

        self._root = tk.Tk()
        self._root.withdraw()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        try:
            self._root.attributes("-alpha", 0.9)
        except Exception:
            pass

        self._label = tk.Label(
            self._root,
            text="\U0001F399 Recording...",
            bg="#222222",
            fg="#ffffff",
            padx=12,
            pady=6,
            font=("Segoe UI", 10),
        )
        self._label.pack()

        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        self._root.geometry(f"+{screen_w - 220}+{screen_h - 100}")

        self._ready.set()
        self._root.mainloop()

    def show(self) -> None:
        if self._root:
            self._root.after(0, self._root.deiconify)

    def hide(self) -> None:
        if self._root:
            self._root.after(0, self._root.withdraw)

    def stop(self) -> None:
        if self._root:
            self._root.after(0, self._root.quit)
