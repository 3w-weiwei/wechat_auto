# ═══════════════════════════════════════════════════════════════
# wechat_auto.py - 智推助手 v2.0（拖拽上传 + 附件管理）
# ═══════════════════════════════════════════════════════════════

# ★ DPI 声明必须在所有 import 之前
import ctypes
import ctypes.wintypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import sys
import time
import random
import os
import struct
import json
import shutil
import uuid
import hashlib
from datetime import datetime, timedelta
from collections import deque

import cv2
import numpy as np
import pygetwindow as gw
import pyautogui
import pyperclip
import win32clipboard
import win32con
import win32gui
import win32process

from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QFileDialog, QScrollArea, QFrame, QTextEdit,
    QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem, QStackedWidget,
    QDateTimeEdit, QMessageBox, QDialog
)
from PyQt5.QtGui import (
    QPixmap, QFont, QColor, QPainter, QIcon, QCursor, QBrush, QTextCursor,
    QDragEnterEvent, QDropEvent
)
from PyQt5.QtCore import (
    Qt, QTimer, QSize, QRectF, QPropertyAnimation, QEasingCurve,
    pyqtProperty, QThread, pyqtSignal, QDateTime, QMimeData, QUrl
)
from PyQt5.QtSvg import QSvgRenderer

# ═══════════════════════ 全局配置 ═══════════════════════════════

def _get_app_data_dir():
    if getattr(sys, 'frozen', False):
        base = os.path.expanduser("~/Documents")
        app_dir = os.path.join(base, "WePush")
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

APP_DIR = _get_app_data_dir()
_ORIGINAL_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(APP_DIR, "tasks.json")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")
ATTACHMENTS_DIR = os.path.join(APP_DIR, "attachments")
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(ATTACHMENTS_DIR, exist_ok=True)

TEMPLATE_KEYS = ["search", "group_label", "recent_label"]
TEMPLATE_LABELS = {"search": "搜索框", "group_label": "群聊标签", "recent_label": "最常使用标签"}

DEFAULT_TEMPLATES = {
    "light": {
        "search": os.path.join(_ORIGINAL_DIR, "search.png"),
        "group_label": os.path.join(_ORIGINAL_DIR, "group_label.png"),
        "recent_label": os.path.join(_ORIGINAL_DIR, "recent_label.png"),
    },
    "dark": {
        "search": os.path.join(_ORIGINAL_DIR, "search_dark.png"),
        "group_label": os.path.join(_ORIGINAL_DIR, "group_label_dark.png"),
        "recent_label": os.path.join(_ORIGINAL_DIR, "recent_label_dark.png"),
    },
}

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except: pass

def get_current_theme():
    return load_config().get("template_theme", "light")

def set_current_theme(theme):
    cfg = load_config(); cfg["template_theme"] = theme; save_config(cfg)

def get_template_path(key):
    theme = get_current_theme()
    fallback = "dark" if theme == "light" else "light"
    cfg = load_config()
    for th in [theme, fallback]:
        custom = cfg.get("templates", {}).get(th, {}).get(key, "")
        if custom and os.path.exists(custom): return custom
        default = DEFAULT_TEMPLATES.get(th, {}).get(key, "")
        if default and os.path.exists(default): return default
    return ""

def generate_task_id():
    return uuid.uuid4().hex[:12]

def cv2_imread_safe(filepath):
    if not filepath or not os.path.exists(filepath): return None
    try:
        img = cv2.imread(filepath)
        if img is not None: return img
    except: pass
    try:
        with open(filepath, 'rb') as f:
            data = np.frombuffer(f.read(), dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except: return None

# ═══════════════════════ 附件管理器 ═════════════════════════════

class AttachmentManager:
    """
    附件统一管理：
    - 上传的图片/视频复制到 ATTACHMENTS_DIR
    - 文件名用 hash 前缀防重名
    - 提供清理未引用附件的功能
    """

    @staticmethod
    def import_file(src_path):
        """
        导入文件到附件目录，返回附件路径
        如果已存在相同文件（hash 一致），直接返回已有路径
        """
        if not src_path or not os.path.exists(src_path):
            return None

        # 计算文件 hash（取前 8 位）
        file_hash = AttachmentManager._file_hash(src_path)
        ext = os.path.splitext(src_path)[1].lower()
        orig_name = os.path.splitext(os.path.basename(src_path))[0]
        # 清理文件名中的特殊字符
        safe_name = "".join(c for c in orig_name if c.isalnum() or c in "._- ")[:30]
        dest_name = f"{file_hash}_{safe_name}{ext}"
        dest_path = os.path.join(ATTACHMENTS_DIR, dest_name)

        # 如果已存在且 hash 相同，直接返回
        if os.path.exists(dest_path):
            return os.path.abspath(dest_path)

        try:
            shutil.copy2(src_path, dest_path)
            return os.path.abspath(dest_path)
        except Exception:
            return None

    @staticmethod
    def _file_hash(filepath, length=8):
        """计算文件 MD5 前 N 位"""
        h = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk: break
                    h.update(chunk)
            return h.hexdigest()[:length]
        except:
            return uuid.uuid4().hex[:length]

    @staticmethod
    def get_all_attachments():
        """列出所有附件"""
        if not os.path.exists(ATTACHMENTS_DIR): return []
        files = []
        for f in os.listdir(ATTACHMENTS_DIR):
            fp = os.path.join(ATTACHMENTS_DIR, f)
            if os.path.isfile(fp):
                ext = os.path.splitext(f)[1].lower()
                ftype = "image" if ext in IMAGE_EXTS else "video" if ext in VIDEO_EXTS else "other"
                size = os.path.getsize(fp)
                files.append({"name": f, "path": os.path.abspath(fp), "type": ftype, "size": size})
        return sorted(files, key=lambda x: x["name"])

    @staticmethod
    def get_referenced_paths(tasks):
        """获取所有任务中引用的附件路径"""
        paths = set()
        for t in tasks:
            for c in t.get("contents", []):
                if c.get("type") in ("image", "video") and c.get("value"):
                    paths.add(os.path.abspath(c["value"]))
        return paths

    @staticmethod
    def cleanup_unreferenced(tasks):
        """清理未被任何任务引用的附件，返回清理数量"""
        referenced = AttachmentManager.get_referenced_paths(tasks)
        all_files = AttachmentManager.get_all_attachments()
        removed = 0
        for f in all_files:
            if f["path"] not in referenced:
                try:
                    os.remove(f["path"]); removed += 1
                except: pass
        return removed

    @staticmethod
    def get_stats(tasks):
        """统计信息"""
        all_files = AttachmentManager.get_all_attachments()
        referenced = AttachmentManager.get_referenced_paths(tasks)
        total_size = sum(f["size"] for f in all_files)
        return {
            "total": len(all_files),
            "referenced": sum(1 for f in all_files if f["path"] in referenced),
            "unreferenced": sum(1 for f in all_files if f["path"] not in referenced),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
        }

    @staticmethod
    def detect_file_type(filepath):
        """根据扩展名判断文件类型"""
        ext = os.path.splitext(filepath)[1].lower()
        if ext in IMAGE_EXTS: return "image"
        if ext in VIDEO_EXTS: return "video"
        return None

# ═══════════════════════ DPI 工具 ═══════════════════════════════

def get_system_dpi():
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return dpi if dpi > 0 else 96
    except: return 96

def get_dpi_scale():
    return get_system_dpi() / 96.0

def get_window_physical_rect(hwnd):
    try:
        rect = ctypes.wintypes.RECT()
        ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect))
        return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    except:
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)

# ═══════════════════ 微信窗口检测 ═══════════════════════════════

def get_wechat_window_state():
    try:
        def callback(hwnd, results):
            if win32gui.IsWindow(hwnd) and win32gui.GetWindowText(hwnd) == "微信":
                if win32gui.IsWindowVisible(hwnd): results.append(hwnd)
            return True
        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        if not hwnds: return "not_found"
        hwnd = hwnds[0]
        if win32gui.IsIconic(hwnd): return "minimized"
        rect = win32gui.GetWindowRect(hwnd)
        if rect[2] <= 0 or rect[3] <= 0: return "minimized"
        if (rect[2]-rect[0]) < 50 or (rect[3]-rect[1]) < 50: return "minimized"
        return "visible"
    except: return "not_found"

# ═══════════════════════ 持久化 ═════════════════════════════════

def save_tasks_to_file(tasks):
    data = []
    for t in tasks:
        data.append({"id": t["id"], "group": t["group"], "datetime": t["datetime"],
                      "contents": t.get("contents", []), "active": t.get("active", True)})
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass

def load_tasks_from_file():
    if not os.path.exists(TASKS_FILE): return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        tasks = []
        for item in data:
            task = {"id": str(item.get("id", generate_task_id())), "group": item.get("group", ""),
                    "datetime": item.get("datetime", ""), "contents": item.get("contents", []),
                    "active": item.get("active", True)}
            if not task["contents"] and "content" in item:
                task["contents"] = [{"type": item.get("type", "text"), "value": item["content"]}]
            tasks.append(task)
        return tasks
    except: return []

# ═══════════════════════ SVG 图标 ═══════════════════════════════

ICONS = {
    "monitor": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
    "clock": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "plus_circle": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>',
    "settings": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    "message": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "image": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
    "video": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>',
    "trash": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
    "search": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "check_circle": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "play": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
    "calendar": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    "x_circle": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
    "arrow_up": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>',
    "arrow_down": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>',
    "upload": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',
    "chevron_down": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>',
    "chevron_up": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>',
    "edit": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',
    "save": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>',
    "terminal": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>',
    "users": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "layers": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
    "sun": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
    "moon": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    "folder": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
    "paperclip": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>',
}

def svg_to_pixmap(svg_str, size=24, color="#666666"):
    svg_str = svg_str.replace('stroke="currentColor"', f'stroke="{color}"')
    r = QSvgRenderer(); r.load(svg_str.encode('utf-8'))
    pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm); r.render(p); p.end(); return pm

def svg_icon(name, size=20, color="#666666"):
    return QIcon(svg_to_pixmap(ICONS.get(name, ""), size, color))

def make_shadow(blur=12, x=0, y=2, alpha=20):
    s = QGraphicsDropShadowEffect(); s.setBlurRadius(blur); s.setXOffset(x); s.setYOffset(y); s.setColor(QColor(0,0,0,alpha)); return s

C = {
    "bg":"#f9fafb","white":"#ffffff","green500":"#22c55e","green50":"#f0fdf4","green600":"#16a34a",
    "blue500":"#3b82f6","blue50":"#eff6ff","red400":"#f87171","red50":"#fef2f2",
    "gray50":"#f9fafb","gray100":"#f3f4f6","gray200":"#e5e7eb","gray300":"#d1d5db","gray400":"#9ca3af",
    "gray500":"#6b7280","gray600":"#4b5563","gray700":"#374151","gray800":"#1f2937","gray900":"#111827",
    "yellow400":"#facc15","yellow500":"#eab308","orange500":"#f97316","orange50":"#fff7ed","purple500":"#a855f7",
    "purple50":"#faf5ff","indigo500":"#6366f1","indigo50":"#eef2ff","amber500":"#f59e0b","amber50":"#fffbeb",
    "teal500":"#14b8a6","teal50":"#f0fdfa",
}

GLOBAL_STYLE = f"""
    * {{ font-family: "Microsoft YaHei", "Segoe UI", sans-serif; }}
    QScrollArea {{ border: none; background-color: transparent; }}
    QScrollBar:vertical {{ border:none;background:transparent;width:6px;margin:4px 0; }}
    QScrollBar::handle:vertical {{ background:{C['gray300']};border-radius:3px;min-height:20px; }}
    QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{ height:0; }}
    QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {{ background:none; }}
"""

# ═══════════════════════ 基础 UI ═══════════════════════════════

class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)
    def __init__(self, checked=True, parent=None):
        super().__init__(parent); self.setFixedSize(42,24); self._checked=checked; self._hp=22.0 if checked else 4.0
        self.setCursor(QCursor(Qt.PointingHandCursor)); self._a=QPropertyAnimation(self,b"hp"); self._a.setDuration(200); self._a.setEasingCurve(QEasingCurve.InOutCubic)
    def isChecked(self): return self._checked
    def setChecked(self, v):
        if self._checked != v:
            self._checked = v; self._a.setStartValue(self._hp); self._a.setEndValue(22.0 if v else 4.0); self._a.start()
    @pyqtProperty(float)
    def hp(self): return self._hp
    @hp.setter
    def hp(self,v): self._hp=v; self.update()
    def mousePressEvent(self,e):
        self._checked=not self._checked; self._a.setStartValue(self._hp); self._a.setEndValue(22.0 if self._checked else 4.0); self._a.start(); self.toggled.emit(self._checked)
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setBrush(QBrush(QColor("#22c55e") if self._checked else QColor("#d1d5db"))); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0,0,42,24),12,12); p.setBrush(QBrush(QColor("white"))); p.drawEllipse(QRectF(self._hp-8,4,16,16)); p.end()

