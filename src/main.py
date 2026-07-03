"""Entry point: wires the tray icon, hotkey listener, recorder, transcriber, and
text injector together into a push-to-talk local dictation app.
"""
import logging
import threading

from logging_setup import setup_logging

setup_logging()

from config import load_config
from audio_recorder import AudioRecorder
from formatting import clean_transcript
from hotkey_listener import HotkeyListener
from text_injector import inject_text
from tray_app import TrayApp
from transcriber import Transcriber

logger = logging.getLogger(__name__)


class DictationApp:
    def __init__(self):
        self.config = load_config()
        self.recorder = AudioRecorder(sample_rate=self.config["sample_rate"])
        self.tray = TrayApp(on_quit=self._on_quit, on_reload_config=self._on_reload_config)
        self.transcriber = None
        self.hotkey = None
        self._notified_not_ready = False

    def _load_model_async(self) -> None:
        def _load():
            self.tray.set_loading()
            logger.info("Loading Whisper model '%s'...", self.config["model_size"])
            try:
                transcriber = Transcriber(
                    model_size=self.config["model_size"],
                    device=self.config["device"],
                    compute_type_cpu=self.config["compute_type_cpu"],
                    compute_type_gpu=self.config["compute_type_gpu"],
                    language=self.config["language"],
                )
            except Exception as exc:
                logger.exception("Model failed to load")
                self.tray.set_error(f"Model failed to load: {exc}")
                return

            self.transcriber = transcriber
            self._notified_not_ready = False
            logger.info("Model ready on device: %s", transcriber.active_device)
            self.tray.set_ready(transcriber.active_device)
            self.tray.notify(
                f"Ready on {transcriber.active_device.upper()}. Hold '{self.config['hotkey']}' to dictate.",
                title="Local Dictation",
            )

        threading.Thread(target=_load, daemon=True).start()

    def _start_hotkey(self) -> None:
        if self.hotkey is not None:
            self.hotkey.stop()
        try:
            self.hotkey = HotkeyListener(
                hotkey=self.config["hotkey"],
                on_press=self._on_hotkey_press,
                on_release=self._on_hotkey_release,
            )
            self.hotkey.start()
        except Exception as exc:
            logger.exception("Failed to register hotkey '%s'", self.config["hotkey"])
            self.tray.set_error(f"Hotkey registration failed: {exc}")

    def _on_hotkey_press(self) -> None:
        if self.transcriber is None:
            if not self._notified_not_ready:
                self._notified_not_ready = True
                self.tray.notify("Model is still loading, please wait a moment.")
            return
        try:
            self.recorder.start()
        except Exception as exc:
            logger.exception("Failed to start recording")
            self.tray.set_error(f"Microphone error: {exc}")
            return
        self.tray.set_recording(True)

    def _on_hotkey_release(self) -> None:
        if not self.recorder.is_recording:
            return
        audio = self.recorder.stop()
        self.tray.set_recording(False)

        duration = self.recorder.duration_seconds(audio)
        if duration < self.config["min_recording_seconds"]:
            return

        threading.Thread(target=self._transcribe_and_inject, args=(audio,), daemon=True).start()

    def _transcribe_and_inject(self, audio) -> None:
        try:
            raw_text = self.transcriber.transcribe(audio)
            text = clean_transcript(raw_text)
            if text:
                inject_text(text, method=self.config["injection_method"])
                logger.info("Injected %d characters", len(text))
        except Exception as exc:
            logger.exception("Transcription/injection failed")
            self.tray.notify(f"Dictation failed: {exc}", title="Local Dictation error")

    def _on_reload_config(self) -> None:
        logger.info("Reloading config.json")
        self.config = load_config()
        self._start_hotkey()
        self.tray.notify(f"Config reloaded. Hotkey: {self.config['hotkey']}")

    def _on_quit(self) -> None:
        if self.hotkey is not None:
            self.hotkey.stop()

    def run(self) -> None:
        self._load_model_async()
        self._start_hotkey()
        self.tray.run()  # blocks until Quit is clicked


if __name__ == "__main__":
    DictationApp().run()
