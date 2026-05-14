from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class ContentType(Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"


class EngineStatus(Enum):
    READY = "ready"
    ERROR = "error"
    NOT_FOUND = "not_found"


class ThemeMode(Enum):
    LIGHT = "light"
    DARK = "dark"


@dataclass
class ContentItem:
    """A single piece of content within a task (text, image, or video)."""

    type: ContentType
    value: str  # text content or file path
    sort_order: int = 0
    category: str = ""  # 注射美容 / 美容皮肤科 / 美容外科

    def is_text(self) -> bool:
        return self.type == ContentType.TEXT

    def is_media(self) -> bool:
        return self.type in (ContentType.IMAGE, ContentType.VIDEO)


@dataclass
class Task:
    """A scheduled messaging task targeting a WeChat group/contact."""

    id: str = field(default_factory=lambda: uuid4().hex[:12])
    group: str = ""  # target group or contact name
    datetime: str = ""  # "YYYY-MM-DD HH:MM"
    active: bool = True
    contents: list[ContentItem] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def has_media(self) -> bool:
        return any(c.is_media() for c in self.contents)

    def content_count(self) -> int:
        return len(self.contents)

    def is_expired(self) -> bool:
        return datetime.strptime(self.datetime, "%Y-%m-%d %H:%M") < datetime.now()


@dataclass
class WindowInfo:
    """Info about a located application window."""

    hwnd: int
    title: str
    rect: WindowRect


@dataclass
class WindowRect:
    """Window geometry in physical pixels."""

    left: int
    top: int
    width: int
    height: int


@dataclass
class TemplateMatch:
    """Result of a template matching operation."""

    found: bool
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.0
    scale: float = 1.0
    template_path: str = ""


@dataclass
class CalibrationData:
    """Stored calibration for the WeChat window."""

    window_rect: WindowRect
    dpi: int
    screen_size: tuple[int, int]
    timestamp: str


@dataclass
class AttachmentInfo:
    """Metadata for a stored attachment file."""

    name: str
    path: str
    type: str  # "image", "video", "other"
    size: int  # bytes


@dataclass
class AttachmentStats:
    """Aggregate stats for the attachments directory."""

    total_count: int
    total_size_mb: float
    referenced_count: int
    unreferenced_count: int


@dataclass
class TemplateConfig:
    """Configuration for a single visual template (e.g., search box)."""

    light: str = ""  # path to light-theme template image
    dark: str = ""  # path to dark-theme template image
    light_default: str = ""
    dark_default: str = ""


@dataclass
class LearnedScale:
    """Learned optimal scale for a template image at a given DPI."""

    scale: float
    dpi: int
    timestamp: str


@dataclass
class AppConfig:
    """Application configuration."""

    template_theme: ThemeMode = ThemeMode.LIGHT
    template_source_dpi: int = 144
    templates: dict[str, dict[str, str]] = field(default_factory=dict)
    learned_scales: dict[str, LearnedScale] = field(default_factory=dict)
    calibration: CalibrationData | None = None
    auto_wake: bool = True
    simulate_delay: bool = True


@dataclass
class BatchCreateSpec:
    """Specification for batch task creation."""

    groups: list[str] = field(default_factory=list)
    slots: list[BatchSlot] = field(default_factory=list)


@dataclass
class BatchSlot:
    """A single time slot in a batch creation form."""

    time: str = ""  # "HH:MM"
    date: str = ""  # "YYYY-MM-DD"
    contents: list[ContentItem] = field(default_factory=list)

    def datetime_str(self) -> str:
        return f"{self.date} {self.time}"