# ═══════════════════════ 拖拽区域组件 ══════════════════════════

class DropZone(QFrame):
    """
    可拖拽文件的区域，支持拖入图片/视频
    文件自动导入到附件目录
    """
    file_dropped = pyqtSignal(str, str)  # (file_type, attachment_path)

    def __init__(self, accept_types=None, parent=None):
        super().__init__(parent)
        self.accept_types = accept_types or ["image", "video"]  # 接受的类型
        self._dragging = False
        self.setAcceptDrops(True)
        self.setMinimumHeight(60)
        self._update_style(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # 图标
        self.icon_label = QLabel()
        self.icon_label.setPixmap(svg_to_pixmap(ICONS["upload"], 24, C["gray400"]))
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("background:transparent;border:none;")
        layout.addWidget(self.icon_label)

        # 提示文字
        types_text = []
        if "image" in self.accept_types:
            types_text.append("图片")
        if "video" in self.accept_types:
            types_text.append("视频")
        hint = " / ".join(types_text)

        self.text_label = QLabel(f"拖拽{hint}到此处，或点击选择")
        self.text_label.setFont(QFont("Microsoft YaHei", 8))
        self.text_label.setStyleSheet(f"color:{C['gray400']};background:transparent;border:none;")
        self.text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.text_label)

        self.setCursor(QCursor(Qt.PointingHandCursor))

    def _update_style(self, dragging):
        oid = f"DZ_{id(self)}"
        self.setObjectName(oid)
        if dragging:
            self.setStyleSheet(f"""
                QFrame#{oid} {{
                    background: {C['green50']};
                    border: 2px dashed {C['green500']};
                    border-radius: 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#{oid} {{
                    background: {C['gray50']};
                    border: 2px dashed {C['gray300']};
                    border-radius: 10px;
                }}
                QFrame#{oid}:hover {{
                    border-color: {C['blue500']};
                    background: {C['blue50']};
                }}
            """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            # 检查是否有可接受的文件类型
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    ftype = AttachmentManager.detect_file_type(url.toLocalFile())
                    if ftype and ftype in self.accept_types:
                        event.acceptProposedAction()
                        self._dragging = True
                        self._update_style(True)
                        return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._dragging = False
        self._update_style(False)

    def dropEvent(self, event: QDropEvent):
        self._dragging = False
        self._update_style(False)

        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    filepath = url.toLocalFile()
                    ftype = AttachmentManager.detect_file_type(filepath)
                    if ftype and ftype in self.accept_types:
                        # 导入到附件目录
                        att_path = AttachmentManager.import_file(filepath)
                        if att_path:
                            self.file_dropped.emit(ftype, att_path)
            event.acceptProposedAction()

    def mousePressEvent(self, event):
        """点击时打开文件选择对话框"""
        if event.button() == Qt.LeftButton:
            filters = []
            if "image" in self.accept_types:
                filters.append("Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
            if "video" in self.accept_types:
                filters.append("Videos (*.mp4 *.avi *.mov *.mkv *.wmv *.flv)")
            filter_str = ";;".join(filters)
            if not filter_str:
                filter_str = "All (*)"

            paths, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", filter_str)
            for filepath in paths:
                ftype = AttachmentManager.detect_file_type(filepath)
                if ftype and ftype in self.accept_types:
                    att_path = AttachmentManager.import_file(filepath)
                    if att_path:
                        self.file_dropped.emit(ftype, att_path)


# ═══════════════════════ 内容编辑组件（支持拖拽）═══════════════

class ContentEditorItem(QFrame):
    """单条内容编辑项（文字/图片/视频），图片视频显示缩略图"""
    remove_requested = pyqtSignal(int)
    move_up_requested = pyqtSignal(int)
    move_down_requested = pyqtSignal(int)

    def __init__(self, index, ctype="text", cvalue="", parent=None):
        super().__init__(parent)
        self.index = index
        self.ctype = ctype
        oid = f"CE_{id(self)}"
        self.setObjectName(oid)
        self.setStyleSheet(f"QFrame#{oid}{{background:{C['gray50']};border:1px solid {C['gray200']};border-radius:10px;}}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # ── 顶部：序号 + 类型 + 操作按钮 ──
        top = QHBoxLayout()
        top.setSpacing(6)
        il = QLabel(f"#{index+1}")
        il.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        il.setStyleSheet(f"color:{C['gray400']};background:transparent;border:none;")

        tn = {"text": "📝 文字", "image": "🖼 图片", "video": "🎬 视频"}
        tc = {"text": C["blue500"], "image": C["green500"], "video": C["orange500"]}
        tl = QLabel(tn.get(ctype, "文字"))
        tl.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        tl.setStyleSheet(f"color:{tc.get(ctype, C['gray600'])};background:transparent;border:none;")

        top.addWidget(il)
        top.addWidget(tl)
        top.addStretch()

        for icon, tip, sig in [("arrow_up", "上移", self.move_up_requested),
                                ("arrow_down", "下移", self.move_down_requested),
                                ("x_circle", "移除", self.remove_requested)]:
            b = QPushButton()
            b.setIcon(svg_icon(icon, 14, C["red400"] if icon == "x_circle" else C["gray400"]))
            b.setIconSize(QSize(14, 14))
            b.setFixedSize(24, 24)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            hbg = C['red50'] if icon == "x_circle" else C['gray200']
            b.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:4px;}} QPushButton:hover{{background:{hbg};}}")
            idx = self.index
            b.clicked.connect(lambda _, i=idx, s=sig: s.emit(i))
            top.addWidget(b)

        layout.addLayout(top)

        # ── 内容区 ──
        if ctype == "text":
            self.value_widget = QTextEdit()
            self.value_widget.setPlaceholderText("输入文字...")
            self.value_widget.setPlainText(cvalue)
            self.value_widget.setFixedHeight(70)
            self.value_widget.setStyleSheet(f"""
                QTextEdit{{background:{C['white']};border:1px solid {C['gray200']};border-radius:6px;
                padding:8px;font-size:11px;color:{C['gray700']};}}
                QTextEdit:focus{{border-color:{C['green500']};}}
            """)
            layout.addWidget(self.value_widget)
        else:
            # 图片/视频：显示文件名 + 缩略图预览
            self._file_path = cvalue
            file_row = QHBoxLayout()
            file_row.setSpacing(8)

            # 缩略图
            self.thumb_label = QLabel()
            self.thumb_label.setFixedSize(48, 48)
            self.thumb_label.setAlignment(Qt.AlignCenter)
            self.thumb_label.setStyleSheet(f"background:{C['gray100']};border:1px solid {C['gray200']};border-radius:6px;")
            self._update_thumbnail(cvalue)
            file_row.addWidget(self.thumb_label)

            # 文件信息
            info_col = QVBoxLayout()
            info_col.setSpacing(2)
            self.name_label = QLabel()
            self.name_label.setFont(QFont("Microsoft YaHei", 9))
            self.name_label.setStyleSheet(f"color:{C['gray700']};background:transparent;border:none;")
            self.size_label = QLabel()
            self.size_label.setFont(QFont("Microsoft YaHei", 7))
            self.size_label.setStyleSheet(f"color:{C['gray400']};background:transparent;border:none;")
            self._update_file_info(cvalue)
            info_col.addWidget(self.name_label)
            info_col.addWidget(self.size_label)
            file_row.addLayout(info_col, 1)

            # 替换按钮
            replace_btn = QPushButton("替换")
            replace_btn.setFixedSize(48, 28)
            replace_btn.setCursor(QCursor(Qt.PointingHandCursor))
            replace_btn.setFont(QFont("Microsoft YaHei", 8))
            replace_btn.setStyleSheet(f"""
                QPushButton{{background:{C['white']};color:{C['gray600']};border:1px solid {C['gray200']};border-radius:6px;}}
                QPushButton:hover{{background:{C['gray100']};}}
            """)
            replace_btn.clicked.connect(lambda: self._browse_replace())
            file_row.addWidget(replace_btn)

            layout.addLayout(file_row)

    def _update_thumbnail(self, filepath):
        """更新缩略图"""
        if filepath and os.path.exists(filepath):
            ext = os.path.splitext(filepath)[1].lower()
            if ext in IMAGE_EXTS:
                pm = QPixmap(filepath)
                if not pm.isNull():
                    self.thumb_label.setPixmap(pm.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    return
            # 视频或无法加载图片：显示图标
            icon_name = "video" if ext in VIDEO_EXTS else "image"
            color = C["orange500"] if ext in VIDEO_EXTS else C["green500"]
            self.thumb_label.setPixmap(svg_to_pixmap(ICONS[icon_name], 24, color))
        else:
            self.thumb_label.setPixmap(svg_to_pixmap(ICONS["image"], 24, C["gray300"]))

    def _update_file_info(self, filepath):
        """更新文件名和大小"""
        if filepath and os.path.exists(filepath):
            name = os.path.basename(filepath)
            size = os.path.getsize(filepath)
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/1024/1024:.1f} MB"
            # 截断长文件名
            disp = name if len(name) <= 25 else name[:12] + "..." + name[-10:]
            self.name_label.setText(disp)
            self.size_label.setText(size_str)
        else:
            self.name_label.setText("文件不存在")
            self.size_label.setText("")

    def _browse_replace(self):
        """替换文件"""
        if self.ctype == "image":
            f = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        else:
            f = "Videos (*.mp4 *.avi *.mov *.mkv *.wmv *.flv)"
        p, _ = QFileDialog.getOpenFileName(self, "选择文件", "", f)
        if p:
            att_path = AttachmentManager.import_file(p)
            if att_path:
                self._file_path = att_path
                self._update_thumbnail(att_path)
                self._update_file_info(att_path)

    def get_data(self):
        if self.ctype == "text":
            return {"type": "text", "value": self.value_widget.toPlainText().strip()}
        return {"type": self.ctype, "value": self._file_path or ""}


class ContentItemWidget(QFrame):
    """任务卡片中的只读内容展示"""
    def __init__(self, index, ctype, cvalue, parent=None):
        super().__init__(parent)
        oid = f"CI_{id(self)}"
        self.setObjectName(oid)
        self.setStyleSheet(f"QFrame#{oid}{{background:{C['gray50']};border:1px solid {C['gray100']};border-radius:6px;}}")
        l = QHBoxLayout(self); l.setContentsMargins(8, 4, 8, 4); l.setSpacing(6)
        il = QLabel(f"#{index+1}"); il.setFont(QFont("Microsoft YaHei", 7, QFont.Bold))
        il.setStyleSheet(f"color:{C['gray400']};border:none;background:transparent;"); il.setFixedWidth(22)
        iname = {"text": "message", "image": "image", "video": "video"}.get(ctype, "message")
        tc = {"text": C["blue500"], "image": C["green500"], "video": C["orange500"]}
        ic = QLabel(); ic.setPixmap(svg_to_pixmap(ICONS[iname], 14, tc.get(ctype, C["gray500"])))
        ic.setFixedSize(16, 16); ic.setStyleSheet("border:none;background:transparent;")
        disp = os.path.basename(cvalue) if ctype in ("image", "video") and cvalue else cvalue
        tl = QLabel(); tl.setFont(QFont("Microsoft YaHei", 8))
        tl.setStyleSheet(f"color:{C['gray600']};border:none;background:transparent;")
        tl.setMaximumWidth(180)
        tl.setText(tl.fontMetrics().elidedText(disp, Qt.ElideRight, 180))
        l.addWidget(il); l.addWidget(ic); l.addWidget(tl, 1)


# ═══════════════════════ 引擎 & 队列（精简，与上版相同）═══════

class AutoEngine:
    SCALE_MIN = 0.3; SCALE_MAX = 3.0; COARSE_STEP = 0.08
    FINE_OFFSETS = [0, -0.03, 0.03, -0.06, 0.06, -0.10, 0.10, -0.15, 0.15, -0.20, 0.20]
    EARLY_EXIT_SCORE = 0.88; DEFAULT_THRESHOLD = 0.65

    def __init__(self, log_callback=None):
        self.wx_region = None; self.wx_hwnd = None; self.log_callback = log_callback
        self._current_dpi = get_system_dpi(); self._dpi_scale = self._current_dpi / 96.0
        pyautogui.FAILSAFE = True

    def _log(self, msg):
        if self.log_callback:
            try: self.log_callback(msg)
            except: pass

    def _get_template_dpi(self):
        return load_config().get("template_source_dpi", 144)

    def _calc_dpi_ratio(self):
        src = self._get_template_dpi(); return self._current_dpi / (src if src > 0 else 144)

    def _scale_key(self, tpath): return os.path.basename(tpath)

    def _get_preferred_scale(self, tpath):
        rec = load_config().get("learned_scales", {}).get(self._scale_key(tpath))
        if rec is None: return None
        if isinstance(rec, dict):
            sd, ss = rec.get("dpi", self._current_dpi), rec.get("scale", 1.0)
            return ss * (self._current_dpi / sd) if sd != self._current_dpi and sd > 0 else ss
        return float(rec)

    def _save_preferred_scale(self, tpath, scale):
        cfg = load_config()
        cfg.setdefault("learned_scales", {})[self._scale_key(tpath)] = {"scale": round(scale, 4), "dpi": self._current_dpi, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        save_config(cfg)

    @staticmethod
    def clear_learned_scales():
        cfg = load_config()
        if "learned_scales" in cfg: del cfg["learned_scales"]; save_config(cfg)

    def stable_sleep(self, base=0.25, jitter=0.15): time.sleep(base + random.uniform(0, jitter))
    def safe_click(self, x, y, clicks=1):
        pyautogui.moveTo(x + random.randint(-2, 2), y + random.randint(-2, 2), duration=0.12 + random.uniform(0.03, 0.12))
        self.stable_sleep(0.08, 0.08); pyautogui.click(clicks=clicks, interval=0.08)
    def safe_paste(self, text):
        pyperclip.copy(text); self.stable_sleep(0.1, 0.1); pyautogui.hotkey("ctrl", "a"); self.stable_sleep(0.05, 0.05)
        pyautogui.press("backspace"); self.stable_sleep(0.08, 0.08); pyautogui.hotkey("ctrl", "v"); self.stable_sleep(0.12, 0.1)

    def _find_wechat_hwnd(self):
        result = []
        def cb(hwnd, _):
            if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) == "微信": result.append(hwnd)
            return True
        win32gui.EnumWindows(cb, None); return result[0] if result else None

    def activate_wechat(self):
        hwnd = self._find_wechat_hwnd()
        if not hwnd: return False
        try:
            if win32gui.IsIconic(hwnd): win32gui.ShowWindow(hwnd, 9); self.stable_sleep(0.3, 0.1)
            win32gui.SetForegroundWindow(hwnd); self.stable_sleep(0.3, 0.15); self.wx_hwnd = hwnd; return True
        except: return False

    def calibrate_silent(self):
        hwnd = self._find_wechat_hwnd()
        if not hwnd: return False
        try:
            if win32gui.IsIconic(hwnd): win32gui.ShowWindow(hwnd, 9); self.stable_sleep(0.3, 0.1)
            win32gui.SetForegroundWindow(hwnd); self.stable_sleep(0.4, 0.2)
        except: return False
        self.wx_hwnd = hwnd; l, t, w, h = get_window_physical_rect(hwnd)
        sw, sh = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
        if w < 50 or h < 50: return False
        l, t = max(0, l), max(0, t); w, h = min(w, sw - l), min(h, sh - t)
        self.wx_region = (l, t, w, h); self._current_dpi = get_system_dpi(); self._dpi_scale = self._current_dpi / 96.0
        cfg = load_config(); cfg["calibration"] = {"window_rect": [l, t, w, h], "screen_size": [sw, sh], "dpi": self._current_dpi, "timestamp": datetime.now().isoformat()}; save_config(cfg)
        return True

    def _take_screenshot(self):
        if not self.wx_region: return None
        try:
            ss = pyautogui.screenshot(region=self.wx_region); return cv2.cvtColor(np.array(ss), cv2.COLOR_RGB2BGR)
        except: return None

    def match_template(self, screen, tpath, threshold=None):
        if not tpath or not os.path.exists(tpath): return None
        if threshold is None: threshold = self.DEFAULT_THRESHOLD
        tpl_bgr = cv2_imread_safe(tpath)
        if tpl_bgr is None: self._log(f"[Match] ✗ 无法读取: {tpath}"); return None
        sg = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY); tg = cv2.cvtColor(tpl_bgr, cv2.COLOR_BGR2GRAY)
        sh, sw = sg.shape[:2]; dr = self._calc_dpi_ratio(); tn = os.path.basename(tpath)
        pref = self._get_preferred_scale(tpath)
        if pref and self.SCALE_MIN <= pref <= self.SCALE_MAX:
            r = self._try(sg, tg, pref, threshold, sw, sh)
            if r: self._log(f"[Match] ⚡ [{tn}] s={pref:.3f} sc={r['score']:.3f}"); return r
            for o in self.FINE_OFFSETS:
                if o == 0: continue
                s = pref + o
                if not (self.SCALE_MIN <= s <= self.SCALE_MAX): continue
                r = self._try(sg, tg, s, threshold, sw, sh)
                if r: self._save_preferred_scale(tpath, r["scale"]); return r
        sl = self._bsl(dr, pref); best = None; tested = 0
        for s in sl:
            tested += 1; r = self._try(sg, tg, s, threshold, sw, sh)
            if r and (best is None or r["score"] > best["score"]):
                best = r
                if best["score"] >= self.EARLY_EXIT_SCORE: break
        if best: self._log(f"[Match] ✓ [{tn}] s={best['scale']:.3f} sc={best['score']:.3f} t={tested}"); self._save_preferred_scale(tpath, best["scale"]); return best
        self._log(f"[Match] ✗ [{tn}] t={tested}"); return None

    def _try(self, sg, tg, scale, thr, sw, sh):
        scaled = tg if abs(scale - 1.0) < 0.005 else cv2.resize(tg, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        rh, rw = scaled.shape[:2]
        if rw > sw or rh > sh or rw < 6 or rh < 6: return None
        try:
            res = cv2.matchTemplate(sg, scaled, cv2.TM_CCOEFF_NORMED); _, mv, _, ml = cv2.minMaxLoc(res)
        except: return None
        return {"loc": ml, "score": mv, "w": rw, "h": rh, "scale": round(scale, 4)} if mv >= thr else None

    def _bsl(self, dr, pref=None):
        c = []
        for o in self.FINE_OFFSETS:
            s = dr + o
            if self.SCALE_MIN <= s <= self.SCALE_MAX: c.append(round(s, 4))
        if abs(dr - 1.0) > 0.15:
            for o in self.FINE_OFFSETS:
                s = 1.0 + o
                if self.SCALE_MIN <= s <= self.SCALE_MAX: c.append(round(s, 4))
        if pref:
            for o in self.FINE_OFFSETS:
                s = pref + o
                if self.SCALE_MIN <= s <= self.SCALE_MAX: c.append(round(s, 4))
        s = dr
        while s <= self.SCALE_MAX: c.append(round(s, 4)); s += self.COARSE_STEP
        s = dr - self.COARSE_STEP
        while s >= self.SCALE_MIN: c.append(round(s, 4)); s -= self.COARSE_STEP
        seen, r = set(), []
        for s in c:
            k = round(s, 3)
            if k not in seen: seen.add(k); r.append(s)
        return r

    def detect_and_input_silent(self, text):
        if not self.wx_region: return
        scr = self._take_screenshot()
        if scr is None: return
        m = self.match_template(scr, get_template_path("search"))
        if not m: self._log("[Vision] ✗ 未找到搜索框"); return
        self.safe_click(self.wx_region[0] + m["loc"][0] + m["w"] // 2, self.wx_region[1] + m["loc"][1] + m["h"] // 2); self.safe_paste(text)

    def find_label(self, screen):
        best, bs = None, 0.0
        for name, path in [("群聊", get_template_path("group_label")), ("最常使用", get_template_path("recent_label"))]:
            if not path or not os.path.exists(path): continue
            m = self.match_template(screen, path)
            if m and m["score"] > bs: best = (name, m["loc"], m["w"], m["h"]); bs = m["score"]
        return best

    def select_target_group(self, target):
        scr = self._take_screenshot()
        if scr is None: self.safe_click(self.wx_region[0] + int(self.wx_region[2] * 0.3), self.wx_region[1] + int(self.wx_region[3] * 0.25)); return True
        f = self.find_label(scr)
        if f: _, ml, w, h = f; self.safe_click(self.wx_region[0] + ml[0] + w // 2, self.wx_region[1] + ml[1] + h + 20); return True
        self.safe_click(self.wx_region[0] + int(self.wx_region[2] * 0.3), self.wx_region[1] + int(self.wx_region[3] * 0.25)); return True

    def focus_chat_input(self):
        if not self.wx_region: return False
        self.safe_click(self.wx_region[0] + int(self.wx_region[2] * 0.60), self.wx_region[1] + int(self.wx_region[3] * 0.88)); self.stable_sleep(0.2, 0.1); return True

    def send_text_silent(self, text):
        if not self.focus_chat_input(): return
        pyperclip.copy(text); self.stable_sleep(0.08, 0.06); pyautogui.hotkey("ctrl", "v"); self.stable_sleep(0.12, 0.08); pyautogui.press("enter")

    def copy_files_to_clipboard(self, paths):
        if isinstance(paths, str): paths = [paths]
        paths = [os.path.abspath(p) for p in paths]; data = ("\0".join(paths) + "\0\0").encode("utf-16le")
        dropfiles = struct.pack("IIIII", 20, 0, 0, 0, 1); win32clipboard.OpenClipboard()
        try: win32clipboard.EmptyClipboard(); win32clipboard.SetClipboardData(win32con.CF_HDROP, dropfiles + data)
        finally: win32clipboard.CloseClipboard()

    def paste_file_to_wechat_silent(self, fp):
        fp = os.path.abspath(fp)
        if not os.path.exists(fp) or not self.focus_chat_input(): return
        self.copy_files_to_clipboard(fp); self.stable_sleep(0.15, 0.1); pyautogui.hotkey("ctrl", "v"); self.stable_sleep(0.5, 0.2); pyautogui.press("enter"); self.stable_sleep(0.3, 0.1)


class TaskQueueRunner(QThread):
    log_signal = pyqtSignal(str); status_signal = pyqtSignal(str); task_finished = pyqtSignal(str, bool, str); all_done = pyqtSignal()
    def __init__(self, tasks, engine): super().__init__(); self.tasks = list(tasks); self.engine = engine
    def run(self):
        self.engine.log_callback = self.log_signal.emit
        try:
            total = len(self.tasks); self.log_signal.emit(f"[Queue] ═══ 串行执行 {total} 个任务 ═══")
            for idx, task in enumerate(self.tasks):
                tid = str(task["id"]); contents = task.get("contents", [])
                self.log_signal.emit(f"[Queue] [{idx+1}/{total}] ▶ {task['group']}")
                try:
                    activated = False
                    for attempt in range(3):
                        if self.engine.activate_wechat(): activated = True; break
                        self.log_signal.emit(f"[Retry] {attempt+1}/3..."); time.sleep(2)
                    if not activated: self.task_finished.emit(tid, False, f"未找到微信 → {task['group']}"); continue
                    if not self.engine.calibrate_silent(): self.task_finished.emit(tid, False, f"校准失败 → {task['group']}"); continue
                    self.engine.detect_and_input_silent(task['group']); time.sleep(1.2)
                    self.engine.select_target_group(task['group']); time.sleep(0.6)
                    sent = 0
                    for i, item in enumerate(contents):
                        ct, cv = item.get("type", "text"), item.get("value", "")
                        if not cv: continue
                        self.log_signal.emit(f"[Send] #{i+1}/{len(contents)} [{ct}] {os.path.basename(cv) if ct != 'text' else cv[:30]}")
                        if ct == "text": self.engine.send_text_silent(cv); sent += 1
                        elif ct in ("image", "video"):
                            if not os.path.exists(cv): self.log_signal.emit(f"[Error] 文件不存在: {cv}"); continue
                            self.engine.paste_file_to_wechat_silent(cv); sent += 1
                        if i < len(contents) - 1: time.sleep(1.5 + random.uniform(0.3, 0.8))
                    self.task_finished.emit(tid, True, f"已发送 {sent}/{len(contents)} 条 → {task['group']}")
                except Exception as e: self.task_finished.emit(tid, False, f"{e} → {task['group']}")
                if idx < total - 1: time.sleep(2.0 + random.uniform(0.5, 1.5))
            self.log_signal.emit(f"[Queue] ═══ 全部完毕 ═══"); self.all_done.emit()
        finally: self.engine.log_callback = None


# ═══════════════════════ 任务列表页 ════════════════════════════

class EditTaskDialog(QDialog):
    task_updated = pyqtSignal(dict)
    def __init__(self, task, parent=None):
        super().__init__(parent); self.task = json.loads(json.dumps(task)); self.content_items = []
        self.setWindowTitle("编辑任务"); self.setFixedSize(370, 600); self.setStyleSheet(f"background:{C['white']};"); self._build()
    def _build(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); scroll.setStyleSheet(f"background:{C['white']};border:none;")
        content = QWidget(); self.form = QVBoxLayout(content); self.form.setContentsMargins(20, 16, 20, 16); self.form.setSpacing(12)
        t = QLabel("编辑任务"); t.setFont(QFont("Microsoft YaHei", 14, QFont.Bold)); t.setStyleSheet(f"color:{C['gray800']};"); self.form.addWidget(t)
        self.form.addWidget(QLabel("目标群聊/联系人")); self.gi = QLineEdit(self.task["group"]); self.gi.setFixedHeight(40); self.gi.setStyleSheet(self._is()); self.form.addWidget(self.gi)
        self.form.addWidget(QLabel("计划发送时间")); self.dte = QDateTimeEdit(); self.dte.setDisplayFormat("yyyy-MM-dd HH:mm"); self.dte.setCalendarPopup(True)
        try: self.dte.setDateTime(QDateTime.fromString(self.task["datetime"], "yyyy-MM-dd HH:mm"))
        except: self.dte.setDateTime(QDateTime.currentDateTime().addSecs(300))
        self.dte.setFixedHeight(40); self.dte.setStyleSheet(self._is()); self.form.addWidget(self.dte)
        self.form.addWidget(QLabel("推送内容")); self.cc = QWidget(); self.cll = QVBoxLayout(self.cc); self.cll.setContentsMargins(0, 0, 0, 0); self.cll.setSpacing(8); self.form.addWidget(self.cc)
        for item in self.task.get("contents", []): self._ac(item["type"], item.get("value", ""))

        # 文字按钮 + 拖拽区
        tb = QPushButton("+ 文字"); tb.setFont(QFont("Microsoft YaHei", 8, QFont.Bold)); tb.setFixedHeight(30); tb.setCursor(QCursor(Qt.PointingHandCursor))
        tb.setStyleSheet(f"QPushButton{{background:{C['blue500']}10;color:{C['blue500']};border:1px dashed {C['blue500']}60;border-radius:6px;padding:0 8px;}} QPushButton:hover{{background:{C['blue500']}20;}}")
        tb.clicked.connect(lambda: self._ac("text")); self.form.addWidget(tb)
        dz = DropZone(); dz.file_dropped.connect(self._on_drop); self.form.addWidget(dz)

        self.form.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Expanding))
        sb = QPushButton("  保存修改"); sb.setIcon(svg_icon("save", 16, "#ffffff")); sb.setFixedHeight(44); sb.setCursor(QCursor(Qt.PointingHandCursor)); sb.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        sb.setStyleSheet(f"QPushButton{{background:{C['green500']};color:white;border:none;border-radius:12px;}} QPushButton:hover{{background:{C['green600']};}}"); sb.clicked.connect(self._save); self.form.addWidget(sb)
        cb = QPushButton("取消"); cb.setFixedHeight(40); cb.setCursor(QCursor(Qt.PointingHandCursor))
        cb.setStyleSheet(f"QPushButton{{background:transparent;color:{C['gray500']};border:1px solid {C['gray200']};border-radius:12px;}} QPushButton:hover{{background:{C['gray100']};}}"); cb.clicked.connect(self.reject); self.form.addWidget(cb)
        scroll.setWidget(content); outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(scroll)
    def _is(self): return f"QLineEdit,QDateTimeEdit{{background:{C['gray50']};border:1px solid {C['gray200']};border-radius:8px;padding:0 12px;font-size:12px;color:{C['gray700']};}} QLineEdit:focus,QDateTimeEdit:focus{{border-color:{C['green500']};}}"
    def _ac(self, ct, cv=""):
        i = ContentEditorItem(len(self.content_items), ct, cv); i.remove_requested.connect(self._rm); i.move_up_requested.connect(self._mu); i.move_down_requested.connect(self._md); self.content_items.append(i); self.cll.addWidget(i)
    def _on_drop(self, ftype, fpath):
        self._ac(ftype, fpath)
    def _rm(self, idx): d = [i.get_data() for i in self.content_items]; d.pop(idx) if 0 <= idx < len(d) else None; self._rb(d)
    def _mu(self, idx):
        d = [i.get_data() for i in self.content_items]
        if idx > 0: d[idx], d[idx-1] = d[idx-1], d[idx]; self._rb(d)
    def _md(self, idx):
        d = [i.get_data() for i in self.content_items]
        if idx < len(d)-1: d[idx], d[idx+1] = d[idx+1], d[idx]; self._rb(d)
    def _rb(self, data):
        for i in self.content_items: self.cll.removeWidget(i); i.setParent(None); i.deleteLater()
        self.content_items.clear()
        for d in data: self._ac(d["type"], d["value"])
    def _save(self):
        g = self.gi.text().strip()
        if not g: QMessageBox.warning(self, "提示", "请填写目标"); return
        contents = [i.get_data() for i in self.content_items if i.get_data()["value"]]
        if not contents: QMessageBox.warning(self, "提示", "至少一条内容"); return
        self.task["group"] = g; self.task["datetime"] = self.dte.dateTime().toString("yyyy-MM-dd HH:mm"); self.task["contents"] = contents
        self.task_updated.emit(self.task); self.accept()

class TaskCard(QFrame):
    delete_clicked = pyqtSignal(str); toggle_clicked = pyqtSignal(str); run_now_clicked = pyqtSignal(str); edit_clicked = pyqtSignal(str)
    def __init__(self, task, parent=None):
        super().__init__(parent); self._tid = str(task["id"]); oid = f"TC_{self._tid}"; self.setObjectName(oid); self._build(task, oid)
    def _build(self, task, oid):
        active = task.get("active", True); contents = task.get("contents", []); bc = C["green500"]+"30" if active else C["gray200"]
        self.setStyleSheet(f"QFrame#{oid}{{background:{C['white']};border:1px solid {bc};border-radius:14px;}}"); self.setGraphicsEffect(make_shadow(12, 0, 2, 20 if active else 8))
        ml = QVBoxLayout(self); ml.setContentsMargins(16, 14, 16, 10); ml.setSpacing(8)
        top = QHBoxLayout(); top.setSpacing(10); ft = contents[0]["type"] if contents else "text"; multi = len(set(c["type"] for c in contents)) > 1 if contents else False
        tif = QFrame(); tif.setFixedSize(34, 34); tif.setStyleSheet(f"background:{C['orange50'] if multi else C['blue50']};border-radius:8px;")
        til = QVBoxLayout(tif); til.setContentsMargins(7, 7, 7, 7); ic = QLabel()
        if multi: ic.setPixmap(svg_to_pixmap(ICONS["plus_circle"], 20, C["orange500"]))
        else: ic.setPixmap(svg_to_pixmap(ICONS[{"text": "message", "image": "image", "video": "video"}.get(ft, "message")], 20, C["blue500"]))
        ic.setAlignment(Qt.AlignCenter); til.addWidget(ic)
        info = QVBoxLayout(); info.setSpacing(2); nl = QLabel(task["group"]); nl.setFont(QFont("Microsoft YaHei", 10, QFont.Bold)); nl.setStyleSheet(f"color:{C['gray800']};background:transparent;border:none;")
        dt_str = task.get("datetime", ""); tr = QHBoxLayout(); tr.setSpacing(4)
        cl = QLabel(); cl.setPixmap(svg_to_pixmap(ICONS["calendar"], 12, C["gray400"])); cl.setFixedSize(14, 14); cl.setStyleSheet("background:transparent;border:none;")
        td, tcol = dt_str, C['gray500']
        try:
            if datetime.strptime(dt_str, "%Y-%m-%d %H:%M") < datetime.now() and active: td, tcol = dt_str+" (已过期)", C['red400']
        except: pass
        ttl = QLabel(td); ttl.setFont(QFont("Microsoft YaHei", 8)); ttl.setStyleSheet(f"color:{tcol};background:transparent;border:none;")
        cnt = QLabel(f"{len(contents)} 条"); cnt.setFont(QFont("Microsoft YaHei", 7, QFont.Bold)); cnt.setStyleSheet(f"color:{C['blue500']};background:{C['blue50']};border-radius:4px;padding:1px 6px;border:none;")
        tr.addWidget(cl); tr.addWidget(ttl); tr.addStretch(); tr.addWidget(cnt); info.addWidget(nl); info.addLayout(tr)
        toggle = ToggleSwitch(checked=active); _t = self._tid; toggle.toggled.connect(lambda _, t=_t: self.toggle_clicked.emit(t))
        top.addWidget(tif); top.addLayout(info, 1); top.addWidget(toggle); ml.addLayout(top)
        for i, item in enumerate(contents): ml.addWidget(ContentItemWidget(i, item.get("type", "text"), item.get("value", "")))
        br = QHBoxLayout(); br.setSpacing(6)
        for label, icon, color, sig in [("  发送", "play", C["orange500"], self.run_now_clicked), ("  编辑", "edit", C["blue500"], self.edit_clicked)]:
            b = QPushButton(label); b.setIcon(svg_icon(icon, 13, color)); b.setIconSize(QSize(13, 13)); b.setCursor(QCursor(Qt.PointingHandCursor)); b.setFont(QFont("Microsoft YaHei", 8, QFont.Bold)); b.setFixedHeight(28)
            bgc = C['orange50'] if "发送" in label else C['blue50']
            b.setStyleSheet(f"QPushButton{{background:{bgc};color:{color};border:1px solid {color}40;border-radius:7px;padding:0 10px;}} QPushButton:hover{{border-color:{color};}}")
            b.clicked.connect(lambda _, t=_t, s=sig: s.emit(t)); br.addWidget(b)
        br.addStretch()
        db = QPushButton("  删除"); db.setIcon(svg_icon("trash", 13, C["red400"])); db.setIconSize(QSize(13, 13)); db.setCursor(QCursor(Qt.PointingHandCursor)); db.setFont(QFont("Microsoft YaHei", 8, QFont.Bold)); db.setFixedHeight(28)
        db.setStyleSheet(f"QPushButton{{background:{C['red50']};color:{C['red400']};border:1px solid {C['red400']}40;border-radius:7px;padding:0 10px;}} QPushButton:hover{{border-color:{C['red400']};}}")
        db.clicked.connect(lambda _, t=_t: self.delete_clicked.emit(t)); br.addWidget(db); ml.addLayout(br)

class TasksPage(QWidget):
    def __init__(self, mgr, parent=None):
        super().__init__(parent); self.mgr = mgr; l = QVBoxLayout(self); l.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.scroll.setStyleSheet(f"background:{C['bg']};")
        self.sc = QWidget(); self.sl = QVBoxLayout(self.sc); self.sl.setContentsMargins(16, 16, 16, 16); self.sl.setSpacing(14); self.sl.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.sc); l.addWidget(self.scroll)
    def refresh(self, tasks):
        while self.sl.count():
            w = self.sl.takeAt(0).widget()
            if w: w.setParent(None); w.deleteLater()
        hw = QWidget(); hl = QHBoxLayout(hw); hl.setContentsMargins(0, 0, 0, 4); lc = QVBoxLayout(); lc.setSpacing(2)
        t = QLabel("执行队列"); t.setFont(QFont("Microsoft YaHei", 14, QFont.Bold)); t.setStyleSheet(f"color:{C['gray800']};")
        s = QLabel("请保持微信窗口可见"); s.setFont(QFont("Microsoft YaHei", 8)); s.setStyleSheet(f"color:{C['gray500']};")
        lc.addWidget(t); lc.addWidget(s); ac = sum(1 for t in tasks if t.get("active"))
        badge = QLabel(f"  {ac} 个待办  "); badge.setFont(QFont("Microsoft YaHei", 9, QFont.Bold)); badge.setStyleSheet(f"color:{C['green600']};background:{C['green50']};border-radius:6px;padding:4px 8px;"); badge.setFixedHeight(28)
        hl.addLayout(lc, 1); hl.addWidget(badge); self.sl.addWidget(hw)
        if not tasks:
            ew = QWidget(); el = QVBoxLayout(ew); el.setAlignment(Qt.AlignCenter)
            ei = QLabel(); ei.setPixmap(svg_to_pixmap(ICONS["message"], 40, C["gray300"])); ei.setAlignment(Qt.AlignCenter)
            et = QLabel("暂无定时任务"); et.setFont(QFont("Microsoft YaHei", 10)); et.setStyleSheet(f"color:{C['gray400']};"); et.setAlignment(Qt.AlignCenter)
            el.addSpacerItem(QSpacerItem(0, 60, QSizePolicy.Minimum, QSizePolicy.Expanding)); el.addWidget(ei); el.addWidget(et); el.addSpacerItem(QSpacerItem(0, 60, QSizePolicy.Minimum, QSizePolicy.Expanding)); self.sl.addWidget(ew); return
        for task in sorted(tasks, key=lambda x: self._sk(x), reverse=True):
            card = TaskCard(task); card.delete_clicked.connect(self.mgr.delete_task); card.toggle_clicked.connect(self.mgr.toggle_task); card.run_now_clicked.connect(self.mgr.run_task_now); card.edit_clicked.connect(self.mgr.edit_task); self.sl.addWidget(card)
        self.sl.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
    @staticmethod
    def _sk(t):
        try: return datetime.strptime(t.get("datetime", ""), "%Y-%m-%d %H:%M")
        except: return datetime.min

