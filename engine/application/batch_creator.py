from __future__ import annotations

from engine.domain.models import BatchCreateSpec, BatchSlot, ContentItem


class BatchCreator:
    """Translates a batch spec (groups × slots) into concrete task parameters."""

    @staticmethod
    def expand(spec: BatchCreateSpec) -> list[dict[str, object]]:
        """Return list of {group, datetime, contents} dicts for task creation."""
        result: list[dict[str, object]] = []
        for group in spec.groups:
            for slot in spec.slots:
                # Filter out empty content items
                contents = [
                    c for c in slot.contents
                    if c.value.strip() != ""
                ]
                if not contents:
                    continue
                result.append({
                    "group": group,
                    "datetime": slot.datetime_str(),
                    "contents": contents,
                })
        return result

    @staticmethod
    def validate(spec: BatchCreateSpec) -> list[str]:
        """Validate batch spec, return list of error messages."""
        errors: list[str] = []
        if not spec.groups:
            errors.append("请至少添加一个目标群聊")
        if not spec.slots:
            errors.append("请至少添加一个时段")
        for i, slot in enumerate(spec.slots):
            if not slot.time:
                errors.append(f"时段 {i + 1} 缺少时间")
            has_content = any(c.value.strip() for c in slot.contents)
            if not has_content:
                errors.append(f"时段 {i + 1} 没有有效内容")
        return errors

    @staticmethod
    def count_tasks(spec: BatchCreateSpec) -> int:
        return len(spec.groups) * len(spec.slots)

    @staticmethod
    def create_slot(time: str = "12:00", date: str = "") -> BatchSlot:
        from datetime import datetime

        return BatchSlot(
            time=time,
            date=date or datetime.now().strftime("%Y-%m-%d"),
            contents=[],
        )

    @staticmethod
    def create_text_content(value: str = "") -> ContentItem:
        return ContentItem(type="text", value=value)  # type: ignore[arg-type]

    @staticmethod
    def create_media_content(media_type: str, value: str = "") -> ContentItem:
        from engine.domain.models import ContentType

        return ContentItem(type=ContentType(media_type), value=value)
