from __future__ import annotations

from engine.domain.models import (
    AttachmentInfo,
    AttachmentStats,
    ContentItem,
    ContentType,
    Task,
)


def task_to_dict(task: Task) -> dict[str, object]:
    return {
        "id": task.id,
        "group": task.group,
        "datetime": task.datetime,
        "active": task.active,
        "contents": [content_item_to_dict(c) for c in task.contents],
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def task_from_dict(data: dict[str, object]) -> Task:
    contents = []
    for c in data.get("contents", []):
        if isinstance(c, dict):
            contents.append(content_item_from_dict(c))
    return Task(
        id=str(data.get("id", "")),
        group=str(data.get("group", "")),
        datetime=str(data.get("datetime", "")),
        active=bool(data.get("active", True)),
        contents=contents,
    )


def content_item_to_dict(item: ContentItem) -> dict[str, object]:
    return {
        "type": item.type.value,
        "value": item.value,
        "sort_order": item.sort_order,
        "category": item.category,
    }


def content_item_from_dict(data: dict[str, object]) -> ContentItem:
    ct = data.get("type", "text")
    if isinstance(ct, str):
        try:
            ct = ContentType(ct)
        except ValueError:
            ct = ContentType.TEXT
    return ContentItem(
        type=ct,
        value=str(data.get("value", "")),
        sort_order=int(data.get("sort_order", 0)),
        category=str(data.get("category", "")),
    )


def attachment_info_to_dict(info: AttachmentInfo) -> dict[str, object]:
    return {
        "name": info.name,
        "path": info.path,
        "type": info.type,
        "size": info.size,
    }


def attachment_stats_to_dict(stats: AttachmentStats) -> dict[str, object]:
    return {
        "total_count": stats.total_count,
        "total_size_mb": stats.total_size_mb,
        "referenced_count": stats.referenced_count,
        "unreferenced_count": stats.unreferenced_count,
    }
