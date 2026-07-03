"""System tray icon (pystray) plus a small always-on-top recording indicator (Tkinter)."""
import logging
import os
import threading

import pystray
from PIL import Image, ImageDraw

from paths import CONFIG_PATH, LOGS_DIR

logger = logging.getLogger(__name__)


def _make_icon_image(color: str) -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 8
    draw.ellipse((margin, margin, size - margin, size - margin), fill=color)
    return img


class TrayApp:
    def __init__(self, on_quit=None, on_reload_config=None):
        self._on_quit = on_quit
        self._on_reload_config = on_reload_config
        self._loading_image = _make_icon_image("#b0b0b0")
        self._idle_image = _make_icon_image("#4a90d9")
        self._recording_image = _make_icon_image("#d94a4a")
        self._error_image = _make_icon_image("#e0a800")
        self._icon = pystray.Icon(
            "wisper_clone",
            self._loading_image,
            "Local Dictation (starting...)",
            menu=pystray.Menu(
                pystray.MenuItem("Open config.json", self._open_config),
                pystray.MenuItem("Open logs folder", self._open_logs),
                pystray.MenuItem("Reload config", self._reload_config),
                pystray.MenuItem("Quit", self._quit),
            ),
        )
        self._indicator = _RecordingIndicator()

    # --- state changes -----------------------------------------------------

    def set_loading(self) -> None:
        self._icon.icon = self._loading_image
        self._icon.title = "Local Dictation (loading model...)"

    def set_ready(self, device: str) -> None:
        self._icon.icon = self._idle_image
        self._icon.title = f"Local Dictation (ready, {device})"

    def set_error(self, message: str) -> None:
        self._icon.icon = self._error_image
        self._icon.title = f"Local Dictation (error: {message[:60]})"
        self.notify(message, title="Local Dictation error")

    def set_recording(self, recording: bool) -> None:
        self._icon.icon = self._recording_image if recording else self._idle_image
        self._icon.title = "Local Dictation (recording...)" if recording else self._icon.title
        if recording:
            self._indicator.show()
        else:
            self._indicator.hide()

    def notify(self, message: str, title: str = "Local Dictation") -> None:
        try:
            self._icon.notify(message, title)
        except Exception:
            logger.warning("Tray notify failed: %s", message)

    # --- menu callbacks ------------------------------------------------------

    def _open_config(self, _icon=None, _item=None) -> None:
        try:
            os.startfile(CONFIG_PATH)
        except Exception:
            logger.exception("Could not open config.json")

    def _open_logs(self, _icon=None, _item=None) -> None:
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(LOGS_DIR)
        except Exception:
            logger.exception("Could not open logs folder")

    def _reload_config(self, _icon=None, _item=None) -> None:
        if self._on_reload_config:
            self._on_reload_config()

    def _quit(self, _icon=None, _item=None) -> None:
        self._indicator.stop()
        self._icon.stop()
        if self._on_quit:
            self._on_quit()

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
