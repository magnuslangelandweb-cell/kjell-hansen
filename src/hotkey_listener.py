"""Global push-to-talk hotkey: fires on_press once on key-down, on_release once on key-up.

Uses the `keyboard` library's low-level Windows hook. Note: this hook does not
receive events from elevated target windows unless this process itself is run
as Administrator - that's a Windows UIPI limitation, not a bug here.
"""
import logging

import keyboard

logger = logging.getLogger(__name__)


class HotkeyListener:
    def __init__(self, hotkey: str, on_press, on_release):
        self.hotkey = hotkey
        self._on_press = on_press
        self._on_release = on_release
        self._is_down = False

    def start(self) -> None:
        keyboard.on_press_key(self.hotkey, self._handle_press, suppress=False)
        keyboard.on_release_key(self.hotkey, self._handle_release, suppress=False)
        logger.info("Listening for push-to-talk hotkey: %s", self.hotkey)

    def stop(self) -> None:
        keyboard.unhook_all()

    def _handle_press(self, _event) -> None:
        if self._is_down:
            return  # ignore OS key-repeat while held
        self._is_down = True
        self._on_press()

    def _handle_release(self, _event) -> None:
        if not self._is_down:
            return
        self._is_down = False
        self._on_release()
