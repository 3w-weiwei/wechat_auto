from __future__ import annotations

import random
import threading
import time
import traceback
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
        self._log(f"[队列] 开始执行 {len(tasks)} 个任务")
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
        self._log(f"[队列] ═══ 串行执行 {total} 个任务 ═══")
        success_count = 0
        fail_count = 0

        for idx, task in enumerate(tasks):
            if self._stop_event.is_set():
                self._log("[队列] 收到停止信号，中断执行")
                break

            tid = task.id
            contents = task.contents
            self._log(f"[队列] [{idx + 1}/{total}] ▶ 开始: {task.group} (内容 {len(contents)} 条)")

            try:
                # Step 1: Activate WeChat
                self._log(f"[队列] 步骤1: 激活微信窗口...")
                activated = False
                for attempt in range(3):
                    if self._platform.activate():
                        activated = True
                        self._log(f"[队列] ✅ 微信窗口已激活")
                        break
                    self._log(f"[队列] ⚠️ 激活失败，重试 {attempt + 1}/3...")
                    time.sleep(2)
                if not activated:
                    self._task_done(tid, False, f"未能激活微信窗口")
                    fail_count += 1
                    continue

                # Step 2: Calibrate
                self._log(f"[队列] 步骤2: 校准窗口位置...")
                time.sleep(0.5)  # let window settle
                if not self._platform.calibrate():
                    self._task_done(tid, False, f"窗口校准失败")
                    fail_count += 1
                    continue

                # Step 3: Navigate to chat
                self._log(f"[队列] 步骤3: 搜索并进入群聊 '{task.group}'")
                region = self._platform.get_wx_region()
                if region:
                    self._log(f"[队列] 微信窗口区域: ({region.left},{region.top}) {region.width}x{region.height}")
                nav_ok = self._platform.navigate_to_chat(task.group)
                if not nav_ok:
                    self._log(f"[队列] ⚠️ 导航可能不完整，继续发送...")
                time.sleep(0.8)

                # Step 4: Send each content item
                self._log(f"[队列] 步骤4: 发送 {len(contents)} 条内容")
                sent = 0
                for i, item in enumerate(contents):
                    if self._stop_event.is_set():
                        break
                    ct = item.type
                    cv = item.value
                    if not cv:
                        self._log(f"[队列]   #{i + 1} 跳过空内容")
                        continue

                    label = cv[:40] if ct == ContentType.TEXT else f"[{item.type.value}] {cv[-40:]}"
                    self._log(f"[队列]   #{i + 1}/{len(contents)} 发送: {label}")

                    ok = self._platform.send_content(ct, cv)
                    if ok:
                        sent += 1
                    else:
                        self._log(f"[队列]   ❌ 发送失败: {cv}")

                    if i < len(contents) - 1:
                        delay = 1.5 + random.uniform(0.3, 0.8)
                        self._log(f"[队列]   间隔 {delay:.1f}s...")
                        time.sleep(delay)

                msg = f"已发送 {sent}/{len(contents)} 条 → {task.group}"
                self._log(f"[队列] ✅ {msg}")
                self._task_done(tid, True, msg)
                success_count += 1

            except Exception:
                tb = traceback.format_exc()
                self._log(f"[队列] ❌ 异常:\n{tb}")
                self._task_done(tid, False, f"执行异常")
                fail_count += 1

            if idx < total - 1:
                delay = 2.0 + random.uniform(0.5, 1.5)
                self._log(f"[队列] 任务间隔 {delay:.1f}s...")
                time.sleep(delay)

        self._log(f"[队列] ═══ 完毕: 成功 {success_count}, 失败 {fail_count} ═══")
        if self._on_all_done:
            self._on_all_done()

    def _task_done(self, task_id: str, success: bool, message: str) -> None:
        if self._on_task_done:
            self._on_task_done(task_id, success, message)
