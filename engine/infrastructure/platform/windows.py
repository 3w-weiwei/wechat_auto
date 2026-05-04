from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import sys

import numpy as np
import pyautogui

from engine.domain.models import WindowInfo, WindowRect
from engine.infrastructure.platform.base import PlatformAdapter


class WindowsPlatformAdapter(PlatformAdapter):
    """Windows-specific implementation using Win32 API."""

    def get_system_dpi(self) -> int:
        try:
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
            ctypes.windll.user32.ReleaseDC(0, hdc)
            return dpi if dpi > 0 else 96
        except Exception:
            return 96

    def get_dpi_scale(self) -> float:
        return self.get_system_dpi() / 96.0

    def find_window_by_title(self, title: str) -> WindowInfo | None:
        import win32gui

        result: list[int] = []

        def callback(hwnd: int, _: object) -> bool:
            if win32gui.IsWindow(hwnd) and win32gui.GetWindowText(hwnd) == title and win32gui.IsWindowVisible(hwnd):
                result.append(hwnd)
            return True

        win32gui.EnumWindows(callback, None)
        if not result:
            return None
        hwnd = result[0]
        rect = self.get_window_rect(hwnd)
        return WindowInfo(hwnd=hwnd, title=title, rect=rect)

    def get_window_rect(self, hwnd: int) -> WindowRect:
        try:
            rect = ctypes.wintypes.RECT()
            ctypes.windll.dwmapi.DwmGetWindowAttribute(
                hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)
            )
            return WindowRect(
                left=rect.left,
                top=rect.top,
                width=rect.right - rect.left,
                height=rect.bottom - rect.top,
            )
        except Exception:
            import win32gui

            r = win32gui.GetWindowRect(hwnd)
            return WindowRect(left=r[0], top=r[1], width=r[2] - r[0], height=r[3] - r[1])

    def activate_window(self, hwnd: int) -> bool:
        import win32gui

        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, 9)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False

    def is_window_visible(self, hwnd: int) -> bool:
        import win32gui

        try:
            return bool(win32gui.IsWindowVisible(hwnd))
        except Exception:
            return False

    def is_window_minimized(self, hwnd: int) -> bool:
        import win32gui

        try:
            return bool(win32gui.IsIconic(hwnd))
        except Exception:
            return True

    def restore_window(self, hwnd: int) -> bool:
        import win32gui

        try:
            win32gui.ShowWindow(hwnd, 9)
            return True
        except Exception:
            return False

    def get_screenshot(self, region: WindowRect | None = None) -> object | None:
        try:
            if region:
                ss = pyautogui.screenshot(
                    region=(region.left, region.top, region.width, region.height)
                )
            else:
                ss = pyautogui.screenshot()
            import cv2

            return cv2.cvtColor(np.array(ss), cv2.COLOR_RGB2BGR)
        except Exception:
            return None

    def open_directory(self, path: str) -> None:
        os.startfile(path)  # type: ignore[attr-defined]

    def get_app_data_dir(self) -> str:
        if getattr(sys, "frozen", False):
            base = os.path.expanduser("~/Documents")
            return os.path.join(base, "WePush")
        return os.path.dirname(os.path.abspath(sys.argv[0]))

    def get_original_dir(self) -> str:
        return os.path.dirname(os.path.abspath(__file__))