# ═══════════════════════ 创建页（含拖拽）═══════════════════════

class GroupTagWidget(QFrame):
    remove_clicked = pyqtSignal(str)
    def __init__(self, name, parent=None):
        super().__init__(parent); self.group_name = name; oid = f"GT_{id(self)}"; self.setObjectName(oid)
        self.setStyleSheet(f"QFrame#{oid}{{background:{C['green50']};border:1px solid {C['green500']}40;border-radius:14px;}}")
        lay = QHBoxLayout(self); lay.setContentsMargins(10, 3, 6, 3); lay.setSpacing(4)
        ic = QLabel(); ic.setPixmap(svg_to_pixmap(ICONS["users"], 12, C["green600"])); ic.setFixedSize(14, 14); ic.setStyleSheet("border:none;background:transparent;")
        nl = QLabel(name); nl.setFont(QFont("Microsoft YaHei", 9)); nl.setStyleSheet(f"color:{C['green600']};background:transparent;border:none;")
        db = QPushButton("✕"); db.setFixedSize(18, 18); db.setCursor(QCursor(Qt.PointingHandCursor)); db.setFont(QFont("Microsoft YaHei", 7))
        db.setStyleSheet(f"QPushButton{{background:transparent;color:{C['green500']};border:none;border-radius:9px;}} QPushButton:hover{{background:{C['red50']};color:{C['red400']};}}")
        db.clicked.connect(lambda: self.remove_clicked.emit(self.group_name)); lay.addWidget(ic); lay.addWidget(nl); lay.addWidget(db)

