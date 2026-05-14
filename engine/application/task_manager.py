from __future__ import annotations

from datetime import datetime

from engine.domain.events import TaskCreated, TaskDeleted, TaskToggled, TaskUpdated
from engine.domain.interfaces import IEventBus, ITaskRepository
from engine.domain.models import ContentItem, Task


class TaskManager:
    """Orchestrates task CRUD operations with event publishing."""

    def __init__(self, repo: ITaskRepository, event_bus: IEventBus | None = None) -> None:
        self._repo = repo
        self._event_bus = event_bus

    def list_all(self) -> list[Task]:
        return self._repo.get_all()

    def get(self, task_id: str) -> Task | None:
        return self._repo.get_by_id(task_id)

    def create(
        self, group: str, datetime_str: str, contents: list[ContentItem], active: bool = True,
    ) -> Task:
        now = datetime.now().isoformat()
        task = Task(
            group=group,
            datetime=datetime_str,
            active=active,
            contents=contents,
            created_at=now,
            updated_at=now,
        )
        self._repo.save(task)
        if self._event_bus:
            self._event_bus.publish(TaskCreated(
                task_id=task.id, task_group=task.group, task_count=1
            ))
        return task

    def create_batch(
        self, groups: list[str], datetime_strs: list[str], contents: list[ContentItem]
    ) -> list[Task]:
        """Create tasks for each group × datetime combination."""
        tasks = []
        for group in groups:
            for dt in datetime_strs:
                task = self.create(group, dt, contents)
                tasks.append(task)
        if self._event_bus:
            self._event_bus.publish(TaskCreated(
                task_id="batch", task_group=f"{len(groups)} groups", task_count=len(tasks)
            ))
        return tasks

    def update(self, task: Task) -> None:
        self._repo.save(task)
        if self._event_bus:
            self._event_bus.publish(TaskUpdated(task_id=task.id))

    def delete(self, task_id: str) -> None:
        task = self._repo.get_by_id(task_id)
        if task:
            self._repo.delete(task_id)
            if self._event_bus:
                self._event_bus.publish(TaskDeleted(
                    task_id=task_id, task_group=task.group
                ))

    def toggle(self, task_id: str) -> bool | None:
        """Toggle active state. Returns new state, or None if not found."""
        task = self._repo.get_by_id(task_id)
        if task is None:
            return None
        task.active = not task.active
        self._repo.save(task)
        if self._event_bus:
            self._event_bus.publish(TaskToggled(task_id=task_id, active=task.active))
        return task.active

    def set_active(self, task_id: str, active: bool) -> bool:
        task = self._repo.get_by_id(task_id)
        if task is None:
            return False
        task.active = active
        self._repo.save(task)
        return True
