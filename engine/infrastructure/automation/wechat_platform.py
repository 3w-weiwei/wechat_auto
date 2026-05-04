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
        self._current_theme: str = "light"

    def is_available(self) -> bool:
        return self.locate_app() is not None

    def locate_app(self) -> WindowInfo | None:
        return self._platform.find_window_by_title(self.name)

    def get_required_theme(self) -> str | None:
        return "light"

    def calibrate(self) -> bool:
        """Find WeChat window, store its position and dimensions."""
        self._log("[校准] 正在查找微信窗口...")
        if self._wx_hwnd:
            info = WindowInfo(hwnd=self._wx_hwnd, title="微信",
                              rect=self._platform.get_window_rect(self._wx_hwnd))
        else:
            info = self.locate_app()
        if not info:
            self._log("[校准] ❌ 未找到微信窗口")
            return False
        hwnd = info.hwnd
        self._log("[校准] 找到微信窗口，正在激活...")
        self._platform.restore_window(hwnd)
        self._platform.activate_window(hwnd)
        time.sleep(0.8)  # wait for window to fully render
        rect = self._platform.get_window_rect(hwnd)
        if rect.width < 50 or rect.height < 50:
            self._log(f"[校准] ❌ 窗口尺寸异常: {rect.width}x{rect.height}")
            return False
        self._wx_hwnd = hwnd
        self._wx_region = rect
        dpi = self._platform.get_system_dpi()
        self._log(f"[校准] ✅ 成功 | 位置=({rect.left},{rect.top}) 尺寸={rect.width}x{rect.height} DPI={dpi}")
        self._vision.set_dpi(dpi)

        # Verify screenshot works
        scr = self._platform.get_screenshot(rect)
        if scr is not None and isinstance(scr, np.ndarray):
            self._log(f"[校准] 截图验证OK: {scr.shape[1]}x{scr.shape[0]}")
        else:
            self._log("[校准] ⚠️ 截图失败，但继续...")
        return True

    def activate(self) -> bool:
        if self._wx_hwnd:
            ok = self._platform.activate_window(self._wx_hwnd)
            if ok:
                return True
        info = self.locate_app()
        if not info:
            return False
        self._wx_hwnd = info.hwnd
        return self._platform.activate_window(self._wx_hwnd)

    def navigate_to_chat(self, chat_name: str) -> bool:
        if not self._wx_region:
            self._log("[导航] ❌ 微信窗口未校准")
            return False

        self._log(f"[导航] ▶ 搜索群聊: {chat_name}")
        scr = self._platform.get_screenshot(self._wx_region)
        if scr is None or not isinstance(scr, np.ndarray):
            self._log("[导航] ❌ 截图失败")
            return False

        # Step 1: Click search box
        search_tpl = self._get_template_path("search")
        search_clicked = False
        if search_tpl:
            self._log(f"[导航] 匹配搜索框: {os.path.basename(search_tpl)}")
            m = self._vision.match_template(scr, search_tpl)
            if m is not None:
                cx = self._wx_region.left + m.x + m.width // 2
                cy = self._wx_region.top + m.y + m.height // 2
                self._log(f"[导航] ✅ 找到搜索框 (置信度={m.confidence:.3f}) 屏幕坐标=({cx},{cy})")
                InputController.click(cx, cy)
                search_clicked = True
            else:
                self._log("[导航] ⚠️ 搜索框模板未匹配")
        else:
            self._log("[导航] ⚠️ 搜索框模板不存在")

        if not search_clicked:
            # Fallback: click top-center area where search usually is
            cx = self._wx_region.left + int(self._wx_region.width * 0.5)
            cy = self._wx_region.top + 60
            self._log(f"[导航] 备选点击搜索区: ({cx},{cy})")
            InputController.click(cx, cy)

        # Type group name
        time.sleep(0.3)
        InputController.clear_and_paste(chat_name)
        self._log(f"[导航] 已输入: {chat_name}")
        time.sleep(2.0)  # wait for search results to appear

        # Step 2: Click target in search results
        self._log("[导航] 识别搜索结果...")
        scr2 = self._platform.get_screenshot(self._wx_region)
        if scr2 is not None and isinstance(scr2, np.ndarray):
            label_pos = self._find_label_in_screen(scr2)
            if label_pos:
                gx = self._wx_region.left + label_pos[0]
                gy = self._wx_region.top + label_pos[1]
                self._log(f"[导航] ✅ 找到群聊标签 屏幕坐标=({gx},{gy})")
                InputController.click(gx, gy)
                time.sleep(0.8)
                return True
            self._log("[导航] ⚠️ 未匹配群聊标签")

        # Fallback: click in the first result area
        gx = self._wx_region.left + int(self._wx_region.width * 0.3)
        gy = self._wx_region.top + int(self._wx_region.height * 0.28)
        self._log(f"[导航] 备选点击结果区: ({gx},{gy})")
        InputController.click(gx, gy)
        time.sleep(0.6)
        return True

    def send_text(self, text: str) -> bool:
        short = text[:50] + ("..." if len(text) > 50 else "")
        self._log(f"[发送文字] {short}")
        self._focus_chat_input()
        InputController.sleep(0.3, 0.1)
        ClipboardHelper.copy_text(text)
        InputController.sleep(0.1, 0.06)
        InputController.paste()
        InputController.sleep(0.15, 0.08)
        InputController.send_enter()
        InputController.sleep(0.1, 0.05)
        self._log("[发送文字] ✅ 已发送")
        return True

    def send_file(self, filepath: str) -> bool:
        filepath = os.path.abspath(filepath)
        if not os.path.exists(filepath):
            self._log(f"[发送文件] ❌ 文件不存在: {filepath}")
            return False
        filename = os.path.basename(filepath)
        size_kb = os.path.getsize(filepath) / 1024
        self._log(f"[发送文件] {filename} ({size_kb:.1f}KB)")
        self._focus_chat_input()
        ClipboardHelper.copy_files([filepath])
        InputController.sleep(0.2, 0.1)
        InputController.paste()
        InputController.sleep(0.6, 0.2)
        InputController.send_enter()
        InputController.sleep(0.3, 0.1)
        self._log("[发送文件] ✅ 已发送")
        return True

    def send_content(self, content_type: ContentType, value: str) -> bool:
        if content_type == ContentType.TEXT:
            return self.send_text(value)
        elif content_type in (ContentType.IMAGE, ContentType.VIDEO):
            return self.send_file(value)
        return False

    def get_wx_region(self) -> WindowRect | None:
        return self._wx_region

    def _focus_chat_input(self) -> None:
        if self._wx_region:
            gx = self._wx_region.left + int(self._wx_region.width * 0.60)
            gy = self._wx_region.top + int(self._wx_region.height * 0.88)
            self._log(f"[输入框] 点击聊天输入区: ({gx},{gy})")
            InputController.click(gx, gy)
            InputController.sleep(0.15, 0.05)

    def _find_label_in_screen(self, screen: np.ndarray) -> tuple[int, int] | None:
        best_score = 0.0
        best_name = ""
        best_pos: tuple[int, int] | None = None
        for key in ("group_label", "recent_label"):
            tpl = self._get_template_path(key)
            if not tpl:
                continue
            m = self._vision.match_template(screen, tpl)
            if m is not None and m.confidence > best_score:
                best_score = m.confidence
                best_name = key
                best_pos = (m.x + m.width // 2, m.y + m.height + 20)
        if best_pos:
            self._log(f"[识别] '{best_name}' (置信度={best_score:.3f})")
        return best_pos

    def _get_template_path(self, key: str) -> str:
        import json

        engine_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        templates_dir = os.path.join(engine_dir, "templates")

        config_path = os.path.join(self._platform.get_app_data_dir(), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8") as f:
                    cfg = json.load(f)
                self._current_theme = cfg.get("template_theme", "light")
            except Exception:
                pass

        fallback_theme = "dark" if self._current_theme == "light" else "light"

        for th in (self._current_theme, fallback_theme):
            local_path = os.path.join(templates_dir, f"{key}_{th}.png")
            if os.path.exists(local_path):
                return local_path
            if os.path.exists(config_path):
                try:
                    with open(config_path, encoding="utf-8") as f:
                        cfg = json.load(f)
                    tp = cfg.get("templates", {}).get(th, {}).get(key, "")
                    if tp and os.path.exists(tp):
                        return tp
                except Exception:
                    pass
            app_data_tpl = os.path.join(
                self._platform.get_app_data_dir(), "templates", f"{key}_{th}.png"
            )
            if os.path.exists(app_data_tpl):
                return app_data_tpl

        return ""

    def _log(self, msg: str) -> None:
        if self._log_callback:
            with contextlib.suppress(Exception):
                self._log_callback(msg)
