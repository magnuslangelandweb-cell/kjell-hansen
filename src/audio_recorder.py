"""Microphone capture for push-to-talk: start on key-down, stop on key-up."""
import threading

import numpy as np
import sounddevice as sd


class AudioRecorder:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._frames = []
        self._stream = None
        self._lock = threading.Lock()
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=self._on_audio,
            )
            self._stream.start()

    def _on_audio(self, indata, frames, time_info, status):
        with self._lock:
            if self._recording:
                self._frames.append(indata.copy())

    def stop(self) -> np.ndarray:
        """Stop recording and return the captured audio as a mono float32 array."""
        with self._lock:
            if not self._recording:
                return np.array([], dtype=np.float32)
            self._recording = False
            stream = self._stream
            self._stream = None

        if stream is not None:
            stream.stop()
            stream.close()

        with self._lock:
            frames = self._frames
            self._frames = []

        if not frames:
            return np.array([], dtype=np.float32)

        return np.concatenate(frames, axis=0).flatten()

    def duration_seconds(self, audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0
        return audio.shape[0] / self.sample_rate
