from __future__ import annotations

import random
import time

import pyautogui
import pyperclip


class InputController:
    """Mouse and keyboard simulation with human-like jitter."""

    @staticmethod
    def sleep(base: float = 0.25, jitter: float = 0.15) -> None:
        time.sleep(base + random.uniform(0, jitter))

    @staticmethod
    def move_mouse(x: int, y: int, duration: float = 0.15) -> None:
        jx = x + random.randint(-2, 2)
        jy = y + random.randint(-2, 2)
        d = duration + random.uniform(0.03, 0.12)
        pyautogui.moveTo(jx, jy, duration=min(d, 1.0))

    @staticmethod
    def click(x: int, y: int, clicks: int = 1, interval: float = 0.08) -> None:
        InputController.move_mouse(x, y)
        time.sleep(random.uniform(0.05, 0.10))
        pyautogui.click(clicks=clicks, interval=interval)

    @staticmethod
    def press_key(key: str) -> None:
        pyautogui.press(key)

    @staticmethod
    def hotkey(*keys: str) -> None:
        pyautogui.hotkey(*keys)

    @staticmethod
    def paste_text(text: str) -> None:
        pyperclip.copy(text)
        time.sleep(random.uniform(0.08, 0.15))
        pyautogui.hotkey("ctrl", "v")

    @staticmethod
    def clear_and_paste(text: str) -> None:
        """Clear existing text (Ctrl+A, Backspace) then paste."""
        pyautogui.hotkey("ctrl", "a")
        time.sleep(random.uniform(0.03, 0.06))
        pyautogui.press("backspace")
        time.sleep(random.uniform(0.05, 0.10))
        InputController.paste_text(text)

    @staticmethod
    def send_enter() -> None:
        pyautogui.press("enter")