class TaskSlotWidget(QFrame):
    """时段任务卡片 — 含拖拽上传"""
    remove_requested = pyqtSignal(int)
    def __init__(self, index, parent=None):
        super().__init__(parent); self.index = index; self.content_items = []
        oid = f"TS_{id(self)}"; self.setObjectName(oid)
        colors = [C["blue500"], C["purple500"], C["orange500"], C["green500"], C["indigo500"]]
        accent = colors[index % len(colors)]; self._accent = accent
        self.setStyleSheet(f"QFrame#{oid}{{background:{C['white']};border:1px solid {C['gray200']};border-left:4px solid {accent};border-radius:12px;}}")
        self.setGraphicsEffect(make_shadow(8, 0, 2, 12))
        ml = QVBoxLayout(self); ml.setContentsMargins(14, 12, 14, 12); ml.setSpacing(10)
        top = QHBoxLayout(); top.setSpacing(6)
        num = QLabel(f"⏰ 时段 {index + 1}"); num.setFont(QFont("Microsoft YaHei", 10, QFont.Bold)); num.setStyleSheet(f"color:{accent};background:transparent;border:none;")
        top.addWidget(num); top.addStretch()
        del_btn = QPushButton(); del_btn.setIcon(svg_icon("x_circle", 16, C["red400"])); del_btn.setIconSize(QSize(16, 16)); del_btn.setFixedSize(26, 26)
        del_btn.setCursor(QCursor(Qt.PointingHandCursor)); del_btn.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:6px;}} QPushButton:hover{{background:{C['red50']};}}")
        del_btn.clicked.connect(lambda: self.remove_requested.emit(self.index)); top.addWidget(del_btn); ml.addLayout(top)

        # 时间
        tr = QHBoxLayout(); tr.setSpacing(8)
        tl = QLabel(); tl.setPixmap(svg_to_pixmap(ICONS["calendar"], 14, C["gray400"])); tl.setFixedSize(16, 16); tl.setStyleSheet("border:none;background:transparent;")
        self.dte = QDateTimeEdit(); self.dte.setDisplayFormat("yyyy-MM-dd HH:mm"); self.dte.setCalendarPopup(True)
        self.dte.setDateTime(QDateTime.currentDateTime().addSecs(300 + index * 3600)); self.dte.setMinimumDateTime(QDateTime.currentDateTime()); self.dte.setFixedHeight(38)
        self.dte.setStyleSheet(f"QDateTimeEdit{{background:{C['gray50']};border:1px solid {C['gray200']};border-radius:8px;padding:0 10px;font-size:11px;color:{C['gray700']};}} QDateTimeEdit:focus{{border-color:{accent};}}")
        tr.addWidget(tl); tr.addWidget(self.dte, 1); ml.addLayout(tr)

        # 内容列表
        self.content_container = QWidget(); self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0); self.content_layout.setSpacing(6); ml.addWidget(self.content_container)

        # 文字按钮
        tb = QPushButton("+ 文字"); tb.setFont(QFont("Microsoft YaHei", 7, QFont.Bold)); tb.setFixedHeight(28)
        tb.setCursor(QCursor(Qt.PointingHandCursor))
        tb.setStyleSheet(f"QPushButton{{background:{C['blue500']}10;color:{C['blue500']};border:1px dashed {C['blue500']}60;border-radius:6px;padding:0 6px;}} QPushButton:hover{{background:{C['blue500']}20;border:1px solid {C['blue500']};}}")
        tb.clicked.connect(lambda: self._add_content("text")); ml.addWidget(tb)

        # ★ 拖拽上传区域
        dz = DropZone(accept_types=["image", "video"])
        dz.file_dropped.connect(self._on_file_dropped)
        ml.addWidget(dz)

    def _on_file_dropped(self, ftype, fpath):
        """拖拽文件回调"""
        self._add_content(ftype, fpath)

    def _add_content(self, ct, cv=""):
        item = ContentEditorItem(len(self.content_items), ct, cv)
        item.remove_requested.connect(self._remove_content)
        item.move_up_requested.connect(self._move_up)
        item.move_down_requested.connect(self._move_down)
        self.content_items.append(item); self.content_layout.addWidget(item)
    def _remove_content(self, idx):
        data = [i.get_data() for i in self.content_items]
        if 0 <= idx < len(data): data.pop(idx)
        self._rebuild_content(data)
    def _move_up(self, idx):
        data = [i.get_data() for i in self.content_items]
        if idx > 0: data[idx], data[idx-1] = data[idx-1], data[idx]; self._rebuild_content(data)
    def _move_down(self, idx):
        data = [i.get_data() for i in self.content_items]
        if idx < len(data)-1: data[idx], data[idx+1] = data[idx+1], data[idx]; self._rebuild_content(data)
    def _rebuild_content(self, data):
        for i in self.content_items: self.content_layout.removeWidget(i); i.setParent(None); i.deleteLater()
        self.content_items.clear()
        for d in data: self._add_content(d["type"], d["value"])
    def collect_contents(self):
        result = []
        for item in self.content_items:
            d = item.get_data()
            if not d["value"]: continue
            if d["type"] in ("image", "video") and not os.path.exists(d["value"]): return None, d["value"]
            result.append(d)
        return result, ""
    def get_datetime_str(self): return self.dte.dateTime().toString("yyyy-MM-dd HH:mm")
    def get_qdatetime(self): return self.dte.dateTime()
    def update_min_datetime(self): self.dte.setMinimumDateTime(QDateTime.currentDateTime())

