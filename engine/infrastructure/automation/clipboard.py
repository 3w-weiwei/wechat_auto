from __future__ import annotations

import os
import struct


class ClipboardHelper:
    """Cross-platform clipboard with Win32 CF_HDROP support for file paste."""

    @staticmethod
    def copy_text(text: str) -> None:
        import pyperclip

        pyperclip.copy(text)

    @staticmethod
    def copy_files(paths: list[str]) -> None:
        """Copy files to clipboard in CF_HDROP format (Windows only)."""
        import win32clipboard
        import win32con

        if isinstance(paths, str):
            paths = [paths]
        abs_paths = [os.path.abspath(p) for p in paths]
        data = ("\0".join(abs_paths) + "\0\0").encode("utf-16le")
        dropfiles = struct.pack("IIIII", 20, 0, 0, 0, 1)
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_HDROP, dropfiles + data)
        finally:
            win32clipboard.CloseClipboard()

    @staticmethod
    def paste() -> None:
        import pyautogui

        pyautogui.hotkey("ctrl", "v")
