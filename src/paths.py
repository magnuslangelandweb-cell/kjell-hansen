"""Central place for filesystem paths, correct both running from source and
running as a PyInstaller-frozen .exe.

When frozen, `__file__`-based paths point into the temporary _MEIxxxxxx
extraction folder, not the folder the .exe actually lives in - config.json
and logs would silently vanish between runs if we used that. sys.executable
is the fix: it always points at the real .exe location when frozen.
"""
import sys
from pathlib import Path


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


APP_DIR = get_app_dir()
LOGS_DIR = APP_DIR / "logs"
MODELS_DIR = APP_DIR / "models"
CONFIG_PATH = APP_DIR / "config.json"
