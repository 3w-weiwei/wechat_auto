from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from engine.domain.interfaces import IConfigRepository, ITaskRepository
from engine.domain.models import (
    AppConfig,
    CalibrationData,
    ContentItem,
    ContentType,
    LearnedScale,
    Task,
    ThemeMode,
    WindowRect,
)


class SQLiteTaskRepository(ITaskRepository):
    """Task persistence backed by SQLite."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    group_name TEXT NOT NULL,
                    datetime TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS task_contents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    content_type TEXT NOT NULL,
                    content_value TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_active_datetime
                    ON tasks(active, datetime);
                CREATE INDEX IF NOT EXISTS idx_task_contents_task
                    ON task_contents(task_id);
            """)

    def get_all(self) -> list[Task]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY datetime DESC"
            ).fetchall()
            tasks = []
            for row in rows:
                contents = self._load_contents(conn, row["id"])
                tasks.append(Task(
                    id=row["id"],
                    group=row["group_name"],
                    datetime=row["datetime"],
                    active=bool(row["active"]),
                    contents=contents,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                ))
            return tasks

    def get_by_id(self, task_id: str) -> Task | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                return None
            contents = self._load_contents(conn, task_id)
            return Task(
                id=row["id"],
                group=row["group_name"],
                datetime=row["datetime"],
                active=bool(row["active"]),
                contents=contents,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def get_active_due(self, now_ts: str, window_seconds: int) -> list[Task]:
        """Find active tasks whose datetime is within the time window."""
        from datetime import datetime as dt
        from datetime import timedelta

        now = dt.fromisoformat(now_ts)
        window_end = now + timedelta(seconds=window_seconds)
        # Simple string comparison works for ISO format within a day
        window_str = window_end.strftime("%Y-%m-%d %H:%M")
        now_str = now.strftime("%Y-%m-%d %H:%M")

        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM tasks
                   WHERE active = 1
                   AND datetime >= ? AND datetime <= ?
                   ORDER BY datetime ASC""",
                (now_str, window_str),
            ).fetchall()
            tasks = []
            for row in rows:
                contents = self._load_contents(conn, row["id"])
                tasks.append(Task(
                    id=row["id"],
                    group=row["group_name"],
                    datetime=row["datetime"],
                    active=True,
                    contents=contents,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                ))
            return tasks

    def save(self, task: Task) -> None:
        now = datetime.now().isoformat()
        task.updated_at = now
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO tasks (id, group_name, datetime, active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (task.id, task.group, task.datetime, int(task.active), task.created_at, now),
            )
            conn.execute("DELETE FROM task_contents WHERE task_id = ?", (task.id,))
            for i, c in enumerate(task.contents):
                conn.execute(
                    "INSERT INTO task_contents (task_id, sort_order, content_type, content_value) VALUES (?, ?, ?, ?)",
                    (task.id, i, c.type.value, c.value),
                )

    def save_all(self, tasks: list[Task]) -> None:
        with self._connect():
            for task in tasks:
                self.save(task)

    def delete(self, task_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    @staticmethod
    def _load_contents(conn: sqlite3.Connection, task_id: str) -> list[ContentItem]:
        rows = conn.execute(
            "SELECT * FROM task_contents WHERE task_id = ? ORDER BY sort_order",
            (task_id,),
        ).fetchall()
        return [
            ContentItem(
                type=ContentType(r["content_type"]),
                value=r["content_value"],
                sort_order=r["sort_order"],
            )
            for r in rows
        ]


class SQLiteConfigRepository(IConfigRepository):
    """Application configuration backed by SQLite."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def get(self, key: str, default: object = None) -> object:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM config WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return default
            try:
                return json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                return row["value"]

    def set(self, key: str, value: object) -> None:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value, ensure_ascii=False), now),
            )

    def get_all_config(self) -> AppConfig:
        theme = self.get("template_theme", "light")
        templates = self.get("templates", {"light": {}, "dark": {}})
        learned = self.get("learned_scales", {})
        calib = self.get("calibration", None)
        template_source_dpi = self.get("template_source_dpi", 144)
        auto_wake = self.get("auto_wake", True)
        simulate_delay = self.get("simulate_delay", True)

        calibration = None
        if calib and isinstance(calib, dict):
            wr = calib.get("window_rect", [0, 0, 0, 0])
            calibration = CalibrationData(
                window_rect=WindowRect(
                    left=wr[0] if len(wr) > 0 else 0,
                    top=wr[1] if len(wr) > 1 else 0,
                    width=wr[2] if len(wr) > 2 else 0,
                    height=wr[3] if len(wr) > 3 else 0,
                ),
                dpi=calib.get("dpi", 96),
                screen_size=(
                    calib.get("screen_size", [1920, 1080])[0],
                    calib.get("screen_size", [1920, 1080])[1],
                ),
                timestamp=calib.get("timestamp", ""),
            )

        learned_scales: dict[str, LearnedScale] = {}
        if isinstance(learned, dict):
            for k, v in learned.items():
                if isinstance(v, dict):
                    learned_scales[k] = LearnedScale(
                        scale=v.get("scale", 1.0),
                        dpi=v.get("dpi", 96),
                        timestamp=v.get("time", ""),
                    )

        return AppConfig(
            template_theme=ThemeMode(theme) if theme in ("light", "dark") else ThemeMode.LIGHT,
            template_source_dpi=int(template_source_dpi) if template_source_dpi else 144,
            templates=templates if isinstance(templates, dict) else {},
            learned_scales=learned_scales,
            calibration=calibration,
            auto_wake=bool(auto_wake),
            simulate_delay=bool(simulate_delay),
        )

    def save_config(self, config: AppConfig) -> None:
        self.set("template_theme", config.template_theme.value)
        self.set("template_source_dpi", config.template_source_dpi)
        self.set("templates", config.templates)
        learned = {}
        for k, v in config.learned_scales.items():
            learned[k] = {"scale": v.scale, "dpi": v.dpi, "time": v.timestamp}
        self.set("learned_scales", learned)
        if config.calibration:
            self.set("calibration", {
                "window_rect": [
                    config.calibration.window_rect.left,
                    config.calibration.window_rect.top,
                    config.calibration.window_rect.width,
                    config.calibration.window_rect.height,
                ],
                "screen_size": list(config.calibration.screen_size),
                "dpi": config.calibration.dpi,
                "timestamp": config.calibration.timestamp,
            })
        self.set("auto_wake", config.auto_wake)
        self.set("simulate_delay", config.simulate_delay)