class CreatePage(QWidget):
    tasks_created = pyqtSignal(list)
    def __init__(self, parent=None):
        super().__init__(parent); self.group_list = []; self.task_slots = []; self._build()
    def _build(self):
        self.setStyleSheet(f"background:{C['white']};")
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background:{C['white']};border:none;")
        content = QWidget(); self.form = QVBoxLayout(content); self.form.setContentsMargins(16, 16, 16, 16); self.form.setSpacing(12)
        title = QLabel("新建推送任务"); title.setFont(QFont("Microsoft YaHei", 15, QFont.Bold)); title.setStyleSheet(f"color:{C['gray800']};"); self.form.addWidget(title)

        # 群聊区
        sec1 = QFrame(); s1id = f"S1_{id(sec1)}"; sec1.setObjectName(s1id)
        sec1.setStyleSheet(f"QFrame#{s1id}{{background:{C['gray50']};border:1px solid {C['gray100']};border-radius:12px;}}")
        s1l = QVBoxLayout(sec1); s1l.setContentsMargins(14, 12, 14, 12); s1l.setSpacing(8)
        gl = QHBoxLayout(); gl.setSpacing(6)
        gi_icon = QLabel(); gi_icon.setPixmap(svg_to_pixmap(ICONS["users"], 16, C["green600"])); gi_icon.setFixedSize(18, 18); gi_icon.setStyleSheet("border:none;background:transparent;")
        gl_text = QLabel("目标群聊 / 联系人"); gl_text.setFont(QFont("Microsoft YaHei", 10, QFont.Bold)); gl_text.setStyleSheet(f"color:{C['gray700']};background:transparent;border:none;")
        gl.addWidget(gi_icon); gl.addWidget(gl_text); gl.addStretch(); s1l.addLayout(gl)
        input_row = QHBoxLayout(); input_row.setSpacing(6)
        self.gi = QLineEdit(); self.gi.setPlaceholderText("输入群名，多个用逗号隔开"); self.gi.setFixedHeight(40)
        self.gi.setStyleSheet(f"QLineEdit{{background:{C['white']};border:1px solid {C['gray200']};border-radius:8px;padding:0 12px;font-size:11px;color:{C['gray700']};}} QLineEdit:focus{{border-color:{C['green500']};}}")
        self.gi.returnPressed.connect(self._add_groups); input_row.addWidget(self.gi, 1)
        add_btn = QPushButton("添加"); add_btn.setFixedSize(52, 40); add_btn.setCursor(QCursor(Qt.PointingHandCursor)); add_btn.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        add_btn.setStyleSheet(f"QPushButton{{background:{C['green500']};color:white;border:none;border-radius:8px;}} QPushButton:hover{{background:{C['green600']};}}")
        add_btn.clicked.connect(self._add_groups); input_row.addWidget(add_btn); s1l.addLayout(input_row)
        self.tags_container = QWidget(); self._init_tags_empty(); s1l.addWidget(self.tags_container)
        self.group_count_label = QLabel(); self.group_count_label.setFont(QFont("Microsoft YaHei", 8)); self.group_count_label.setStyleSheet(f"color:{C['gray400']};background:transparent;border:none;"); s1l.addWidget(self.group_count_label)
        self.form.addWidget(sec1)

        # 时段区
        sec2h = QHBoxLayout(); sec2h.setSpacing(6)
        s2i = QLabel(); s2i.setPixmap(svg_to_pixmap(ICONS["layers"], 16, C["indigo500"])); s2i.setFixedSize(18, 18); s2i.setStyleSheet("border:none;background:transparent;")
        s2t = QLabel("推送时段"); s2t.setFont(QFont("Microsoft YaHei", 10, QFont.Bold)); s2t.setStyleSheet(f"color:{C['gray700']};")
        self.slot_badge = QLabel("0"); self.slot_badge.setFont(QFont("Microsoft YaHei", 8, QFont.Bold)); self.slot_badge.setStyleSheet(f"color:{C['indigo500']};background:{C['indigo50']};border-radius:4px;padding:2px 8px;")
        sec2h.addWidget(s2i); sec2h.addWidget(s2t); sec2h.addStretch(); sec2h.addWidget(self.slot_badge); self.form.addLayout(sec2h)
        self.slots_container = QWidget(); self.slots_layout = QVBoxLayout(self.slots_container); self.slots_layout.setContentsMargins(0, 0, 0, 0); self.slots_layout.setSpacing(10); self.form.addWidget(self.slots_container)
        asb = QPushButton("  ＋ 新增时段"); asb.setIcon(svg_icon("plus_circle", 16, C["indigo500"])); asb.setIconSize(QSize(16, 16)); asb.setFixedHeight(40); asb.setCursor(QCursor(Qt.PointingHandCursor)); asb.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        asb.setStyleSheet(f"QPushButton{{background:{C['indigo50']};color:{C['indigo500']};border:2px dashed {C['indigo500']}50;border-radius:10px;}} QPushButton:hover{{background:{C['indigo500']}15;border-color:{C['indigo500']};}}")
        asb.clicked.connect(self._add_slot); self.form.addWidget(asb)
        self.preview_label = QLabel(); self.preview_label.setFont(QFont("Microsoft YaHei", 8)); self.preview_label.setStyleSheet(f"color:{C['gray500']};"); self.preview_label.setAlignment(Qt.AlignCenter); self.preview_label.setWordWrap(True); self.form.addWidget(self.preview_label)
        self.form.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Expanding))
        sb = QPushButton("  保存并加入队列"); sb.setIcon(svg_icon("check_circle", 18, "#ffffff")); sb.setIconSize(QSize(18, 18)); sb.setFixedHeight(48); sb.setCursor(QCursor(Qt.PointingHandCursor)); sb.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        sb.setStyleSheet(f"QPushButton{{background:{C['green500']};color:white;border:none;border-radius:14px;}} QPushButton:hover{{background:{C['green600']};}}")
        sb.setGraphicsEffect(make_shadow(20, 0, 4, 40)); sb.clicked.connect(self._submit); self.form.addWidget(sb)
        scroll.setWidget(content); outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(scroll)
        self._add_slot()
    def _init_tags_empty(self):
        lay = QVBoxLayout(self.tags_container); lay.setContentsMargins(0, 0, 0, 0)
        h = QLabel("💡 输入群名后点击添加或按回车"); h.setFont(QFont("Microsoft YaHei", 8)); h.setStyleSheet(f"color:{C['gray400']};"); h.setAlignment(Qt.AlignCenter); lay.addWidget(h)
    def _add_groups(self):
        raw = self.gi.text().strip().replace("，", ",")
        if not raw: return
        added = 0
        for n in [x.strip() for x in raw.split(",") if x.strip()]:
            if n not in self.group_list: self.group_list.append(n); added += 1
        if added > 0: self.gi.clear(); self._rebuild_tags(); self._update_preview()
    def _remove_group(self, name):
        if name in self.group_list: self.group_list.remove(name); self._rebuild_tags(); self._update_preview()
    def _rebuild_tags(self):
        pl = self.tags_container.parent().layout(); idx = pl.indexOf(self.tags_container)
        pl.removeWidget(self.tags_container); self.tags_container.setParent(None); self.tags_container.deleteLater()
        self.tags_container = QWidget(); to = QVBoxLayout(self.tags_container); to.setContentsMargins(0, 0, 0, 0); to.setSpacing(4)
        if self.group_list:
            cr = QHBoxLayout(); cr.setSpacing(6); cr.setAlignment(Qt.AlignLeft); rw = 0
            for name in self.group_list:
                tag = GroupTagWidget(name); tag.remove_clicked.connect(self._remove_group); est = len(name) * 14 + 50
                if rw + est > 290 and rw > 0: to.addLayout(cr); cr = QHBoxLayout(); cr.setSpacing(6); cr.setAlignment(Qt.AlignLeft); rw = 0
                cr.addWidget(tag); rw += est + 6
            cr.addStretch(); to.addLayout(cr)
        else:
            h = QLabel("💡 输入群名后点击添加或按回车"); h.setFont(QFont("Microsoft YaHei", 8)); h.setStyleSheet(f"color:{C['gray400']};"); h.setAlignment(Qt.AlignCenter); to.addWidget(h)
        pl.insertWidget(idx, self.tags_container); self.group_count_label.setText(f"已添加 {len(self.group_list)} 个目标" if self.group_list else "")
    def _add_slot(self):
        slot = TaskSlotWidget(len(self.task_slots)); slot.remove_requested.connect(self._remove_slot); self.task_slots.append(slot); self.slots_layout.addWidget(slot); self._update_preview()
    def _remove_slot(self, idx):
        if len(self.task_slots) <= 1: QMessageBox.information(self, "提示", "至少保留一个时段"); return
        data = [{"datetime": s.get_datetime_str(), "contents": [i.get_data() for i in s.content_items]} for s in self.task_slots]
        if 0 <= idx < len(data): data.pop(idx)
        for s in self.task_slots: self.slots_layout.removeWidget(s); s.setParent(None); s.deleteLater()
        self.task_slots.clear()
        for i, d in enumerate(data):
            slot = TaskSlotWidget(i); slot.remove_requested.connect(self._remove_slot)
            try: slot.dte.setDateTime(QDateTime.fromString(d["datetime"], "yyyy-MM-dd HH:mm"))
            except: pass
            for c in d.get("contents", []):
                if c.get("value"): slot._add_content(c["type"], c["value"])
            self.task_slots.append(slot); self.slots_layout.addWidget(slot)
        self._update_preview()
    def _update_preview(self):
        ng, ns = len(self.group_list), len(self.task_slots); self.slot_badge.setText(f"{ns} 个时段")
        if ng == 0: self.preview_label.setText("⬆️ 请先添加目标群聊")
        elif ng > 0 and ns > 0: self.preview_label.setText(f"📊 {ng} 个群聊 × {ns} 个时段 = {ng * ns} 个定时任务")
        else: self.preview_label.setText("")
    def _submit(self):
        if not self.group_list: self._add_groups()
        if not self.group_list: QMessageBox.warning(self, "提示", "请添加至少一个目标"); return
        now = QDateTime.currentDateTime(); sl = []
        for i, s in enumerate(self.task_slots):
            if s.get_qdatetime() < now: QMessageBox.warning(self, "提示", f"时段 {i+1} 时间已过期"); return
            c, bf = s.collect_contents()
            if c is None: QMessageBox.warning(self, "提示", f"时段 {i+1} 文件不存在:\n{bf}"); return
            if not c: QMessageBox.warning(self, "提示", f"时段 {i+1} 无内容"); return
            sl.append((s.get_datetime_str(), c))
        total = len(self.group_list) * len(sl)
        if total > 3:
            lines = [f"  • {g}  @ {dt}  ({len(c)}条)" for g in self.group_list for dt, c in sl]
            if QMessageBox.question(self, "确认", f"创建 {total} 个任务：\n\n" + "\n".join(lines[:12]), QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        tasks = []
        for g in self.group_list:
            for dt, c in sl:
                tasks.append({"id": generate_task_id(), "group": g, "datetime": dt, "contents": json.loads(json.dumps(c)), "active": True})
        self.tasks_created.emit(tasks); self._reset()
    def _reset(self):
        self.gi.clear(); self.group_list.clear(); self._rebuild_tags(); self._update_preview()
        for s in self.task_slots: self.slots_layout.removeWidget(s); s.setParent(None); s.deleteLater()
        self.task_slots.clear(); self._add_slot()
    def update_min_datetime(self):
        for s in self.task_slots: s.update_min_datetime()


# ═══════════════════════ 设置页 ═════════════════════════════════

class CollapsibleCard(QFrame):
    def __init__(self, title, icon_name, icon_color, collapsed=True, parent=None):
        super().__init__(parent); self._collapsed = collapsed; oid = f"CC_{id(self)}"; self.setObjectName(oid)
        self.setStyleSheet(f"QFrame#{oid}{{background:{C['white']};border:1px solid {C['gray100']};border-radius:14px;}}"); self.setGraphicsEffect(make_shadow(10, 0, 2, 15))
        self._ml = QVBoxLayout(self); self._ml.setContentsMargins(16, 14, 16, 14); self._ml.setSpacing(0)
        header = QWidget(); header.setCursor(QCursor(Qt.PointingHandCursor)); hl = QHBoxLayout(header); hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(8)
        ic = QLabel(); ic.setPixmap(svg_to_pixmap(ICONS[icon_name], 18, icon_color)); ic.setFixedSize(20, 20); ic.setStyleSheet("border:none;background:transparent;")
        tl = QLabel(title); tl.setFont(QFont("Microsoft YaHei", 11, QFont.Bold)); tl.setStyleSheet(f"color:{C['gray800']};background:transparent;border:none;")
        self._chev = QLabel(); self._uc(); self._chev.setFixedSize(20, 20); self._chev.setStyleSheet("border:none;background:transparent;")
        hl.addWidget(ic); hl.addWidget(tl); hl.addStretch(); hl.addWidget(self._chev); header.mousePressEvent = lambda e: self.toggle(); self._ml.addWidget(header)
        self._content = QWidget(); self._cl = QVBoxLayout(self._content); self._cl.setContentsMargins(0, 12, 0, 0); self._cl.setSpacing(10); self._ml.addWidget(self._content); self._content.setVisible(not self._collapsed)
    def content_layout(self): return self._cl
    def toggle(self): self._collapsed = not self._collapsed; self._content.setVisible(not self._collapsed); self._uc()
    def _uc(self): self._chev.setPixmap(svg_to_pixmap(ICONS["chevron_down" if self._collapsed else "chevron_up"], 16, C["gray400"]))

class ThemeSwitcher(QFrame):
    theme_changed = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent); oid = f"TS_{id(self)}"; self.setObjectName(oid)
        self.setStyleSheet(f"QFrame#{oid}{{background:{C['white']};border:1px solid {C['gray100']};border-radius:12px;}}"); self.setGraphicsEffect(make_shadow(8, 0, 2, 12))
        ml = QVBoxLayout(self); ml.setContentsMargins(14, 12, 14, 12); ml.setSpacing(10)
        top = QHBoxLayout(); ic = QLabel(); ic.setPixmap(svg_to_pixmap(ICONS["image"], 16, C["purple500"])); ic.setFixedSize(18, 18); ic.setStyleSheet("border:none;background:transparent;")
        tl = QLabel("微信主题模板"); tl.setFont(QFont("Microsoft YaHei", 11, QFont.Bold)); tl.setStyleSheet(f"color:{C['gray800']};background:transparent;border:none;")
        top.addWidget(ic); top.addWidget(tl); top.addStretch(); ml.addLayout(top)
        br = QHBoxLayout(); br.setSpacing(10)
        self.light_btn = self._mb("☀️", "浅色", C["amber500"], C["amber50"], "light")
        self.dark_btn = self._mb("🌙", "深色", C["indigo500"], C["indigo50"], "dark")
        br.addWidget(self.light_btn); br.addWidget(self.dark_btn); ml.addLayout(br)
        self.status = QLabel(); self.status.setFont(QFont("Microsoft YaHei", 8, QFont.Bold)); self.status.setAlignment(Qt.AlignCenter); self.status.setStyleSheet(f"color:{C['gray500']};background:transparent;border:none;"); ml.addWidget(self.status); self._uu()
    def _mb(self, emoji, title, color, bg, theme):
        btn = QFrame(); bid = f"TB_{theme}_{id(btn)}"; btn.setObjectName(bid); btn.setCursor(QCursor(Qt.PointingHandCursor)); btn.setFixedHeight(50)
        l = QVBoxLayout(btn); l.setContentsMargins(8, 6, 8, 6); l.setAlignment(Qt.AlignCenter)
        el = QLabel(f"{emoji} {title}"); el.setFont(QFont("Microsoft YaHei", 10, QFont.Bold)); el.setAlignment(Qt.AlignCenter); el.setStyleSheet(f"color:{C['gray700']};background:transparent;border:none;")
        l.addWidget(el); btn.mousePressEvent = lambda e, t=theme: self._sel(t); btn._theme = theme; btn._color = color; btn._bg = bg; btn._oid = bid; return btn
    def _sel(self, theme): set_current_theme(theme); self._uu(); self.theme_changed.emit(theme)
    def _uu(self):
        cur = get_current_theme()
        for btn in [self.light_btn, self.dark_btn]:
            a = btn._theme == cur
            btn.setStyleSheet(f"QFrame#{btn._oid}{{background:{btn._bg if a else C['gray50']};border:{'2px solid '+btn._color if a else '1px solid '+C['gray200']};border-radius:10px;}}")
        self.status.setText(f"当前：{'☀️ 浅色' if cur == 'light' else '🌙 深色'}")

