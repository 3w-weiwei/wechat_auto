#!/usr/bin/env python3
"""智推助手 (ZhiTui Assistant) — Engine entry point.

Starts the WebSocket JSON-RPC server that the React UI connects to.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import deque
from datetime import datetime

# Ensure engine package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import contextlib

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


def main() -> None:
    app_dir = _get_app_data_dir()
    os.makedirs(app_dir, exist_ok=True)

    db_path = os.path.join(app_dir, "wechat_auto.db")
    attachments_dir = os.path.join(app_dir, "attachments")
    templates_dir = os.path.join(app_dir, "templates")
    os.makedirs(attachments_dir, exist_ok=True)
    os.makedirs(templates_dir, exist_ok=True)

    # Infrastructure
    platform = WindowsPlatformAdapter()
    task_repo = SQLiteTaskRepository(db_path)
    config_repo = SQLiteConfigRepository(db_path)
    attachment_manager = AttachmentManager(attachments_dir)

    # Migrate legacy JSON -> SQLite on first run
    tasks_json = os.path.join(app_dir, "tasks.json")
    if os.path.exists(tasks_json) and not task_repo.get_all():
        count = FileStore.migrate_json_to_sqlite(tasks_json, task_repo, config_repo)
        print(f"[Migrate] Imported {count} tasks from tasks.json")

    # Domain services
    event_bus = EventBus()
    task_manager = TaskManager(task_repo, event_bus)

    # Vision + WeChat
    config = config_repo.get_all_config()
    dpi = platform.get_system_dpi()
    vision = VisionEngine(
        dpi=dpi,
        template_source_dpi=config.template_source_dpi,
    )
    if config.learned_scales:
        vision.set_learned_scales({
            k: {"scale": v.scale, "dpi": v.dpi, "time": v.timestamp}
            for k, v in config.learned_scales.items()
        })

    log_queue: deque[str] = deque(maxlen=500)
    def on_log(msg: str) -> None:
        log_queue.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        print(msg)

    wechat = WeChatPlatform(platform, vision, on_log)

    # Queue Runner
    pending_tasks: deque[str] = deque()
    queue_runner: QueueRunner | None = None

    def on_task_done(task_id: str, success: bool, message: str) -> None:
        if success:
            task_manager.set_active(task_id, False)
        scheduler.remove_fired(task_id)
        on_log(f"[Queue] Task {task_id}: {'OK' if success else 'FAIL'} - {message}")

    def on_all_done() -> None:
        nonlocal queue_runner
        on_log("[Queue] All tasks complete")
        queue_runner = None
        # Start next batch if pending
        _start_next_batch()

    def _start_next_batch() -> None:
        nonlocal queue_runner
        if pending_tasks and queue_runner is None:
            batch_ids = []
            while pending_tasks:
                batch_ids.append(pending_tasks.popleft())
            tasks = [task_manager.get(tid) for tid in batch_ids]
            tasks = [t for t in tasks if t is not None]
            if tasks:
                queue_runner = QueueRunner(wechat, on_log, on_task_done, on_all_done)
                queue_runner.run(tasks)

    def on_run_now(task_ids: list[str]) -> None:
        for tid in task_ids:
            if tid not in pending_tasks:
                pending_tasks.append(tid)
        _start_next_batch()

    def on_tasks_due(tasks: list) -> None:
        for t in tasks:
            if t.id not in pending_tasks:
                pending_tasks.append(t.id)
        _start_next_batch()

    # Scheduler
    scheduler = Scheduler(task_repo, on_tasks_due, interval_seconds=5.0)

    # WeChat state monitor
    async def wx_monitor() -> None:
        while True:
            try:
                info = wechat.locate_app()
                if info is None:
                    status = "not_found"
                elif platform.is_window_minimized(info.hwnd):
                    status = "minimized"
                else:
                    status = "ready"
                await ws_server.broadcast("engine.status", {"status": status})
            except Exception:
                pass
            await asyncio.sleep(3.0)

    # Build handlers + server
    handlers = Handlers(
        task_manager=task_manager,
        task_repo=task_repo,
        config_repo=config_repo,
        attachment_manager=attachment_manager,
        platform=platform,
        wechat=wechat,
        on_run_now=on_run_now,
        on_log=on_log,
    )

    ws_server = WebSocketServer(handlers, on_log=on_log)

    # Async event loop
    async def run() -> None:
        await ws_server.start()
        scheduler.start()
        asyncio.create_task(wx_monitor())
        on_log("[Engine] ZhiTui Assistant started")
        # Keep running
        stop_event = asyncio.Event()
        with contextlib.suppress(asyncio.CancelledError):
            await stop_event.wait()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        on_log("[Engine] Shutting down...")
    finally:
        scheduler.stop()
        if queue_runner:
            queue_runner.stop()


if __name__ == "__main__":
    main()
