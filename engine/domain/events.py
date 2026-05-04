from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


class DomainEvent:
    """Base marker class for all domain events.

    Subclasses must be @dataclass and should declare a timestamp field.
    """


# ─── Task Events ───


@dataclass
class TaskCreated(DomainEvent):
    task_id: str = ""
    task_group: str = ""
    task_count: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskUpdated(DomainEvent):
    task_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskDeleted(DomainEvent):
    task_id: str = ""
    task_group: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskToggled(DomainEvent):
    task_id: str = ""
    active: bool = True
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskStarted(DomainEvent):
    task_id: str = ""
    task_group: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskCompleted(DomainEvent):
    task_id: str = ""
    task_group: str = ""
    success: bool = True
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskProgress(DomainEvent):
    task_id: str = ""
    step: int = 0
    total: int = 0
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AllTasksCompleted(DomainEvent):
    total: int = 0
    success_count: int = 0
    fail_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ─── Engine Events ───


@dataclass
class EngineStatusChanged(DomainEvent):
    status: str = "ready"
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WindowCalibrated(DomainEvent):
    window_title: str = ""
    dpi: int = 0
    rect: tuple[int, int, int, int] | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TemplateMatched(DomainEvent):
    template: str = ""
    confidence: float = 0.0
    scale: float = 1.0
    position: tuple[int, int] = (0, 0)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ─── Attachment Events ───


@dataclass
class FileImported(DomainEvent):
    filename: str = ""
    destination: str = ""
    file_type: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AttachmentsCleaned(DomainEvent):
    removed_count: int = 0
    freed_mb: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ─── Log Event ───


@dataclass
class LogMessage(DomainEvent):
    level: str = "info"  # "info", "warn", "error", "success", "debug"
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