class TemplateRow(QFrame):
    changed = pyqtSignal()
    def __init__(self, key, label, parent=None):
        super().__init__(parent); self.key = key; oid = f"TPL_{key}_{id(self)}"; self.setObjectName(oid)
        self.setStyleSheet(f"QFrame#{oid}{{background:{C['white']};border:1px solid {C['gray200']};border-radius:10px;}}")
        l = QVBoxLayout(self); l.setContentsMargins(12, 10, 12, 10); l.setSpacing(8)
        top = QHBoxLayout(); nl = QLabel(label); nl.setFont(QFont("Microsoft YaHei", 9, QFont.Bold)); nl.setStyleSheet(f"color:{C['gray700']};background:transparent;border:none;")
        self.tb = QLabel(); self.sl = QLabel(); top.addWidget(nl); top.addStretch(); top.addWidget(self.tb); top.addWidget(self.sl); l.addLayout(top)
        self.preview = QLabel(); self.preview.setFixedHeight(50); self.preview.setAlignment(Qt.AlignCenter); self.preview.setStyleSheet(f"background:{C['gray50']};border:1px solid {C['gray100']};border-radius:6px;"); l.addWidget(self.preview)
        br = QHBoxLayout(); br.setSpacing(8)
        ub = QPushButton("  上传"); ub.setIcon(svg_icon("upload", 14, C["blue500"])); ub.setFixedHeight(28); ub.setCursor(QCursor(Qt.PointingHandCursor)); ub.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
        ub.setStyleSheet(f"QPushButton{{background:{C['blue50']};color:{C['blue500']};border:1px solid {C['blue500']}40;border-radius:6px;padding:0 8px;}} QPushButton:hover{{border-color:{C['blue500']};}}")
        ub.clicked.connect(self._upload)
        rb = QPushButton("  默认"); rb.setFixedHeight(28); rb.setCursor(QCursor(Qt.PointingHandCursor)); rb.setFont(QFont("Microsoft YaHei", 8))
        rb.setStyleSheet(f"QPushButton{{background:transparent;color:{C['gray500']};border:1px solid {C['gray200']};border-radius:6px;padding:0 8px;}} QPushButton:hover{{background:{C['gray100']};}}")
        rb.clicked.connect(self._reset); br.addWidget(ub); br.addWidget(rb); br.addStretch(); l.addLayout(br); self._refresh()
    def _refresh(self):
        theme = get_current_theme(); self.tb.setText("☀️" if theme == "light" else "🌙"); self.tb.setStyleSheet(f"color:{C['amber500'] if theme=='light' else C['indigo500']};background:transparent;border:none;")
        p = get_template_path(self.key)
        if p and os.path.exists(p):
            pm = QPixmap(p)
            if not pm.isNull():
                self.preview.setPixmap(pm.scaled(200, 45, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                cfg = load_config(); ic = bool(cfg.get("templates", {}).get(theme, {}).get(self.key, ""))
                self.sl.setText("✅ 自定义" if ic else "📁 默认"); self.sl.setStyleSheet(f"color:{C['green500'] if ic else C['gray400']};background:transparent;border:none;"); return
        self.preview.setText("未找到"); self.preview.setPixmap(QPixmap()); self.sl.setText("⚠️ 缺失"); self.sl.setStyleSheet(f"color:{C['red400']};background:transparent;border:none;")
    def _upload(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择模板", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not p: return
        theme = get_current_theme(); dest = os.path.join(TEMPLATES_DIR, f"{self.key}_{theme}{os.path.splitext(p)[1]}")
        try: shutil.copy2(p, dest)
        except Exception as e: QMessageBox.warning(self, "错误", str(e)); return
        cfg = load_config(); cfg.setdefault("templates", {}).setdefault(theme, {})[self.key] = os.path.abspath(dest)
        learned = cfg.get("learned_scales", {}); [learned.pop(k, None) for k in list(learned) if self.key in k]; save_config(cfg); self._refresh(); self.changed.emit()
    def _reset(self):
        theme = get_current_theme(); cfg = load_config()
        if "templates" in cfg and theme in cfg["templates"] and self.key in cfg["templates"][theme]: del cfg["templates"][theme][self.key]; save_config(cfg)
        self._refresh(); self.changed.emit()

class LogConsole(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent); oid = f"LOG_{id(self)}"; self.setObjectName(oid)
        self.setStyleSheet(f"QFrame#{oid}{{background:{C['gray100']};border:1px solid {C['gray200']};border-radius:10px;}}"); self.setFixedHeight(150)
        l = QVBoxLayout(self); l.setContentsMargins(0, 0, 0, 0); l.setSpacing(0)
        hdr = QHBoxLayout(); hdr.setContentsMargins(12, 8, 12, 4)
        ti = QLabel(); ti.setPixmap(svg_to_pixmap(ICONS["terminal"], 14, C["gray400"])); ti.setFixedSize(16, 16); ti.setStyleSheet("border:none;background:transparent;")
        tl = QLabel("运行日志"); tl.setFont(QFont("Microsoft YaHei", 8, QFont.Bold)); tl.setStyleSheet(f"color:{C['gray500']};background:transparent;border:none;")
        hdr.addWidget(ti); hdr.addWidget(tl); hdr.addStretch(); l.addLayout(hdr)
        self.te = QTextEdit(); self.te.setReadOnly(True)
        self.te.setStyleSheet(f"QTextEdit{{background:{C['gray100']};border:none;padding:4px 12px;font-family:Consolas,monospace;font-size:10px;color:{C['gray500']};}}")
        l.addWidget(self.te)
    def append_log(self, text, color=None):
        if color: html = f'<span style="color:{color};">{text}</span>'
        elif "[Error]" in text or "❌" in text: html = f'<span style="color:{C["red400"]};">{text}</span>'
        elif "✅" in text: html = f'<span style="color:{C["green500"]};">{text}</span>'
        elif "[Match]" in text: html = f'<span style="color:{C["blue500"]};">{text}</span>'
        elif "[Queue]" in text: html = f'<span style="color:{C["purple500"]};font-weight:bold;">{text}</span>'
        elif "[Warn]" in text or "⚠️" in text: html = f'<span style="color:{C["orange500"]};">{text}</span>'
        else: html = f'<span style="color:{C["gray500"]};">{text}</span>'
        self.te.append(html); c = self.te.textCursor(); c.movePosition(QTextCursor.End); self.te.setTextCursor(c)


class SettingsPage(QWidget):
    calibrate_requested = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent); self.template_rows = []; self._build()
    def _build(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); scroll.setStyleSheet(f"background:{C['bg']};border:none;")
        content = QWidget(); layout = QVBoxLayout(content); layout.setContentsMargins(20, 20, 20, 20); layout.setSpacing(16)
        t = QLabel("系统配置"); t.setFont(QFont("Microsoft YaHei", 16, QFont.Bold)); t.setStyleSheet(f"color:{C['gray800']};"); layout.addWidget(t)

        # 校准
        cc = QFrame(); cid = f"cal_{id(cc)}"; cc.setObjectName(cid); cc.setStyleSheet(f"QFrame#{cid}{{background:{C['white']};border:1px solid {C['gray100']};border-radius:14px;}}"); cc.setGraphicsEffect(make_shadow(10, 0, 2, 15))
        cl = QVBoxLayout(cc); cl.setContentsMargins(16, 14, 16, 14)
        self.cal_btn = QPushButton("  重新校准微信窗口"); self.cal_btn.setIcon(svg_icon("monitor", 16, C["blue500"])); self.cal_btn.setFixedHeight(40); self.cal_btn.setCursor(QCursor(Qt.PointingHandCursor)); self.cal_btn.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.cal_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{C['blue500']};border:1px solid {C['blue500']};border-radius:10px;}} QPushButton:hover{{background:{C['blue50']};}}")
        self.cal_btn.clicked.connect(self.calibrate_requested.emit); cl.addWidget(self.cal_btn); layout.addWidget(cc)

        # 附件管理
        self.att_card = CollapsibleCard("附件管理", "paperclip", C["teal500"], collapsed=True)
        acl = self.att_card.content_layout()
        self.att_info = QLabel(); self.att_info.setFont(QFont("Microsoft YaHei", 8)); self.att_info.setStyleSheet(f"color:{C['gray500']};background:transparent;border:none;"); self.att_info.setWordWrap(True)
        acl.addWidget(self.att_info)
        abr = QHBoxLayout(); abr.setSpacing(6)
        open_btn = QPushButton("  打开目录"); open_btn.setIcon(svg_icon("folder", 13, C["blue500"])); open_btn.setFixedHeight(28); open_btn.setCursor(QCursor(Qt.PointingHandCursor)); open_btn.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
        open_btn.setStyleSheet(f"QPushButton{{background:{C['blue50']};color:{C['blue500']};border:1px solid {C['blue500']}40;border-radius:6px;padding:0 8px;}} QPushButton:hover{{border-color:{C['blue500']};}}")
        open_btn.clicked.connect(lambda: os.startfile(ATTACHMENTS_DIR) if os.path.exists(ATTACHMENTS_DIR) else None)
        self.clean_btn = QPushButton("  清理未引用"); self.clean_btn.setIcon(svg_icon("trash", 13, C["red400"])); self.clean_btn.setFixedHeight(28); self.clean_btn.setCursor(QCursor(Qt.PointingHandCursor)); self.clean_btn.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
        self.clean_btn.setStyleSheet(f"QPushButton{{background:{C['red50']};color:{C['red400']};border:1px solid {C['red400']}40;border-radius:6px;padding:0 8px;}} QPushButton:hover{{border-color:{C['red400']};}}")
        self.clean_btn.clicked.connect(self._clean_attachments)
        abr.addWidget(open_btn); abr.addWidget(self.clean_btn); abr.addStretch(); acl.addLayout(abr)
        layout.addWidget(self.att_card)

        # 主题
        self.theme_switcher = ThemeSwitcher(); self.theme_switcher.theme_changed.connect(self._on_theme_changed); layout.addWidget(self.theme_switcher)

        # 模板
        self.tpl_card = CollapsibleCard("视觉模板管理", "image", C["purple500"], collapsed=True); tcl = self.tpl_card.content_layout()
        for key in TEMPLATE_KEYS:
            row = TemplateRow(key, TEMPLATE_LABELS[key]); row.changed.connect(lambda k=key: self.log.append_log(f"[Template] {k} 已更新")); self.template_rows.append(row); tcl.addWidget(row)
        layout.addWidget(self.tpl_card)

        # 偏好
        pc = QFrame(); pid = f"pref_{id(pc)}"; pc.setObjectName(pid); pc.setStyleSheet(f"QFrame#{pid}{{background:{C['white']};border:1px solid {C['gray100']};border-radius:14px;}}"); pc.setGraphicsEffect(make_shadow(10, 0, 2, 15))
        pl = QVBoxLayout(pc); pl.setContentsMargins(16, 14, 16, 14); pl.setSpacing(14)
        pt = QLabel("模拟行为偏好"); pt.setFont(QFont("Microsoft YaHei", 11, QFont.Bold)); pt.setStyleSheet(f"color:{C['gray800']};background:transparent;border:none;"); pl.addWidget(pt)
        self.t_act = ToggleSwitch(True); pl.addLayout(self._pr("执行前自动唤醒", "强制窗口前置", self.t_act))
        self.t_dly = ToggleSwitch(True); pl.addLayout(self._pr("模拟人工延迟", "防封号保护", self.t_dly))
        layout.addWidget(pc)

        self.log = LogConsole(); layout.addWidget(self.log)
        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        scroll.setWidget(content); outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(scroll)

    def _pr(self, title, desc, toggle):
        r = QHBoxLayout(); tc = QVBoxLayout(); tc.setSpacing(2)
        t = QLabel(title); t.setFont(QFont("Microsoft YaHei", 10, QFont.Bold)); t.setStyleSheet(f"color:{C['gray700']};background:transparent;border:none;")
        d = QLabel(desc); d.setFont(QFont("Microsoft YaHei", 8)); d.setStyleSheet(f"color:{C['gray400']};background:transparent;border:none;")
        tc.addWidget(t); tc.addWidget(d); r.addLayout(tc, 1); r.addWidget(toggle); return r

    def _on_theme_changed(self, theme):
        self.log.append_log(f"[Theme] 切换到 {'☀️浅色' if theme=='light' else '🌙深色'}")
        for row in self.template_rows: row._refresh()
        AutoEngine.clear_learned_scales()

    def refresh_attachment_info(self, tasks):
        stats = AttachmentManager.get_stats(tasks)
        self.att_info.setText(
            f"📁 附件目录: {ATTACHMENTS_DIR}\n"
            f"📊 总计 {stats['total']} 个文件 ({stats['total_size_mb']} MB)\n"
            f"✅ 被引用 {stats['referenced']} 个 | ⚠️ 未引用 {stats['unreferenced']} 个"
        )

    def _clean_attachments(self):
        # 需要通过主窗口获取 tasks，此处发信号
        self._clean_requested = True
        self.log.append_log("[Attach] 请求清理未引用附件...")

    def append_log(self, text, color=None): self.log.append_log(text, color)
    def set_calibrating(self, v):
        if v: self.cal_btn.setText("  扫描中..."); self.cal_btn.setEnabled(False)
        else: self.cal_btn.setText("  重新校准微信窗口"); self.cal_btn.setEnabled(True)
    def refresh_diagnostic(self): pass


