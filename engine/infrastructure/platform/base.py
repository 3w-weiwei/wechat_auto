from __future__ import annotations

from abc import ABC, abstractmethod

from engine.domain.models import WindowInfo, WindowRect


class PlatformAdapter(ABC):
    """OS-level operations — DPI, window management, screenshots, file system."""

    @abstractmethod
    def get_system_dpi(self) -> int: ...

    @abstractmethod
    def get_dpi_scale(self) -> float: ...

    @abstractmethod
    def find_window_by_title(self, title: str) -> WindowInfo | None: ...

    @abstractmethod
    def get_window_rect(self, hwnd: int) -> WindowRect: ...

    @abstractmethod
    def activate_window(self, hwnd: int) -> bool: ...

    @abstractmethod
    def is_window_visible(self, hwnd: int) -> bool: ...

    @abstractmethod
    def is_window_minimized(self, hwnd: int) -> bool: ...

    @abstractmethod
    def restore_window(self, hwnd: int) -> bool: ...

    @abstractmethod
    def get_screenshot(self, region: WindowRect | None = None) -> object | None: ...

    @abstractmethod
    def open_directory(self, path: str) -> None: ...

    @abstractmethod
    def get_app_data_dir(self) -> str: ...

    @abstractmethod
    def get_original_dir(self) -> str: ...
