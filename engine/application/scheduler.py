from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime, timedelta

from engine.domain.interfaces import ITaskRepository
from engine.domain.models import Task


class Scheduler:
    """Periodic scheduler that checks for due tasks and invokes a callback."""

    def __init__(
        self,
        task_repo: ITaskRepository,
        on_tasks_due: Callable[[list[Task]], None],
        interval_seconds: float = 5.0,
        window_seconds: int = 90,
    ) -> None:
        self._repo = task_repo
        self._on_tasks_due = on_tasks_due
        self._interval = interval_seconds
        self._window = window_seconds
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._fired_ids: set[str] = set()

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def remove_fired(self, task_id: str) -> None:
        self._fired_ids.discard(task_id)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                # Allow tasks within -10s to +window_seconds of now
                start = now - timedelta(seconds=10)
                end = now + timedelta(seconds=self._window)
                now_str = start.isoformat()
                window = int((end - start).total_seconds())

                due = [
                    t for t in self._repo.get_active_due(now_str, window)
                    if t.id not in self._fired_ids
                ]
                if due:
                    for t in due:
                        self._fired_ids.add(t.id)
                    self._on_tasks_due(due)
            except Exception:
                pass

            self._stop_event.wait(self._interval)
