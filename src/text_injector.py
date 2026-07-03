"""Types transcribed text into whatever window currently has focus.

Default strategy (matches how Wispr Flow itself injects text): save the
current clipboard, put the transcript on the clipboard, simulate Ctrl+V via
SendInput, then restore the original clipboard shortly after. Some elevated
apps, games with raw-input capture, and RDP sessions block synthetic paste;
for those, `injection_method: "type"` falls back to typing each character
directly via SendInput's Unicode key events (slower, but bypasses paste
blocking).

Windows-only module - imports fail fast and loudly on other platforms rather
than pretending to work.
"""
import ctypes
import time
from ctypes import wintypes

import win32clipboard

# --- SendInput plumbing (ctypes) -------------------------------------------

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_CONTROL = 0x11
VK_V = 0x56

ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUT_UNION)]


def _send_key_event(vk: int = 0, scan: int = 0, flags: int = 0) -> None:
    inp = INPUT(type=INPUT_KEYBOARD, union=_INPUT_UNION(ki=KEYBDINPUT(vk, scan, flags, 0, 0)))
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def _send_ctrl_v() -> None:
    _send_key_event(vk=VK_CONTROL, flags=0)
    _send_key_event(vk=VK_V, flags=0)
    _send_key_event(vk=VK_V, flags=KEYEVENTF_KEYUP)
    _send_key_event(vk=VK_CONTROL, flags=KEYEVENTF_KEYUP)


def _type_unicode_text(text: str) -> None:
    for ch in text:
        code = ord(ch)
        _send_key_event(scan=code, flags=KEYEVENTF_UNICODE)
        _send_key_event(scan=code, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
        time.sleep(0.002)


# --- Clipboard helpers -------------------------------------------------------

def _read_clipboard_text():
    win32clipboard.OpenClipboard()
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        return None
    finally:
        win32clipboard.CloseClipboard()


def _write_clipboard_text(text: str) -> None:
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()


# --- Public API ---------------------------------------------------------------

def inject_text(text: str, method: str = "paste", restore_delay: float = 0.25) -> None:
    if not text:
        return

    if method == "type":
        _type_unicode_text(text)
        return

    previous = None
    try:
        previous = _read_clipboard_text()
    except Exception:
        previous = None

    _write_clipboard_text(text)
    time.sleep(0.05)  # give the OS a moment to register the new clipboard content
    _send_ctrl_v()

    if previous is not None:
        time.sleep(restore_delay)
        try:
            _write_clipboard_text(previous)
        except Exception:
            pass
