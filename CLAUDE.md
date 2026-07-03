# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Local Dictation — a private, fully local, $0 push-to-talk voice-dictation tool for Windows 10/11 (a Wispr Flow clone). Hold a hotkey, speak, release, and the transcribed text is pasted directly into whatever window has focus. No cloud calls, no telemetry, no API keys. Transcription runs locally via `faster-whisper`.

This is a small, single-purpose Python script/tray-app project, not a library or service — there's no test suite, build system, or CI. Windows is the only supported target platform (the code uses `pywin32` and Win32 `SendInput` directly).

## Setup and running

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1      # creates .venv, installs requirements.txt, copies config.example.json -> config.json
.\.venv\Scripts\python.exe src\main.py                   # run the app (tray icon appears)
powershell -ExecutionPolicy Bypass -File build_exe.ps1    # optional: PyInstaller --onefile --noconsole build -> dist\LocalDictation.exe
```

There is no test suite, linter, or formatter configured in this repo. Validation is manual (see "Manual test checklist" in README.md): run the app, hold the hotkey in a real text field, speak, and confirm the transcribed text is pasted correctly. This requires real Windows hardware with a microphone — it cannot be verified from a headless/non-Windows environment.

## Architecture

`src/main.py`'s `DictationApp` wires together five independent, single-responsibility modules with no shared state beyond what's passed explicitly. The flow on every push-to-talk cycle:

1. **`hotkey_listener.py`** (`HotkeyListener`) — low-level Windows keyboard hook (`keyboard` package) fires `on_press`/`on_release` exactly once per physical hold, debouncing OS key-repeat.
2. **`audio_recorder.py`** (`AudioRecorder`) — on press, opens a `sounddevice` input stream and accumulates frames in a background callback; on release, stops the stream and returns the concatenated mono `float32` array.
3. **`transcriber.py`** (`Transcriber`) — wraps `faster_whisper.WhisperModel`. Loaded once, lazily, in a background thread at startup (so the tray icon appears immediately instead of blocking on model load/download). Tries CUDA first when `device` is `"auto"`/`"cuda"`, falls back to CPU `int8` on any failure. Note: CTranslate2 (faster-whisper's backend) has no ROCm/Vulkan support, so non-NVIDIA GPUs always land on CPU regardless of config — see README.md for the whisper.cpp/Vulkan alternative if that's ever revisited.
4. **`formatting.py`** (`clean_transcript`) — light safety-net post-processing: capitalize first letter, ensure trailing punctuation.
5. **`text_injector.py`** (`inject_text`) — Windows-only, ctypes-based. Default `"paste"` method: save current clipboard → write transcript to clipboard → simulate Ctrl+V via `SendInput` → restore original clipboard after a delay. Fallback `"type"` method: type each Unicode character directly via `SendInput` key events (slower, but works where synthetic paste is blocked, e.g. some elevated apps/games/RDP).

`tray_app.py` (`TrayApp`) owns the `pystray` tray icon (blue = idle, red = recording) and a borderless always-on-top Tkinter "🎙 Recording..." indicator; `main.py` calls `tray.set_recording(bool)` around each capture.

`config.py` loads `config.json` (auto-created from `config.example.json` on first run), merging saved values over `DEFAULTS` so new keys added to `DEFAULTS` don't break existing user configs.

Threading model: hotkey callbacks run on the `keyboard` library's hook thread; transcription+injection runs on its own daemon thread per utterance (`_transcribe_and_inject`) so it never blocks the hotkey listener or tray event loop; the tray icon's `run()` blocks the main thread until Quit.

## Key conventions

- Each `src/` module is a thin, independent wrapper around one OS/library concern (keyboard hook, audio stream, ASR model, clipboard+SendInput, tray icon). Keep that separation — `main.py` is the only place that coordinates across them.
- `text_injector.py` is intentionally Windows-only and fails fast/loudly on import elsewhere; don't add cross-platform shims to it.
- Config keys live in exactly two places that must stay in sync: `config.py`'s `DEFAULTS` dict and `config.example.json`. When adding a new config option, update both, plus the reference table in README.md.
- `.gitignore` excludes `config.json` (user-local, generated from the example) and `models/` (Whisper model cache) — never commit either.
