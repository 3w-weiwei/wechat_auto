# 遗留问题

## 严重

### 1. 发送按钮不执行自动流程

**现象**：点击"发送"后，日志仅显示 `[系统] 收到手动执行请求`，后续无任何执行日志。

**排查过程**：
- `_handle_task_run_now` 被正确调用 → `on_run_now` 执行 → 日志出现 ✅
- `_start_next_batch`（现 `EngineApp._try_start_batch`）未被调用或未产生输出 ❌
- 已从闭包方案重写为类方案（`EngineApp` 类），理论上消除了闭包作用域问题
- 终端 `print()` debug 输出也未见，说明函数体未执行

**可能原因**：
- `_try_start_batch` 内部的异常被 `dispatch` 的 `try/except` 吞掉
- `on_run_now` 回调存储/传递出现问题（Handlers 保存函数引用时出错）
- asyncio 事件循环与线程 WebSocket 处理的交互问题

**下一步**：在 `_try_start_batch` 第一行和 `dispatch` 方法增加 `traceback.print_exc()` 直接输出异常到终端

### 2. 微信自动化完整流程未验证

自动发送的完整流程（激活微信 → 校准位置 → 截图识别 → 搜索群聊 → 选择目标 → 发送内容）从未端到端跑通。流程代码已实现但卡在第 1 个问题（点击发送不触发队列）。

## 中等

### 3. 引擎日志中文乱码

终端显示的中文日志全部乱码（如 `[ϵͳ]` 应为 `[系统]`）。可能是 Python 的 stdout 编码或 Electron spawn 的编码问题。不影响功能但影响调试。

### 4. 端口 9876 残留

端口 9876 在先前的会话中多次被残留进程占用，导致新进程无法绑定。没有自动重试或清理机制。需要手动 `taskkill` 清理。

### 5. Electron GPU 缓存错误

```
ERROR:net/disk_cache/cache_util_win.cc:25] Unable to move the cache: 拒绝访问。
ERROR:gpu/ipc/host/gpu_disk_cache.cc:725] Gpu Cache Creation failed: -2
```

不影响功能，是 Electron 在写 GPU 缓存目录时的权限问题。可通过 `--disable-gpu` 或修复缓存目录权限解决。

### 6. 模板图片依赖性

微信自动化依赖 `engine/templates/` 下的模板图片：
- `search_light.png` / `search_dark.png` — 微信搜索框图标
- `group_label_light.png` / `group_label_dark.png` — 群聊标签
- `recent_label_light.png` / `recent_label_dark.png` — 最常使用标签

模板图片必须精确匹配用户微信窗口的实际外观（缩放级别、主题）。不匹配时自动化会降级到坐标推算，精度较低。

## 轻微

### 7. 深色主题状态未持久化

切换浅色/深色主题后，刷新页面主题状态未能正确加载（`config.get` 偶尔返回默认值）。

### 8. 偏好设置开关不可交互

设置页的"执行前自动唤醒"和"模拟人工延迟"开关仅展示，无交互逻辑。

### 9. 窗口拖动偶发失效

`-webkit-app-region: drag` 在 Electron 中偶发失效（需点击空白区域而非按钮区域）。按钮区域使用了 `no-drag` class，但某些子元素可能未覆盖。

---

*最后更新：2026-05-04*
