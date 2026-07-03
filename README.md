# Local Dictation (Wispr Flow clone)

A private, fully local, $0 voice-dictation tool for Windows 10/11. Hold a
hotkey, speak, release — the transcribed text is typed directly into
whatever app or text field currently has focus. No cloud calls, no
telemetry, no API keys, no subscriptions.

## How it works

1. Hold **Right Ctrl** (configurable) → microphone starts recording, a small
   "🎙 Recording..." indicator appears near the bottom-right of the screen.
2. Release the key → recording stops and is transcribed locally with
   [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (an optimized
   Whisper implementation).
3. The transcribed text is copied to the clipboard and pasted (Ctrl+V) into
   whichever window currently has focus, then your previous clipboard
   contents are restored.

This is push-to-talk, not always-on streaming — the same model Wispr Flow
itself uses. It keeps the pipeline simple: no need for live streaming ASR,
just fast batch transcription of a few seconds of audio.

## Setup plan

**Dependencies** (all free/open-source, installed by `setup.ps1`):
- Python 3.10+
- [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) — the transcription engine (CTranslate2-based)
- `sounddevice` — microphone capture
- `keyboard` — global push-to-talk hotkey
- `pywin32` — Windows clipboard + `SendInput` access for text injection
- `pystray` + `Pillow` — system tray icon
- (optional, only for building a standalone `.exe`) `PyInstaller`

**Model download**: handled automatically. The first time you hold the
hotkey and speak, `faster-whisper` downloads the configured model (default
`small.en`, ~150 MB) from Hugging Face into a local cache — no manual step
needed. Everything after that first download runs fully offline.

**Folder structure**:
```
.
├── README.md
├── requirements.txt
├── config.example.json     # copied to config.json on first run
├── setup.ps1                # one-time environment setup
├── build_exe.ps1             # optional: build a standalone .exe
└── src/
    ├── main.py               # entry point, wires everything together
    ├── config.py             # load/save config.json
    ├── hotkey_listener.py     # push-to-talk hold/release detection
    ├── audio_recorder.py      # microphone capture
    ├── transcriber.py         # faster-whisper wrapper (GPU/CPU auto-detect)
    ├── formatting.py          # light text cleanup (capitalization, punctuation)
    ├── text_injector.py       # clipboard + simulated paste into the focused window
    └── tray_app.py            # system tray icon + recording indicator
```

## Step-by-step build walkthrough

### 1. Installer / setup script

Run in PowerShell from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

This creates a `.venv`, installs everything in `requirements.txt`, and
copies `config.example.json` → `config.json` (edit this file to change the
hotkey, model size, or injection method).

Then run the app:

```powershell
.\.venv\Scripts\python.exe src\main.py
```

A tray icon appears (blue = idle, red = recording). Hold Right Ctrl, speak,
release, and the text should appear wherever your cursor was focused.

### 2. The hotkey listener (`src/hotkey_listener.py`)

Uses the `keyboard` package's low-level Windows keyboard hook to detect
key-down and key-up for a single configurable key (default: Right Ctrl).
It debounces OS key-repeat so a held key only fires one "press" event.

**Known limitation**: Windows blocks low-privilege input hooks from seeing
keystrokes destined for *elevated* (Run as Administrator) windows. If you
need dictation to work inside an elevated app, run this tray app itself as
Administrator too.

### 3. The transcription pipeline (`src/transcriber.py`)

Wraps `faster_whisper.WhisperModel`. On startup it tries to load the model
on CUDA; if that fails (no NVIDIA GPU, or on an AMD/Intel GPU) it falls back
to CPU with `int8` quantization, which is fast enough for short push-to-talk
clips (typically 1-3 seconds to transcribe 5-10 seconds of speech on a
modern CPU).

**Model size / engine choice, and why:** the target machine has an AMD GPU.
`faster-whisper`'s backend (CTranslate2) only accelerates via CUDA — there is
no ROCm or Vulkan backend, so on AMD it always runs on CPU regardless of the
`device` setting. The alternative engine, `whisper.cpp`, does support Vulkan
(works on any GPU vendor), but as of this writing the official
`whisper.cpp` Windows releases don't ship a prebuilt Vulkan binary — you'd
need to compile it yourself with the Vulkan SDK + CMake, or trust an
unofficial third-party build. Given that tradeoff, this project defaults to
`faster-whisper` on CPU: it installs with a single `pip install`, needs no
compiler toolchain, and `small.en` at `int8` is genuinely fast enough for
push-to-talk dictation on any reasonably modern CPU.

Default model is `small.en` — a good latency/accuracy balance for short
dictation clips. Change `model_size` in `config.json`:

| Model | Speed (CPU) | Accuracy | When to use |
|---|---|---|---|
| `base.en` | fastest | lower | older/slower CPU, want snappiest response |
| `small.en` | fast | good | **default** — best balance for dictation |
| `medium.en` | slower | better | willing to trade latency for accuracy |
| `distil-large-v3` | medium | near-large accuracy, ~5x faster than large | best accuracy still viable on CPU |

#### Optional: GPU acceleration on AMD (advanced)

If CPU transcription feels too slow, you can get real GPU acceleration on
an AMD card via `whisper.cpp` + Vulkan, at the cost of a manual build:

1. Install the [Vulkan SDK](https://vulkan.lunarg.com/) and CMake.
2. Clone [`ggml-org/whisper.cpp`](https://github.com/ggml-org/whisper.cpp) and build with:
   ```powershell
   cmake -B build -DGGML_VULKAN=1
   cmake --build build --config Release
   ```
3. Download a quantized `ggml` model (e.g. `small.en-q5_1`) into `whisper.cpp/models`.
4. Swap `src/transcriber.py`'s implementation for a `subprocess` call to the
   built `whisper-cli.exe`, piping in the recorded WAV and reading the
   printed transcript back — the rest of the pipeline (hotkey, recorder,
   injector) is unchanged.

This is left as an opt-in path rather than the default because it depends
on a working local compiler toolchain and isn't officially supported by the
whisper.cpp project's release binaries yet.

### 4. The text-injection mechanism (`src/text_injector.py`)

This is the same approach Wispr Flow itself uses: save your current
clipboard contents, put the transcript on the clipboard, simulate Ctrl+V
via the Windows `SendInput` API, then restore your original clipboard a
moment later. This is far more reliable than simulating individual
keystrokes for arbitrary Unicode text (emoji, accents, etc.) and works
across virtually all normal desktop apps, browsers, and editors.

If paste doesn't work in a specific app (some elevated apps, some games,
some RDP sessions block synthetic paste), set `"injection_method": "type"`
in `config.json` to fall back to direct character-by-character typing via
`SendInput`'s Unicode key events — slower, but bypasses paste blocking.

### 5. Packaging as a background tray app

```powershell
powershell -ExecutionPolicy Bypass -File build_exe.ps1
```

Produces `dist\LocalDictation.exe` — a single-file, no-console-window
executable (via PyInstaller `--noconsole --onefile`). The Whisper model is
**not** bundled into the exe (that would bloat it and slow down startup
extraction); it downloads on first use, same as running from source.

To run automatically at login: press `Win+R`, type `shell:startup`, and
drop a shortcut to `LocalDictation.exe` in the folder that opens.

## Configuration reference (`config.json`)

| Key | Default | Meaning |
|---|---|---|
| `hotkey` | `"right ctrl"` | Any key name recognized by the `keyboard` package |
| `model_size` | `"small.en"` | Whisper model size/variant |
| `device` | `"auto"` | `"auto"`, `"cuda"`, or `"cpu"` |
| `injection_method` | `"paste"` | `"paste"` (clipboard+Ctrl+V) or `"type"` (direct Unicode typing) |
| `min_recording_seconds` | `0.15` | Ignore accidental taps shorter than this |
| `max_recording_seconds` | `60` | Safety cap on a single recording |
| `show_recording_indicator` | `true` | Show the on-screen "Recording..." overlay |

## Troubleshooting

- **Nothing gets pasted**: the target app may be running elevated, or is
  blocking synthetic input. Try `"injection_method": "type"` in
  `config.json`, or run the tray app as Administrator.
- **Hotkey doesn't trigger in some app**: same elevation issue — see above.
- **Transcription is slow**: switch `model_size` to `"base.en"` in
  `config.json`, or see the AMD GPU section above for the Vulkan path.
- **No microphone detected**: check Windows Settings → Privacy & security →
  Microphone, and confirm the correct input device is set as default in
  Windows Sound settings (this app uses the system default input device).
- **First run is slow**: that's the one-time model download; subsequent
  runs are fully offline and fast.

## Manual test checklist

Since this has to run on real Windows hardware with a real microphone, after
`setup.ps1`:

1. `python src\main.py` — confirm a tray icon appears.
2. Open Notepad, click into it, hold Right Ctrl, say a sentence, release.
3. Confirm the text appears in Notepad, capitalized with trailing punctuation.
4. Repeat in a browser address bar and a chat app (e.g. Slack/Discord) to
   confirm paste-based injection works broadly.
5. Try `"injection_method": "type"` and repeat step 2-3 to confirm the
   fallback path also works.
6. Quit via the tray icon's Quit menu item and confirm the process exits
   cleanly.