# ═══════════════════════ Main Window ════════════════════════════

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智推助手"); self.setFixedSize(390, 760)
        self.setWindowFlags(Qt.FramelessWindowHint); self.setAttribute(Qt.WA_TranslucentBackground)

        self.engine = AutoEngine()
        self.engine_status = "ready"; self._last_wx_state = None
        self.tasks = load_tasks_from_file()
        if not self.tasks:
            tmr = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            self.tasks = [
                {"id": generate_task_id(), "group": "产品研发沟通群", "datetime": f"{tmr} 10:00", "contents": [{"type": "text", "value": "大家早上好"}], "active": True},
            ]
            self._save()

        self.active_tab = "tasks"; self._drag_pos = None; self._fired_tasks = set()
        self._queue_runner = None; self._pending_exec = deque(); self._is_executing = False

        self._build_ui(); self._refresh_all()
        self.engine.log_callback = lambda msg: self.sp.append_log(msg)
        self.sp.append_log(f"[System] 已加载 {len(self.tasks)} 个任务，DPI={get_system_dpi()}")
        self.sp.refresh_attachment_info(self.tasks)

        # 定时器
        self.sched_timer = QTimer(self); self.sched_timer.timeout.connect(self._check_sched); self.sched_timer.start(5000)
        self.wx_timer = QTimer(self); self.wx_timer.timeout.connect(self._check_wx); self.wx_timer.start(3000)
        self.mindt_timer = QTimer(self); self.mindt_timer.timeout.connect(lambda: self.cp.update_min_datetime() if self.active_tab == "create" else None); self.mindt_timer.start(60000)

        # 附件清理定时检查
        self.att_timer = QTimer(self); self.att_timer.timeout.connect(self._check_clean_request); self.att_timer.start(500)

        QTimer.singleShot(300, self._check_wx)

    def _check_clean_request(self):
        if hasattr(self.sp, '_clean_requested') and self.sp._clean_requested:
            self.sp._clean_requested = False
            removed = AttachmentManager.cleanup_unreferenced(self.tasks)
            self.sp.append_log(f"[Attach] ✅ 已清理 {removed} 个未引用附件")
            self.sp.refresh_attachment_info(self.tasks)

    def _check_wx(self):
        if self._is_executing: return
        state = get_wechat_window_state()
        if state == "visible":
            if self.engine_status != "ready": self.set_engine_status("ready")
            if self._last_wx_state != "visible": self.sp.append_log("[System] ✅ 微信可见")
        elif state == "minimized":
            if self.engine_status != "error": self.set_engine_status("error")
            if self._last_wx_state != "minimized": self.sp.append_log("[Warn] ⚠️ 微信已最小化", C["orange500"])
        else:
            if self.engine_status != "error": self.set_engine_status("error")
            if self._last_wx_state != "not_found": self.sp.append_log("[Warn] ⚠️ 未找到微信", C["orange500"])
        self._last_wx_state = state

    @staticmethod
    def _parse_dt(s):
        try: return datetime.strptime(s, "%Y-%m-%d %H:%M")
        except: return None

    def _save(self): save_tasks_to_file(self.tasks)

    def _build_ui(self):
        outer = QVBoxLayout(self); outer.setContentsMargins(8, 8, 8, 8)
        self.ctn = QFrame(); self.ctn.setObjectName("MC")
        self.ctn.setStyleSheet(f"QFrame#MC{{background:{C['white']};border-radius:28px;border:5px solid {C['gray900']};}}")
        self.ctn.setGraphicsEffect(make_shadow(40, 0, 8, 80))
        cl = QVBoxLayout(self.ctn); cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(0)
        self.hdr = self._build_hdr(); cl.addWidget(self.hdr)
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background:{C['gray100']};"); cl.addWidget(sep)
        self.stk = QStackedWidget()
        self.tp = TasksPage(self); self.cp = CreatePage(); self.cp.tasks_created.connect(self._on_batch)
        self.sp = SettingsPage(); self.sp.calibrate_requested.connect(self._on_cal)
        self.stk.addWidget(self.tp); self.stk.addWidget(self.cp); self.stk.addWidget(self.sp)
        cl.addWidget(self.stk, 1); self.nav = self._build_nav(); cl.addWidget(self.nav); outer.addWidget(self.ctn)

    def _build_hdr(self):
        h = QFrame(); h.setFixedHeight(50); h.setStyleSheet(f"background:{C['white']};border-top-left-radius:24px;border-top-right-radius:24px;")
        l = QHBoxLayout(h); l.setContentsMargins(18, 8, 18, 8)
        left = QHBoxLayout(); left.setSpacing(8)
        il = QLabel(); il.setPixmap(svg_to_pixmap(ICONS["monitor"], 18, C["gray700"])); il.setFixedSize(20, 20)
        tl = QLabel("智推助手"); tl.setFont(QFont("Microsoft YaHei", 11, QFont.Bold)); tl.setStyleSheet(f"color:{C['gray800']};"); left.addWidget(il); left.addWidget(tl)
        cb = QPushButton("✕"); cb.setFixedSize(28, 28); cb.setCursor(QCursor(Qt.PointingHandCursor)); cb.setFont(QFont("Microsoft YaHei", 10))
        cb.setStyleSheet(f"QPushButton{{background:transparent;color:{C['gray400']};border:none;border-radius:14px;}} QPushButton:hover{{background:{C['gray100']};color:{C['gray700']};}}")
        cb.clicked.connect(self.close)
        self.sb = QFrame(); self.sb.setFixedHeight(26); self.sb.setStyleSheet(f"QFrame{{background:{C['gray50']};border:1px solid {C['gray100']};border-radius:13px;}}")
        bl = QHBoxLayout(self.sb); bl.setContentsMargins(10, 0, 10, 0); bl.setSpacing(6)
        self.sd = QLabel(); self.sd.setFixedSize(8, 8)
        self.st = QLabel("检测中..."); self.st.setFont(QFont("Microsoft YaHei", 8, QFont.Bold)); self.st.setStyleSheet(f"color:{C['gray600']};")
        self._set_dot(); bl.addWidget(self.sd); bl.addWidget(self.st)
        l.addLayout(left); l.addStretch(); l.addWidget(self.sb); l.addWidget(cb); return h

    def _set_dot(self):
        self.sd.setStyleSheet(f"background:{C['green500'] if self.engine_status == 'ready' else '#ef4444'};border-radius:4px;")

    def set_engine_status(self, s):
        self.engine_status = s; self.st.setText({"ready": "视觉就绪", "error": "未见微信"}.get(s, "检测中...")); self._set_dot()

    def _build_nav(self):
        n = QFrame(); n.setFixedHeight(75)
        n.setStyleSheet(f"QFrame{{background:{C['white']};border-top:1px solid {C['gray100']};border-bottom-left-radius:24px;border-bottom-right-radius:24px;}}")
        l = QHBoxLayout(n); l.setContentsMargins(10, 0, 10, 16); l.setSpacing(0)
        self.nt = self._nb("clock", "任务", "tasks"); l.addWidget(self.nt, 1, Qt.AlignCenter)
        cc = QWidget(); ccl = QVBoxLayout(cc); ccl.setContentsMargins(0, 0, 0, 0); ccl.setSpacing(4); ccl.setAlignment(Qt.AlignCenter)
        self.ncb = QPushButton(); self.ncb.setFixedSize(52, 52); self.ncb.setIcon(svg_icon("plus_circle", 28, "#ffffff")); self.ncb.setIconSize(QSize(28, 28))
        self.ncb.setCursor(QCursor(Qt.PointingHandCursor)); self.ncb.clicked.connect(lambda: self._sw("create")); self._ucb(); self.ncb.setGraphicsEffect(make_shadow(16, 0, 4, 60))
        self.ncl = QLabel("新建"); self.ncl.setFont(QFont("Microsoft YaHei", 7, QFont.Bold)); self.ncl.setAlignment(Qt.AlignCenter); self.ncl.setStyleSheet(f"color:{C['gray600']};")
        ccl.addWidget(self.ncb, 0, Qt.AlignCenter); ccl.addWidget(self.ncl); l.addWidget(cc, 1, Qt.AlignCenter)
        self.ns = self._nb("settings", "设置", "settings"); l.addWidget(self.ns, 1, Qt.AlignCenter); return n

    def _nb(self, icon, label, tab):
        c = QWidget(); l = QVBoxLayout(c); l.setContentsMargins(0, 4, 0, 0); l.setSpacing(3); l.setAlignment(Qt.AlignCenter)
        b = QPushButton(); b.setFixedSize(32, 32); b.setCursor(QCursor(Qt.PointingHandCursor)); b.setStyleSheet("background:transparent;border:none;")
        b.clicked.connect(lambda: self._sw(tab)); b.setObjectName(f"n_{tab}")
        lb = QLabel(label); lb.setFont(QFont("Microsoft YaHei", 7, QFont.Bold)); lb.setAlignment(Qt.AlignCenter); lb.setObjectName(f"nl_{tab}")
        l.addWidget(b, 0, Qt.AlignCenter); l.addWidget(lb, 0, Qt.AlignCenter); return c

    def _un(self):
        for tn, iname in [("tasks", "clock"), ("settings", "settings")]:
            a = self.active_tab == tn; col = C["green500"] if a else C["gray400"]
            b = self.findChild(QPushButton, f"n_{tn}")
            if b: b.setIcon(svg_icon(iname, 22, col)); b.setIconSize(QSize(22, 22))
            lb = self.findChild(QLabel, f"nl_{tn}")
            if lb: lb.setStyleSheet(f"color:{col};")
        self._ucb(); self.ncl.setStyleSheet(f"color:{C['green500'] if self.active_tab == 'create' else C['gray600']};")

    def _ucb(self):
        a = self.active_tab == "create"; bg = C["green500"] if a else C["gray800"]
        self.ncb.setStyleSheet(f"QPushButton{{background:{bg};border-radius:26px;border:none;}} QPushButton:hover{{background:{C['green600'] if a else C['gray700']};}}")

    def _sw(self, tab):
        self.active_tab = tab; self.stk.setCurrentIndex({"tasks": 0, "create": 1, "settings": 2}.get(tab, 0)); self._un()
        if tab == "tasks": self._rt()
        elif tab == "create": self.cp.update_min_datetime()
        elif tab == "settings": self.sp.refresh_attachment_info(self.tasks)

    def _refresh_all(self): self._rt(); self._un()
    def _rt(self): self.tp.refresh(self.tasks)
    def delete_task(self, tid):
        self.tasks = [t for t in self.tasks if str(t["id"]) != str(tid)]; self._fired_tasks.discard(str(tid)); self._save(); self._rt()
    def toggle_task(self, tid):
        for t in self.tasks:
            if str(t["id"]) == str(tid): t["active"] = not t["active"]; break
        self._save(); self._rt()
    def run_task_now(self, tid):
        task = next((t for t in self.tasks if str(t["id"]) == str(tid)), None)
        if task: self.sp.append_log(f"[Manual] {task['group']}"); self._enqueue([task])
    def edit_task(self, tid):
        task = next((t for t in self.tasks if str(t["id"]) == str(tid)), None)
        if task: dlg = EditTaskDialog(task, self); dlg.task_updated.connect(self._on_updated); dlg.exec_()
    def _on_updated(self, updated):
        for i, t in enumerate(self.tasks):
            if str(t["id"]) == str(updated["id"]): self.tasks[i] = updated; break
        self._fired_tasks.discard(str(updated["id"])); self._save(); self._rt()
    def _on_batch(self, task_list):
        for task in task_list: self.tasks.append(task)
        self._save(); self._sw("tasks")
        self.sp.append_log(f"[Task] ✅ 新增 {len(task_list)} 个任务")
    def _on_cal(self):
        self.sp.set_calibrating(True); QTimer.singleShot(300, self._do_cal)
    def _do_cal(self):
        ok = self.engine.calibrate_silent()
        if ok:
            r = self.engine.wx_region; self.sp.append_log(f"[Vision] ✅ ({r[0]},{r[1]}) {r[2]}x{r[3]} DPI={self.engine._current_dpi}")
        else: self.sp.append_log("[Vision] ❌ 校准失败")
        self.sp.set_calibrating(False)
    def _check_sched(self):
        now = datetime.now(); batch = []
        for t in self.tasks:
            if not t.get("active"): continue
            tid = str(t["id"])
            if tid in self._fired_tasks: continue
            dt = self._parse_dt(t.get("datetime", ""))
            if not dt: continue
            diff = (now - dt).total_seconds()
            if -10 <= diff <= 90: self._fired_tasks.add(tid); batch.append(t)
        if batch: self._enqueue(batch)
    def _enqueue(self, tasks):
        for t in tasks: self._pending_exec.append(t)
        if not self._is_executing: self._start_queue()
    def _start_queue(self):
        if not self._pending_exec: self._is_executing = False; return
        self._is_executing = True; batch = list(self._pending_exec); self._pending_exec.clear()
        runner = TaskQueueRunner(batch, self.engine)
        runner.log_signal.connect(self.sp.append_log); runner.task_finished.connect(self._on_task_done); runner.all_done.connect(self._on_queue_done)
        self._queue_runner = runner; runner.start()
    def _on_task_done(self, tid, ok, msg):
        self.sp.append_log(f"[Result] {'✅' if ok else '❌'} {msg}")
        if ok:
            for t in self.tasks:
                if str(t["id"]) == str(tid): t["active"] = False; break
            self._save(); self._rt()
        else: self._fired_tasks.discard(str(tid))
    def _on_queue_done(self):
        self._queue_runner = None; self._is_executing = False
        if self._pending_exec: self._start_queue()
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.y() < 60: self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton: self.move(e.globalPos() - self._drag_pos)
    def mouseReleaseEvent(self, e): self._drag_pos = None
    def closeEvent(self, e): self._save(); e.accept()


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLE)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())