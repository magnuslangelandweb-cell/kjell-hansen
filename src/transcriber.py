"""faster-whisper wrapper with GPU auto-detect and CPU int8 fallback."""
import logging

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class Transcriber:
    def __init__(
        self,
        model_size: str = "small.en",
        device: str = "auto",
        compute_type_cpu: str = "int8",
        compute_type_gpu: str = "float16",
        language: str = "en",
    ):
        self.model_size = model_size
        self.language = language
        self.model, self.active_device = self._load_model(
            model_size, device, compute_type_cpu, compute_type_gpu
        )

    @staticmethod
    def _load_model(model_size, device, compute_type_cpu, compute_type_gpu):
        """Try CUDA first when requested/auto, fall back to CPU int8 on any failure.

        faster-whisper only accelerates via CUDA (CTranslate2 has no ROCm/Vulkan
        backend), so on AMD or any non-NVIDIA GPU this will always land on CPU.
        """
        if device in ("auto", "cuda"):
            try:
                model = WhisperModel(
                    model_size, device="cuda", compute_type=compute_type_gpu
                )
                logger.info("Loaded %s on CUDA GPU", model_size)
                return model, "cuda"
            except Exception as exc:
                if device == "cuda":
                    raise
                logger.info("CUDA unavailable (%s), falling back to CPU", exc)

        model = WhisperModel(model_size, device="cpu", compute_type=compute_type_cpu)
        logger.info("Loaded %s on CPU (%s)", model_size, compute_type_cpu)
        return model, "cpu"

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""

        segments, _info = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return "".join(segment.text for segment in segments).strip()
