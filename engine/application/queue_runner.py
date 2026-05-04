from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable

from engine.domain.models import ContentType, Task
from engine.infrastructure.automation.wechat_platform import WeChatPlatform


class QueueRunner:
    """Executes tasks sequentially in a background thread."""

    def __init__(
        self,
        platform: WeChatPlatform,
        on_log: Callable[[str], None] | None = None,
        on_task_done: Callable[[str, bool, str], None] | None = None,
        on_all_done: Callable[[], None] | None = None,
    ) -> None:
        self._platform = platform
        self._on_log = on_log
        self._on_task_done = on_task_done
        self._on_all_done = on_all_done
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def run(self, tasks: list[Task]) -> None:
        """Start executing tasks in a background thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._execute, args=(tasks,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _log(self, msg: str) -> None:
        if self._on_log:
            self._on_log(msg)

    def _execute(self, tasks: list[Task]) -> None:
        total = len(tasks)
        self._log(f"[Queue] === Serial execution of {total} tasks ===")
        success_count = 0
        fail_count = 0

        for idx, task in enumerate(tasks):
            if self._stop_event.is_set():
                break

            tid = task.id
            contents = task.contents
            self._log(f"[Queue] [{idx + 1}/{total}] > {task.group}")

            try:
                # Activate WeChat (retry up to 3 times)
                activated = False
                for attempt in range(3):
                    if self._platform.activate():
                        activated = True
                        break
                    self._log(f"[Retry] {attempt + 1}/3...")
                    time.sleep(2)
                if not activated:
                    self._task_done(tid, False, f"WeChat not found -> {task.group}")
                    fail_count += 1
                    continue

                # Calibrate window position
                if not self._platform.calibrate():
                    self._task_done(tid, False, f"Calibration failed -> {task.group}")
                    fail_count += 1
                    continue

                # Navigate to chat
                self._platform.navigate_to_chat(task.group)
                time.sleep(0.6)

                # Send each content item
                sent = 0
                for i, item in enumerate(contents):
                    if self._stop_event.is_set():
                        break
                    ct = item.type
                    cv = item.value
                    if not cv:
                        continue

                    label = cv[:30] if ct == ContentType.TEXT else f"[{item.type.value}] {cv[-40:]}"
                    self._log(f"[Send] #{i + 1}/{len(contents)} {label}")

                    if self._platform.send_content(ct, cv):
                        sent += 1
                    else:
                        self._log(f"[Error] Failed to send: {cv}")

                    if i < len(contents) - 1:
                        time.sleep(1.5 + random.uniform(0.3, 0.8))

                self._task_done(tid, True, f"Sent {sent}/{len(contents)} -> {task.group}")
                success_count += 1

            except Exception as e:
                self._task_done(tid, False, f"{e} -> {task.group}")
                fail_count += 1

            if idx < total - 1:
                time.sleep(2.0 + random.uniform(0.5, 1.5))

        self._log(f"[Queue] === Done: {success_count} OK, {fail_count} FAIL ===")
        if self._on_all_done:
            self._on_all_done()

    def _task_done(self, task_id: str, success: bool, message: str) -> None:
        if self._on_task_done:
            self._on_task_done(task_id, success, message)
