from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from engine.application.task_manager import TaskManager
from engine.domain.models import ContentItem, ContentType
from engine.infrastructure.attachment_manager import AttachmentManager
from engine.infrastructure.automation.wechat_platform import WeChatPlatform
from engine.infrastructure.platform.base import PlatformAdapter
from engine.infrastructure.storage.sqlite_repo import SQLiteConfigRepository, SQLiteTaskRepository


class Handlers:
    """JSON-RPC method handlers. Each method takes params dict and returns result."""

    def __init__(
        self,
        task_manager: TaskManager,
        task_repo: SQLiteTaskRepository,
        config_repo: SQLiteConfigRepository,
        attachment_manager: AttachmentManager,
        platform: PlatformAdapter,
        wechat: WeChatPlatform,
        on_run_now: Callable[[list[str]], None],
        on_log: Callable[[str], None],
    ) -> None:
        self.task_manager = task_manager
        self.task_repo = task_repo
        self.config_repo = config_repo
        self.attachment_manager = attachment_manager
        self.platform = platform
        self.wechat = wechat
        self._on_run_now = on_run_now
        self._on_log = on_log

    def dispatch(self, method: str, params: dict[str, object]) -> object:
        handler = getattr(self, f"_handle_{method.replace('.', '_')}", None)
        if handler is None:
            return {"error": {"code": -32601, "message": f"Unknown method: {method}"}}
        try:
            import sys, traceback
            print(f"[DISPATCH] method={method} params={params}", file=sys.stderr, flush=True)
            result = handler(params)
            print(f"[DISPATCH] method={method} result={result}", file=sys.stderr, flush=True)
            return result
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            return {"error": {"code": -32000, "message": str(e)}}

    # ─── Task Methods ───

    def _handle_task_list(self, _params: dict[str, object]) -> object:
        from engine.adapters.serializers import task_to_dict
        tasks = self.task_manager.list_all()
        return {"tasks": [task_to_dict(t) for t in tasks]}

    def _handle_task_get(self, params: dict[str, object]) -> object:
        from engine.adapters.serializers import task_to_dict
        task = self.task_manager.get(str(params.get("id", "")))
        if task is None:
            return {"error": {"code": -32000, "message": "Task not found"}}
        return {"task": task_to_dict(task)}

    def _handle_task_create(self, params: dict[str, object]) -> object:
        from engine.adapters.serializers import content_item_from_dict, task_to_dict

        groups = params.get("groups", [])
        slots = params.get("slots", [])
        if isinstance(groups, str):
            groups = [g.strip() for g in groups.replace("，", ",").split(",") if g.strip()]
        if not groups:
            return {"error": {"code": -32602, "message": "groups required"}}

        new_tasks = []
        now = datetime.now().isoformat()

        # For each group × each slot, create a task with that slot's contents
        for group_name in groups:
            if isinstance(slots, list) and len(slots) > 0:
                for slot in slots:
                    if not isinstance(slot, dict):
                        continue
                    date = str(slot.get("date", datetime.now().strftime("%Y-%m-%d")))
                    time_str = str(slot.get("time", "12:00"))
                    dt = f"{date} {time_str}"

                    # Extract contents from this specific slot
                    contents = []
                    slot_contents = slot.get("contents", [])
                    if isinstance(slot_contents, list):
                        for c in slot_contents:
                            if isinstance(c, dict) and c.get("value", "").strip():
                                contents.append(content_item_from_dict(c))

                    if contents:
                        task = self.task_manager.create(str(group_name), dt, contents)
                        new_tasks.append(task)
            else:
                # No slots: use top-level contents + datetime
                dt = str(params.get("datetime", datetime.now().strftime("%Y-%m-%d %H:%M")))
                contents = []
                contents_raw = params.get("contents", [])
                if isinstance(contents_raw, list):
                    for c in contents_raw:
                        if isinstance(c, dict) and c.get("value", "").strip():
                            contents.append(content_item_from_dict(c))
                if contents:
                    task = self.task_manager.create(str(group_name), dt, contents)
                    new_tasks.append(task)

        if not new_tasks:
            return {"error": {"code": -32602, "message": "No valid tasks to create"}}

        self._on_log(f"[Task] 批量创建 {len(new_tasks)} 个任务")
        return {"tasks": [task_to_dict(t) for t in new_tasks]}

    def _handle_task_update(self, params: dict[str, object]) -> object:
        from engine.adapters.serializers import content_item_from_dict, task_to_dict

        task_id = str(params.get("id", ""))
        task = self.task_manager.get(task_id)
        if task is None:
            return {"error": {"code": -32000, "message": "Task not found"}}

        if "group" in params:
            task.group = str(params["group"])
        if "datetime" in params:
            task.datetime = str(params["datetime"])
        if "active" in params:
            task.active = bool(params["active"])
        if "contents" in params:
            contents_raw = params["contents"]
            if isinstance(contents_raw, list):
                task.contents = [
                    content_item_from_dict(c) if isinstance(c, dict) else ContentItem()
                    for c in contents_raw
                ]

        self.task_manager.update(task)
        return {"task": task_to_dict(task)}

    def _handle_task_delete(self, params: dict[str, object]) -> object:
        task_id = str(params.get("id", ""))
        self.task_manager.delete(task_id)
        return {"deleted": True}

    def _handle_task_toggle(self, params: dict[str, object]) -> object:
        task_id = str(params.get("id", ""))
        state = self.task_manager.toggle(task_id)
        if state is None:
            return {"error": {"code": -32000, "message": "Task not found"}}
        return {"task_id": task_id, "active": state}

    def _handle_task_run_now(self, params: dict[str, object]) -> object:
        task_id = str(params.get("id", ""))
        self._on_run_now([task_id])
        return {"queued": True}

    # ─── Config Methods ───

    def _handle_config_get(self, params: dict[str, object]) -> object:
        key = str(params.get("key", ""))
        if key:
            return {"value": self.config_repo.get(key)}
        return {"config": self.config_repo.get_all_config()}

    def _handle_config_set(self, params: dict[str, object]) -> object:
        key = str(params.get("key", ""))
        value = params.get("value")
        self.config_repo.set(key, value)
        return {"ok": True}

    # ─── Engine Methods ───

    def _handle_engine_calibrate(self, _params: dict[str, object]) -> object:
        ok = self.wechat.calibrate()
        if ok:
            region = self.wechat.get_wx_region()
            dpi = self.platform.get_system_dpi()
            screen_size = self.platform.get_screen_size()
            config = self.config_repo.get_all_config()
            from engine.domain.models import CalibrationData
            if region:
                config.calibration = CalibrationData(
                    window_rect=region,
                    dpi=dpi,
                    screen_size=screen_size,
                    timestamp=datetime.now().isoformat(),
                )
            self.config_repo.set("calibration", {
                "window_rect": [region.left, region.top, region.width, region.height] if region else [0, 0, 0, 0],
                "screen_size": list(screen_size),
                "dpi": dpi,
                "timestamp": datetime.now().isoformat(),
            })
            return {"status": "ready", "dpi": dpi}
        return {"status": "error", "message": "WeChat window not found"}

    def _handle_engine_status(self, _params: dict[str, object]) -> object:
        info = self.wechat.locate_app()
        if info is None:
            return {"status": "not_found"}
        if self.platform.is_window_minimized(info.hwnd):
            return {"status": "minimized"}
        return {"status": "ready"}

    # ─── Attachment Methods ───

    def _handle_attachment_list(self, _params: dict[str, object]) -> object:
        from engine.adapters.serializers import attachment_info_to_dict
        files = self.attachment_manager.get_attachments()
        return {"attachments": [attachment_info_to_dict(f) for f in files]}

    def _handle_attachment_stats(self, _params: dict[str, object]) -> object:
        from engine.adapters.serializers import attachment_stats_to_dict
        tasks = self.task_manager.list_all()
        stats = self.attachment_manager.get_stats(tasks)
        return {"stats": attachment_stats_to_dict(stats)}

    def _handle_attachment_cleanup(self, _params: dict[str, object]) -> object:
        tasks = self.task_manager.list_all()
        removed = self.attachment_manager.cleanup_unreferenced(tasks)
        self._on_log(f"[Attach] Cleaned {removed} unreferenced files")
        return {"removed": removed}

    def _handle_attachment_import(self, params: dict[str, object]) -> object:
        # Support both local file path and base64 data import
        data_b64 = str(params.get("data", ""))
        filename = str(params.get("filename", ""))
        if data_b64 and filename:
            dest = self.attachment_manager.import_from_data(filename, data_b64)
        else:
            src = str(params.get("path", ""))
            dest = self.attachment_manager.import_file(src)
        if dest is None:
            return {"error": {"code": -32000, "message": "Import failed"}}
        return {"path": dest}

    def _handle_attachment_open_dir(self, _params: dict[str, object]) -> object:
        self.platform.open_directory(self.attachment_manager._dir)
        return {"ok": True}

    # ─── Template Methods ───

    def _handle_template_list(self, _params: dict[str, object]) -> object:
        config = self.config_repo.get_all_config()
        return {
            "theme": config.template_theme.value,
            "templates": config.templates,
        }

    def _handle_template_set_theme(self, params: dict[str, object]) -> object:
        theme = str(params.get("theme", "light"))
        config = self.config_repo.get_all_config()
        from engine.domain.models import ThemeMode
        config.template_theme = ThemeMode(theme) if theme in ("light", "dark") else ThemeMode.LIGHT
        self.config_repo.save_config(config)
        # Also save to config.json for template path resolution
        import json, os
        app_dir = self.platform.get_app_data_dir()
        config_json = os.path.join(app_dir, "config.json")
        try:
            json_config = {}
            if os.path.exists(config_json):
                with open(config_json, encoding="utf-8") as f:
                    json_config = json.load(f)
            json_config["template_theme"] = theme
            with open(config_json, "w", encoding="utf-8") as f:
                json.dump(json_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        # Also update WeChatPlatform directly
        self.wechat._current_theme = theme
        self._on_log(f"[Config] Theme switched to {theme}")
        return {"theme": theme}

    def _handle_template_upload(self, params: dict[str, object]) -> object:
        """Save a custom template image from base64 data."""
        import base64
        import os

        key = str(params.get("key", ""))
        theme = str(params.get("theme", "light"))
        filename = str(params.get("filename", f"{key}_{theme}.png"))
        data_url = str(params.get("data", ""))

        if not key or not data_url:
            return {"error": {"code": -32602, "message": "key and data required"}}

        # Decode base64 data URL
        if "," in data_url:
            data_url = data_url.split(",", 1)[1]
        try:
            file_data = base64.b64decode(data_url)
        except Exception:
            return {"error": {"code": -32602, "message": "Invalid base64 data"}}

        # Save to engine/templates/
        engine_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        templates_dir = os.path.join(engine_dir, "templates")
        os.makedirs(templates_dir, exist_ok=True)
        dest_name = f"{key}_{theme}.png"
        dest_path = os.path.join(templates_dir, dest_name)
        with open(dest_path, "wb") as f:
            f.write(file_data)

        # Update config
        config = self.config_repo.get_all_config()
        if theme not in config.templates:
            config.templates[theme] = {}
        config.templates[theme][key] = dest_path
        self.config_repo.save_config(config)

        self._on_log(f"[Template] Saved {dest_name} ({len(file_data)} bytes)")
        return {"path": dest_path, "key": key, "theme": theme}

    def _handle_template_preview(self, params: dict[str, object]) -> object:
        """Return base64-encoded preview of a template image."""
        import base64
        import os

        key = str(params.get("key", ""))
        theme = str(params.get("theme", "light"))

        engine_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        templates_dir = os.path.join(engine_dir, "templates")

        # Try the requested theme first, then fallback
        for th in (theme, "dark" if theme == "light" else "light"):
            tpl_path = os.path.join(templates_dir, f"{key}_{th}.png")
            if os.path.exists(tpl_path):
                with open(tpl_path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("ascii")
                return {
                    "key": key,
                    "theme": th,
                    "filename": f"{key}_{th}.png",
                    "data": f"data:image/png;base64,{data}",
                    "size": os.path.getsize(tpl_path),
                }
        return {"error": {"code": -32000, "message": f"Template not found: {key}"}}

    # ─── Log stream support ───

    def _handle_log_stream(self, params: dict[str, object]) -> object:
        return {"subscribed": True}
