"""Load/save the app's JSON config, seeded from config.example.json on first run."""
import json
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config.json"
EXAMPLE_CONFIG_PATH = ROOT_DIR / "config.example.json"

DEFAULTS = {
    "hotkey": "right ctrl",
    "model_size": "small.en",
    "device": "auto",
    "compute_type_cpu": "int8",
    "compute_type_gpu": "float16",
    "sample_rate": 16000,
    "min_recording_seconds": 0.15,
    "max_recording_seconds": 60,
    "injection_method": "paste",
    "language": "en",
    "show_recording_indicator": True,
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        if EXAMPLE_CONFIG_PATH.exists():
            shutil.copy(EXAMPLE_CONFIG_PATH, CONFIG_PATH)
        else:
            save_config(DEFAULTS)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    merged = {**DEFAULTS, **config}
    return merged


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
