# 任务记录 — 智推助手 WeChat Auto

> 每次开发会话完成后更新本文。记录已完成任务、当前进度、下一步计划。

---

## 当前状态

- **当前 Phase**: 6 — 功能完善 & 可移植性
- **下一步**: Phase 7 — 桌面打包 (Electron builder)
- **最新更新**: 2026-05-14 (Session 4)

---

## Phase 0: 工程基础

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 0.1 | 初始化 git 仓库 | ✅ done | 2026-05-04 |
| 0.2 | 编写 docs/CONVENTIONS.md | ✅ done | 2026-05-04 |
| 0.3 | 编写 docs/TASKS.md | ✅ done | 2026-05-04 |
| 0.4 | 创建 pyproject.toml (uv) | ✅ done | 2026-05-04 |
| 0.5 | 创建 .gitignore | ✅ done | 2026-05-04 |
| 0.6 | 搭建 engine/ 包结构 | ✅ done | 2026-05-04 |
| 0.7 | 创建 domain/models.py | ✅ done | 18 个数据类，覆盖全部领域模型 |
| 0.8 | 创建 domain/interfaces.py | ✅ done | 11 个抽象接口 (ABC) |
| 0.9 | 创建 domain/events.py | ✅ done | 12 个领域事件类型 |
| 0.10 | 搭建 ui/ 脚手架 | ✅ done | Vite + React 18 + TS + Tailwind v4 |
| 0.11 | 首次提交 | ✅ done | 2026-05-04 |

### Phase 0 交付物
- 完整的 Python 包结构 (`engine/domain/`, `engine/application/`, `engine/infrastructure/`, `engine/adapters/`)
- 领域层：models + interfaces + events（零外部依赖）
- UI 脚手架：Vite + React + TypeScript + Tailwind CSS v4 + Zustand + React Query
- 工程配置：pyproject.toml (uv)、.gitignore、ruff、mypy、pytest
- 编码规范文档：CONVENTIONS.md
- 所有 lint 检查通过 (ruff + tsc)

---

## Phase 1: 引擎核心抽离

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 1.1 | 抽离 AttachmentManager → infrastructure/attachment_manager.py | ⬜ pending | |
| 1.2 | 抽离 vision 模板匹配 → infrastructure/automation/vision.py | ⬜ pending | |
| 1.3 | 抽离 input 键鼠模拟 → infrastructure/automation/input.py | ⬜ pending | |
| 1.4 | 抽离 clipboard 剪贴板 → infrastructure/automation/clipboard.py | ⬜ pending | |
| 1.5 | 抽离 window_manager → infrastructure/automation/window_manager.py | ⬜ pending | |
| 1.6 | 实现 platform/base.py + platform/windows.py | ⬜ pending | |
| 1.7 | 实现 IMessagingPlatform + WeChatPlatform | ⬜ pending | |
| 1.8 | 抽离 TaskQueueRunner → application/queue_runner.py | ⬜ pending | |
| 1.9 | 编写 Phase 1 单元测试 | ⬜ pending | |

---

## 开发日志

### 2026-05-04 (Session 1)
- 初始化项目仓库
- 完成代码库全面分析（wechat_auto_v3.0.py 1670 行 + 微信视觉群发助手_v3.jsx 422 行）
- 建立重构架构计划（Clean Architecture + Python engine + React UI + Electron）
- 完成 Phase 0 全部 11 项任务

### 2026-05-04 (Session 2)
- **Phase 1 完成**: AttachmentManager, platform abstraction, vision/input/clipboard/window_manager, WeChatPlatform, queue_runner 全部抽离
- **Phase 2 完成**: SQLiteTaskRepository, SQLiteConfigRepository, FileStore (JSON→SQLite 迁移)
- **Phase 3 完成**: event_bus, task_manager, batch_creator, scheduler
- **Phase 4 完成**: WebSocket JSON-RPC 服务, handlers, serializers, main.py 入口
- **Phase 5 完成**: React UI (api client, 3 hooks, Zustand store, TasksPage/CreatePage/SettingsPage, EditTaskDialog, TaskCard, ToggleSwitch, ContentPreview)
- 所有 lint 通过 (ruff + tsc), engine 模块导入和逻辑验证通过, UI build 成功 (223KB JS, 24KB CSS)
- 总计 25+ 新文件，~4000 行新代码

### 2026-05-13 (Session 3)
- **Electron 桌面体验**: 无边框窗口增加最小化/关闭按钮 (IPC + preload + React)
- **连接修复**: apiClient.call() 改为等待 WebSocket 握手完成再发请求，解决启动时 "Not connected" 错误
- **端口清理**: python-manager.js 启动前/关闭后自动清理 9876 端口残留进程；main.py 优雅关闭 WS server
- **Vite 构建**: outDir 改为 ../desktop/dist，消除手动复制步骤

### 2026-05-14 (Session 4)
- **可移植性**: 屏幕尺寸从硬编码 1920x1080 改为 win32api.GetSystemMetrics 查询；微信标题支持中英文候选；SetForegroundWindow Alt 键绕过前台锁定；DPI 失败增加告警日志；Debug 截图改为环境变量控制；uv 路径增加 Windows 典型位置；模板源 DPI 可在设置页配置
- **拖拽上传**: 每个素材行支持拖拽 + 点击选择文件，base64 导入到 AttachmentManager
- **素材分类**: ContentItem 新增 category 字段（注射美容/美容皮肤科/美容外科），每个素材独立分类
- **时段/任务双验证**: 日期只能选今天及之后，时间若选今天则限制当前时间之后
- **过期任务**: 任务卡片自动检测过期，变灰 + "已过期" 标签
- 双配置 (config.json + SQLite) 合并为 SQLite 单一来源
- 回退偏移从硬编码 px 改为百分比（7% 搜索栏，1.3x 标签点击）
