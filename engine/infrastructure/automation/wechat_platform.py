from __future__ import annotations

import contextlib
import os
import time
from collections.abc import Callable

import numpy as np

from engine.domain.interfaces import IMessagingPlatform
from engine.domain.models import ContentType, WindowInfo, WindowRect
from engine.infrastructure.automation.clipboard import ClipboardHelper
from engine.infrastructure.automation.input import InputController
from engine.infrastructure.automation.vision import VisionEngine
from engine.infrastructure.platform.base import PlatformAdapter


class WeChatPlatform(IMessagingPlatform):
    """WeChat desktop automation via computer vision + keyboard/mouse simulation."""

    name = "微信"

    def __init__(
        self,
        platform: PlatformAdapter,
        vision: VisionEngine,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._platform = platform
        self._vision = vision
        self._log_callback = log_callback
        self._wx_region: WindowRect | None = None
        self._wx_hwnd: int | None = None

    def is_available(self) -> bool:
        return self.locate_app() is not None

    def locate_app(self) -> WindowInfo | None:
        return self._platform.find_window_by_title(self.name)

    def get_required_theme(self) -> str | None:
        return "light"

    def calibrate(self) -> bool:
        """Find WeChat window, store its position and dimensions."""
        info = self.locate_app()
        if not info:
            return False
        hwnd = info.hwnd
        self._platform.restore_window(hwnd)
        self._platform.activate_window(hwnd)
        time.sleep(0.5)
        rect = self._platform.get_window_rect(hwnd)
        if rect.width < 50 or rect.height < 50:
            return False
        self._wx_hwnd = hwnd
        self._wx_region = rect
        return True

    def activate(self) -> bool:
        if self._wx_hwnd:
            return self._platform.activate_window(self._wx_hwnd)
        info = self.locate_app()
        if not info:
            return False
        self._wx_hwnd = info.hwnd
        return self._platform.activate_window(self._wx_hwnd)

    def navigate_to_chat(self, chat_name: str) -> bool:
        if not self._wx_region:
            return False
        scr = self._platform.get_screenshot(self._wx_region)
        if scr is None or not isinstance(scr, np.ndarray):
            return False

        # Click search box area — use template matching
        search_tpl = self._get_template_path("search")
        if search_tpl:
            m = self._vision.match_template(scr, search_tpl)
            if m is not None:
                self._click_in_wx(m.x + m.width // 2, m.y + m.height // 2)
                time.sleep(0.1)
                InputController.clear_and_paste(chat_name)
                time.sleep(1.0)
            else:
                self._log("[Vision] Search box not found, clicking fallback")
                self._click_in_wx(int(self._wx_region.width * 0.5), 60)
                time.sleep(0.2)
                InputController.clear_and_paste(chat_name)
                time.sleep(1.0)
        else:
            self._click_in_wx(int(self._wx_region.width * 0.5), 60)
            time.sleep(0.2)
            InputController.clear_and_paste(chat_name)
            time.sleep(1.0)

        # Click on target in search results
        scr2 = self._platform.get_screenshot(self._wx_region)
        if scr2 is not None and isinstance(scr2, np.ndarray):
            label_pos = self._find_label_in_screen(scr2)
            if label_pos:
                self._click_in_wx(label_pos[0], label_pos[1])
                time.sleep(0.6)
                return True

        # Fallback click
        self._click_in_wx(int(self._wx_region.width * 0.3), int(self._wx_region.height * 0.25))
        time.sleep(0.6)
        return True

    def send_text(self, text: str) -> bool:
        self._focus_chat_input()
        InputController.sleep(0.2, 0.1)
        ClipboardHelper.copy_text(text)
        InputController.sleep(0.08, 0.06)
        InputController.paste()
        InputController.sleep(0.12, 0.08)
        InputController.send_enter()
        return True

    def send_file(self, filepath: str) -> bool:
        filepath = os.path.abspath(filepath)
        if not os.path.exists(filepath):
            self._log(f"[Error] File not found: {filepath}")
            return False
        self._focus_chat_input()
        ClipboardHelper.copy_files([filepath])
        InputController.sleep(0.15, 0.1)
        InputController.paste()
        InputController.sleep(0.5, 0.2)
        InputController.send_enter()
        InputController.sleep(0.3, 0.1)
        return True

    def send_content(self, content_type: ContentType, value: str) -> bool:
        if content_type == ContentType.TEXT:
            return self.send_text(value)
        elif content_type in (ContentType.IMAGE, ContentType.VIDEO):
            return self.send_file(value)
        return False

    def get_wx_region(self) -> WindowRect | None:
        return self._wx_region

    def _click_in_wx(self, x: int, y: int) -> None:
        if self._wx_region:
            InputController.click(self._wx_region.left + x, self._wx_region.top + y)

    def _focus_chat_input(self) -> None:
        if self._wx_region:
            self._click_in_wx(
                int(self._wx_region.width * 0.60), int(self._wx_region.height * 0.88)
            )
            InputController.sleep(0.2, 0.1)

    def _find_label_in_screen(self, screen: np.ndarray) -> tuple[int, int] | None:
        """Find group label or recent label in search results."""
        best_score = 0.0
        best_pos: tuple[int, int] | None = None
        for key in ("group_label", "recent_label"):
            tpl = self._get_template_path(key)
            if not tpl:
                continue
            m = self._vision.match_template(screen, tpl)
            if m is not None and m.confidence > best_score:
                best_score = m.confidence
                best_pos = (m.x + m.width // 2, m.y + m.height + 20)
        return best_pos

    def _get_template_path(self, key: str) -> str:
        """Resolve template image path by theme preference."""
        import json

        config_path = os.path.join(self._platform.get_app_data_dir(), "config.json")
        theme = "light"
        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8") as f:
                    cfg = json.load(f)
                theme = cfg.get("template_theme", "light")
            except Exception:
                pass
        fallback = "dark" if theme == "light" else "light"
        for th in (theme, fallback):
            custom_path = os.path.join(
                self._platform.get_app_data_dir(), "templates", f"{key}_{th}.png"
            )
            if os.path.exists(custom_path):
                return custom_path
            # Check config
            if os.path.exists(config_path):
                try:
                    with open(config_path, encoding="utf-8") as f:
                        cfg = json.load(f)
                    tp = cfg.get("templates", {}).get(th, {}).get(key, "")
                    if tp and os.path.exists(tp):
                        return tp
                except Exception:
                    pass
        # Default: look alongside script
        suffix = "_dark" if theme == "dark" else ""
        default = os.path.join(self._platform.get_original_dir(), f"{key}{suffix}.png")
        if os.path.exists(default):
            return default
        return ""

    def _log(self, msg: str) -> None:
        if self._log_callback:
            with contextlib.suppress(Exception):
                self._log_callback(msg)
