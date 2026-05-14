from __future__ import annotations

import hashlib
import os
import shutil
import uuid

from engine.domain.interfaces import IAttachmentManager
from engine.domain.models import AttachmentInfo, AttachmentStats, Task

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"}


class AttachmentManager(IAttachmentManager):
    """File import, dedup via MD5 hash prefix, cleanup of unreferenced files."""

    def __init__(self, attachments_dir: str) -> None:
        self._dir = attachments_dir
        os.makedirs(self._dir, exist_ok=True)

    def import_file(self, src_path: str) -> str | None:
        if not src_path or not os.path.exists(src_path):
            return None
        file_hash = self._file_hash(src_path)
        ext = os.path.splitext(src_path)[1].lower()
        orig_name = os.path.splitext(os.path.basename(src_path))[0]
        safe_name = "".join(c for c in orig_name if c.isalnum() or c in "._- ")[:30]
        dest_name = f"{file_hash}_{safe_name}{ext}"
        dest_path = os.path.join(self._dir, dest_name)
        if os.path.exists(dest_path):
            return os.path.abspath(dest_path)
        try:
            shutil.copy2(src_path, dest_path)
            return os.path.abspath(dest_path)
        except OSError:
            return None

    def import_from_data(self, filename: str, data_b64: str) -> str | None:
        """Import file from base64-encoded data. Returns absolute path on success."""
        import base64

        try:
            raw = base64.b64decode(data_b64)
        except Exception:
            return None
        if not raw:
            return None
        h = hashlib.md5(raw).hexdigest()[:8]
        ext = os.path.splitext(filename)[1].lower()
        orig_name = os.path.splitext(os.path.basename(filename))[0]
        safe_name = "".join(c for c in orig_name if c.isalnum() or c in "._- ")[:30]
        dest_name = f"{h}_{safe_name}{ext}"
        dest_path = os.path.join(self._dir, dest_name)
        if os.path.exists(dest_path):
            return os.path.abspath(dest_path)
        try:
            with open(dest_path, "wb") as f:
                f.write(raw)
            return os.path.abspath(dest_path)
        except OSError:
            return None

    def get_attachments(self) -> list[AttachmentInfo]:
        if not os.path.exists(self._dir):
            return []
        files: list[AttachmentInfo] = []
        for f in os.listdir(self._dir):
            fp = os.path.join(self._dir, f)
            if os.path.isfile(fp):
                ext = os.path.splitext(f)[1].lower()
                ftype = (
                    "image" if ext in IMAGE_EXTS else "video" if ext in VIDEO_EXTS else "other"
                )
                size = os.path.getsize(fp)
                files.append(AttachmentInfo(name=f, path=os.path.abspath(fp), type=ftype, size=size))
        return sorted(files, key=lambda x: x.name)

    def get_stats(self, tasks: list[Task]) -> AttachmentStats:
        all_files = self.get_attachments()
        referenced = self._get_referenced_paths(tasks)
        total_bytes = sum(f.size for f in all_files)
        return AttachmentStats(
            total_count=len(all_files),
            total_size_mb=round(total_bytes / 1024 / 1024, 2),
            referenced_count=sum(1 for f in all_files if f.path in referenced),
            unreferenced_count=sum(1 for f in all_files if f.path not in referenced),
        )

    def cleanup_unreferenced(self, tasks: list[Task]) -> int:
        referenced = self._get_referenced_paths(tasks)
        removed = 0
        for f in self.get_attachments():
            if f.path not in referenced:
                try:
                    os.remove(f.path)
                    removed += 1
                except OSError:
                    pass
        return removed

    @staticmethod
    def detect_file_type(filepath: str) -> str | None:
        ext = os.path.splitext(filepath)[1].lower()
        if ext in IMAGE_EXTS:
            return "image"
        if ext in VIDEO_EXTS:
            return "video"
        return None

    @staticmethod
    def _file_hash(filepath: str, length: int = 8) -> str:
        h = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()[:length]
        except OSError:
            return uuid.uuid4().hex[:length]

    @staticmethod
    def _get_referenced_paths(tasks: list[Task]) -> set[str]:
        paths: set[str] = set()
        for t in tasks:
            for c in t.contents:
                if c.is_media() and c.value:
                    paths.add(os.path.abspath(c.value))
        return paths
