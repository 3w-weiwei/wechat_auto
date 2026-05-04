from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from .events import DomainEvent
from .models import (
    AppConfig,
    AttachmentInfo,
    AttachmentStats,
    Task,
    WindowInfo,
    WindowRect,
)

# ─── Logging ───


class ILogger(ABC):
    """Log output interface."""

    @abstractmethod
    def log(self, message: str, level: str = "info") -> None: ...


# ─── Event Bus ───


class IEventBus(ABC):
    """Publish-subscribe for engine events."""

    @abstractmethod
    def publish(self, event: DomainEvent) -> None: ...

    @abstractmethod
    def subscribe(self, event_type: type[DomainEvent], handler: Callable) -> None: ...


# ─── Platform Abstraction ───


class IPlatformAdapter(ABC):
    """All OS-specific operations through this interface."""

    @abstractmethod
    def get_dpi_scale(self) -> float: ...

    @abstractmethod
    def get_system_dpi(self) -> int: ...

    @abstractmethod
    def find_window_by_title(self, title: str) -> WindowInfo | None: ...

    @abstractmethod
    def get_window_rect(self, hwnd: Any) -> WindowRect: ...

    @abstractmethod
    def activate_window(self, hwnd: Any) -> bool: ...

    @abstractmethod
    def is_window_visible(self, hwnd: Any) -> bool: ...

    @abstractmethod
    def is_window_minimized(self, hwnd: Any) -> bool: ...

    @abstractmethod
    def restore_window(self, hwnd: Any) -> bool: ...

    @abstractmethod
    def open_directory(self, path: str) -> None: ...


# ─── Screenshot Abstraction ───


class IScreenshotAdapter(ABC):
    """Cross-platform screenshot capability."""

    @abstractmethod
    def capture(self, region: WindowRect | None = None) -> Any: ...


# ─── Clipboard Abstraction ───


class IClipboardAdapter(ABC):
    """Clipboard operations, including file paste support."""

    @abstractmethod
    def copy_text(self, text: str) -> None: ...

    @abstractmethod
    def get_text(self) -> str: ...

    @abstractmethod
    def copy_files(self, paths: list[str]) -> None: ...


# ─── Input Abstraction ───


class IInputAdapter(ABC):
    """Mouse and keyboard simulation."""

    @abstractmethod
    def move_mouse(self, x: int, y: int, duration: float = 0.15) -> None: ...

    @abstractmethod
    def click(self, x: int, y: int, clicks: int = 1, interval: float = 0.08) -> None: ...

    @abstractmethod
    def press_key(self, key: str) -> None: ...

    @abstractmethod
    def hotkey(self, *keys: str) -> None: ...

    @abstractmethod
    def sleep(self, seconds: float) -> None: ...


# ─── Messaging Platform Abstraction (Plugin System) ───


class IMessagingPlatform(ABC):
    """Adapter for a messaging app (WeChat, WhatsApp, Telegram, etc.)."""

    name: str

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def locate_app(self) -> WindowInfo | None: ...

    @abstractmethod
    def navigate_to_chat(self, chat_name: str) -> bool: ...

    @abstractmethod
    def send_text(self, text: str) -> bool: ...

    @abstractmethod
    def send_file(self, filepath: str) -> bool: ...

    @abstractmethod
    def get_required_theme(self) -> str | None: ...


# ─── Storage Abstraction ───


class ITaskRepository(ABC):
    """CRUD for scheduled tasks."""

    @abstractmethod
    def get_all(self) -> list[Task]: ...

    @abstractmethod
    def get_by_id(self, task_id: str) -> Task | None: ...

    @abstractmethod
    def get_active_due(self, now_ts: str, window_seconds: int) -> list[Task]: ...

    @abstractmethod
    def save(self, task: Task) -> None: ...

    @abstractmethod
    def save_all(self, tasks: list[Task]) -> None: ...

    @abstractmethod
    def delete(self, task_id: str) -> None: ...


class IConfigRepository(ABC):
    """Application configuration persistence."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any: ...

    @abstractmethod
    def set(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def get_all_config(self) -> AppConfig: ...

    @abstractmethod
    def save_config(self, config: AppConfig) -> None: ...


# ─── Attachment Abstraction ───


class IAttachmentManager(ABC):
    """File import, dedup, cleanup for attached media."""

    @abstractmethod
    def import_file(self, src_path: str) -> str: ...

    @abstractmethod
    def get_attachments(self) -> list[AttachmentInfo]: ...

    @abstractmethod
    def get_stats(self, tasks: list[Task]) -> AttachmentStats: ...

    @abstractmethod
    def cleanup_unreferenced(self, tasks: list[Task]) -> int: ...
