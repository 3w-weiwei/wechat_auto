from __future__ import annotations

import json
import os

from engine.domain.models import Task


class FileStore:
    """Utility for reading/writing legacy JSON task files (backward compat)."""

    @staticmethod
    def load_tasks_from_json(filepath: str) -> list[Task]:
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        from engine.domain.models import ContentItem, ContentType

        tasks = []
        for item in data:
            contents = []
            for c in item.get("contents", []):
                try:
                    ct = ContentType(c.get("type", "text"))
                except ValueError:
                    ct = ContentType.TEXT
                contents.append(ContentItem(type=ct, value=c.get("value", "")))
            if not contents:
                legacy_type = item.get("type", "text")
                try:
                    ct = ContentType(legacy_type)
                except ValueError:
                    ct = ContentType.TEXT
                contents = [ContentItem(type=ct, value=item.get("content", ""))]

            import uuid

            tasks.append(Task(
                id=str(item.get("id", uuid.uuid4().hex[:12])),
                group=item.get("group", ""),
                datetime=item.get("datetime", ""),
                contents=contents,
                active=item.get("active", True),
            ))
        return tasks

    @staticmethod
    def save_tasks_to_json(tasks: list[Task], filepath: str) -> None:
        data = []
        for t in tasks:
            data.append({
                "id": t.id,
                "group": t.group,
                "datetime": t.datetime,
                "contents": [
                    {"type": c.type.value, "value": c.value} for c in t.contents
                ],
                "active": t.active,
            })
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    @staticmethod
    def migrate_json_to_sqlite(
        json_path: str, task_repo, config_repo
    ) -> int:
        """Migrate tasks from JSON file to SQLite. Returns count of migrated tasks."""
        tasks = FileStore.load_tasks_from_json(json_path)
        for task in tasks:
            task_repo.save(task)
        return len(tasks)
