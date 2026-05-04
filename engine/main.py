#!/usr/bin/env python3
"""智推助手 (ZhiTui Assistant) — Engine entry point."""

from __future__ import annotations

import asyncio
import contextlib
import os
import queue
import sys
from collections import deque
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.adapters.handlers import Handlers
from engine.adapters.ws_server import WebSocketServer
from engine.application.event_bus import EventBus
from engine.application.queue_runner import QueueRunner
from engine.application.scheduler import Scheduler
from engine.application.task_manager import TaskManager
from engine.infrastructure.attachment_manager import AttachmentManager
from engine.infrastructure.automation.vision import VisionEngine
from engine.infrastructure.automation.wechat_platform import WeChatPlatform
from engine.infrastructure.platform.windows import WindowsPlatformAdapter
from engine.infrastructure.storage.file_store import FileStore
from engine.infrastructure.storage.sqlite_repo import SQLiteConfigRepository, SQLiteTaskRepository


def _get_app_data_dir() -> str:
    if getattr(sys, "frozen", False):
        base = os.path.expanduser("~/Documents")
        return os.path.join(base, "WePush")
    return os.path.dirname(os.path.abspath(__file__))


class EngineApp:
    """Holds all engine state and provides the execution entry points."""

    def __init__(self) -> None:
        self.app_dir = _get_app_data_dir()
        os.makedirs(self.app_dir, exist_ok=True)

        db_path = os.path.join(self.app_dir, "wechat_auto.db")
        attachments_dir = os.path.join(self.app_dir, "attachments")
        templates_dir = os.path.join(self.app_dir, "templates")
        os.makedirs(attachments_dir, exist_ok=True)
        os.makedirs(templates_dir, exist_ok=True)

        self.platform = WindowsPlatformAdapter()
        self.task_repo = SQLiteTaskRepository(db_path)
        self.config_repo = SQLiteConfigRepository(db_path)
        self.attachment_manager = AttachmentManager(attachments_dir)

        # Migrate legacy
        tasks_json = os.path.join(self.app_dir, "tasks.json")
        if os.path.exists(tasks_json) and not self.task_repo.get_all():
            count = FileStore.migrate_json_to_sqlite(tasks_json, self.task_repo, self.config_repo)
            print(f"[Migrate] Imported {count} tasks from tasks.json")

        self.event_bus = EventBus()
        self.task_manager = TaskManager(self.task_repo, self.event_bus)

        config = self.config_repo.get_all_config()
        dpi = self.platform.get_system_dpi()
        self.vision = VisionEngine(dpi=dpi, template_source_dpi=config.template_source_dpi)
        if config.learned_scales:
            self.vision.set_learned_scales({
                k: {"scale": v.scale, "dpi": v.dpi, "time": v.timestamp}
                for k, v in config.learned_scales.items()
            })

        # Log broadcast queue (thread-safe)
        self._log_queue: queue.Queue[dict[str, object]] = queue.Queue()
        self._ws_server: WebSocketServer | None = None

        # Task execution state
        self._pending_tasks: deque[str] = deque()
        self._queue_runner: QueueRunner | None = None
        self._scheduler: Scheduler | None = None

        # WeChat platform (needs _log defined first)
        self.wechat = WeChatPlatform(self.platform, self.vision, self._log)

        self._log("[系统] 智推助手 v4.0 启动中...")
        self._log(f"[系统] 数据目录: {self.app_dir}")
        self._log(f"[系统] DPI: {dpi} ({self.platform.get_dpi_scale():.2f}x)")
        self._log(f"[系统] 当前主题: {config.template_theme.value}")
        self._log(f"[系统] 已加载 {self.task_repo.get_all().__len__()} 个任务")

    def _log(self, msg: str, level: str = "info") -> None:
        ts = datetime.now().strftime('%H:%M:%S')
        formatted = f"[{ts}] {msg}"
        print(formatted, flush=True)
        self._log_queue.put({
            "level": level, "message": msg,
            "timestamp": datetime.now().isoformat(),
        })

    def set_ws_server(self, ws: WebSocketServer) -> None:
        self._ws_server = ws

    # ─── Task execution (called from WebSocket handler thread) ───

    def enqueue_manual(self, task_ids: list[str]) -> None:
        """Enqueue tasks for immediate execution (called from WS handler)."""
        self._log(f"[系统] 收到手动执行请求: {task_ids}")
        for tid in task_ids:
            if tid not in self._pending_tasks:
                self._pending_tasks.append(tid)
        self._try_start_batch()

    def enqueue_scheduled(self, tasks: list) -> None:
        """Enqueue due tasks from scheduler."""
        self._log(f"[调度] 到期 {len(tasks)} 个任务")
        for t in tasks:
            if t.id not in self._pending_tasks:
                self._pending_tasks.append(t.id)
        self._try_start_batch()

    def _try_start_batch(self) -> None:
        """Start executing the next batch if idle."""
        print(f"DEBUG _try_start_batch: pending={len(self._pending_tasks)} qr_active={self._queue_runner is not None}", file=sys.stderr, flush=True)

        if not self._pending_tasks:
            print("DEBUG: no pending tasks, returning", file=sys.stderr, flush=True)
            return
        if self._queue_runner is not None:
            print("DEBUG: queue_runner already active, returning", file=sys.stderr, flush=True)
            return

        batch_ids = []
        while self._pending_tasks:
            batch_ids.append(self._pending_tasks.popleft())

        self._log(f"[系统] 准备执行 {len(batch_ids)} 个任务: {batch_ids}")
        tasks = [self.task_manager.get(tid) for tid in batch_ids]
        tasks = [t for t in tasks if t is not None]

        self._log(f"[系统] 加载了 {len(tasks)} 个有效任务")
        if not tasks:
            self._log("[系统] ⚠️ 没有有效任务", "warn")
            return

        for t in tasks:
            self._log(f"[系统]   id={t.id[:8]}.. 群={t.group} 内容={len(t.contents)}条 时间={t.datetime}")

        def on_done(tid: str, ok: bool, msg: str) -> None:
            if ok:
                self.task_manager.set_active(tid, False)
            if self._scheduler:
                self._scheduler.remove_fired(tid)
            self._log(f"[队列] {tid[:8]}.. {'✅' if ok else '❌'} {msg}",
                      "success" if ok else "error")

        def on_all() -> None:
            self._log("[队列] 全部任务执行完毕")
            self._queue_runner = None
            self._try_start_batch()

        self._queue_runner = QueueRunner(self.wechat, self._log, on_done, on_all)
        self._queue_runner.run(tasks)
        self._log(f"[系统] 队列已启动，{len(tasks)} 个任务开始执行")

    # ─── Async helpers ───

    async def broadcast_logs(self) -> None:
        while True:
            try:
                while not self._log_queue.empty():
                    entry = self._log_queue.get_nowait()
                    if self._ws_server:
                        await self._ws_server.broadcast("log", entry)
            except Exception:
                pass
            await asyncio.sleep(0.1)

    async def monitor_wechat(self) -> None:
        while True:
            try:
                info = self.wechat.locate_app()
                if info is None:
                    status = "not_found"
                elif self.platform.is_window_minimized(info.hwnd):
                    status = "minimized"
                else:
                    status = "ready"
                if self._ws_server:
                    await self._ws_server.broadcast("engine.status", {"status": status})
            except Exception:
                pass
            await asyncio.sleep(3.0)

    def start_scheduler(self) -> None:
        self._scheduler = Scheduler(self.task_repo, self.enqueue_scheduled, interval_seconds=5.0)
        self._scheduler.start()

    def stop(self) -> None:
        if self._scheduler:
            self._scheduler.stop()
        if self._queue_runner:
            self._queue_runner.stop()


def main() -> None:
    app = EngineApp()

    handlers = Handlers(
        task_manager=app.task_manager,
        task_repo=app.task_repo,
        config_repo=app.config_repo,
        attachment_manager=app.attachment_manager,
        platform=app.platform,
        wechat=app.wechat,
        on_run_now=app.enqueue_manual,
        on_log=app._log,
    )

    ws_server = WebSocketServer(handlers, host="127.0.0.1", port=9876, on_log=app._log)
    app.set_ws_server(ws_server)

    async def run() -> None:
        await ws_server.start()
        app.start_scheduler()
        asyncio.create_task(app.monitor_wechat())
        asyncio.create_task(app.broadcast_logs())
        app._log("[系统] 引擎启动完成，等待指令...")
        stop_event = asyncio.Event()
        with contextlib.suppress(asyncio.CancelledError):
            await stop_event.wait()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        app._log("[系统] 正在关闭...")
    finally:
        app.stop()


if __name__ == "__main__":
    main()
