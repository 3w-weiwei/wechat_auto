from __future__ import annotations

from engine.domain.models import WindowInfo
from engine.infrastructure.platform.base import PlatformAdapter


class WindowManager:
    """Window finding and state management."""

    def __init__(self, platform: PlatformAdapter) -> None:
        self._platform = platform

    def find_app(self, title: str) -> WindowInfo | None:
        return self._platform.find_window_by_title(title)

    def activate(self, hwnd: int) -> bool:
        if self._platform.is_window_minimized(hwnd):
            self._platform.restore_window(hwnd)
        return self._platform.activate_window(hwnd)

    def get_window_state(self, title: str) -> str:
        """Returns 'not_found', 'minimized', or 'visible'."""
        import win32gui

        result: list[int] = []

        def callback(hwnd: int, _results: list[int]) -> bool:
            if win32gui.IsWindow(hwnd) and win32gui.GetWindowText(hwnd) == title and win32gui.IsWindowVisible(hwnd):
                _results.append(hwnd)
            return True

        win32gui.EnumWindows(callback, result)
        if not result:
            return "not_found"
        hwnd = result[0]
        if win32gui.IsIconic(hwnd):
            return "minimized"
        rect = win32gui.GetWindowRect(hwnd)
        if rect[2] <= 0 or rect[3] <= 0:
            return "minimized"
        if (rect[2] - rect[0]) < 50 or (rect[3] - rect[1]) < 50:
            return "minimized"
        return "visible"
