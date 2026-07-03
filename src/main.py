"""Entry point: wires the tray icon, hotkey listener, recorder, transcriber, and
text injector together into a push-to-talk local dictation app.
"""
import logging
import threading

from config import load_config
from audio_recorder import AudioRecorder
from formatting import clean_transcript
from hotkey_listener import HotkeyListener
from text_injector import inject_text
from tray_app import TrayApp
from transcriber import Transcriber

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class DictationApp:
    def __init__(self):
        self.config = load_config()
        self.recorder = AudioRecorder(sample_rate=self.config["sample_rate"])
        self.tray = TrayApp(on_quit=self._on_quit)
        self.transcriber = None  # loaded lazily in the background so the tray shows up fast
        self.hotkey = HotkeyListener(
            hotkey=self.config["hotkey"],
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )

    def _load_model_async(self) -> None:
        def _load():
            logger.info("Loading Whisper model '%s'...", self.config["model_size"])
            self.transcriber = Transcriber(
                model_size=self.config["model_size"],
                device=self.config["device"],
                compute_type_cpu=self.config["compute_type_cpu"],
                compute_type_gpu=self.config["compute_type_gpu"],
                language=self.config["language"],
            )
            logger.info("Model ready on device: %s", self.transcriber.active_device)

        threading.Thread(target=_load, daemon=True).start()

    def _on_hotkey_press(self) -> None:
        if self.transcriber is None:
            logger.info("Model still loading, ignoring press")
            return
        self.recorder.start()
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
        except Exception:
            logger.exception("Transcription/injection failed")

    def _on_quit(self) -> None:
        self.hotkey.stop()

    def run(self) -> None:
        self._load_model_async()
        self.hotkey.start()
        self.tray.run()  # blocks until Quit is clicked


if __name__ == "__main__":
    DictationApp().run()
