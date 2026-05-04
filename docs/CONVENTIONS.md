# 编码规范 — 智推助手 WeChat Auto

> **重要：每次开始开发前必须阅读本文。开发完成后需在 TASKS.md 中记录进展。**

---

## 1. 项目结构约定

```
wechat_auto/
├── engine/          # Python 后端 — 所有业务逻辑、自动化引擎
│   ├── domain/      # 纯业务逻辑，零外部依赖（除标准库和 pydantic）
│   ├── application/ # 用例编排，依赖 domain 接口
│   ├── infrastructure/ # 平台/存储/自动化实现
│   └── adapters/    # 对外 IPC 接口（WebSocket）
├── ui/              # React + TypeScript 前端 — 仅展示和用户交互
├── tests/           # 测试，镜像 engine/ + ui/ 结构
├── docs/            # 项目文档
└── desktop/         # Electron 桌面壳（后续阶段）
```

## 2. Python 规范

### 2.1 环境管理
- 使用 **uv** 管理虚拟环境和依赖
- 创建环境: `uv venv`
- 激活: `.venv\Scripts\activate` (Win) 或 `source .venv/bin/activate` (Unix)
- 添加依赖: `uv add <package>`
- 运行脚本: `uv run python -m engine.main`

### 2.2 代码风格
- **ruff** 格式化 + lint，配置在 `pyproject.toml`
- 行宽: **100** 字符
- 目标版本: **Python 3.11**
- 类型注解: 所有公共函数/方法必须有类型注解
- 使用 `from __future__ import annotations` 延迟求值

### 2.3 命名规范
| 类型 | 规则 | 示例 |
|------|------|------|
| 模块/文件 | snake_case | `task_manager.py` |
| 类 (包括 ABC) | PascalCase | `TaskRepository`, `WeChatPlatform` |
| 函数/方法 | snake_case | `get_active_tasks()` |
| 变量 | snake_case | `task_list`, `current_dpi` |
| 常量 | UPPER_SNAKE | `DEFAULT_THRESHOLD = 0.65` |
| 私有成员 | 前缀 `_` | `_build_scale_list()` |
| 接口/ABC | 前缀 `I` | `IPlatformAdapter`, `ITaskRepository` |

### 2.4 导入顺序
1. `from __future__ import annotations`
2. 标准库
3. 第三方库
4. 内部模块（相对导入 `from .domain.models import Task`）

**引擎内部使用相对导入**。`engine/` 是一个自包含的 Python 包。

### 2.5 领域层铁律
**`engine/domain/` 中禁止 import：**
- `opencv-python` (cv2)
- `numpy`
- `pyautogui`
- `pywin32` / `win32*`
- `pyside6` / `pyqt*`
- 任何平台相关库

**允许的依赖：** `dataclasses`, `abc`, `datetime`, `enum`, `typing`, `uuid`, `pydantic`

### 2.6 异常处理
- 永远不要写裸 `except: pass`
- 使用具体异常类型
- 基础设施层抛出领域层定义的异常
- 异常类定义在 `domain/exceptions.py`

### 2.7 测试
- 文件名: `test_{模块名}.py`
- 测试类: `Test{被测类名}`
- 测试函数: `test_{场景描述}`
- 使用 pytest fixtures 管理测试依赖
- Mock 外部接口，不 Mock 领域对象
- 覆盖率目标: domain > 90%, application > 80%, infrastructure > 60%

## 3. TypeScript / React 规范

### 3.1 环境
- 包管理: **npm**（Node.js >= 20）
- 构建: **Vite**
- TypeScript: **strict mode**
- 样式: **Tailwind CSS**（优先使用 utility classes）

### 3.2 命名规范
| 类型 | 规则 | 示例 |
|------|------|------|
| 文件 | PascalCase (组件) 或 camelCase (工具) | `TaskCard.tsx`, `useTasks.ts`, `api.ts` |
| React 组件 | PascalCase | `TaskCard`, `CreatePage` |
| Hook 函数 | `use` 前缀 + camelCase | `useWebSocket`, `useTasks` |
| 类型/接口 | PascalCase (禁止 `I` 前缀) | `Task`, `ContentItem` |
| 变量/函数 | camelCase | `taskList`, `handleSubmit` |
| 常量 | UPPER_SNAKE | `MAX_RETRY_COUNT` |

### 3.3 组件结构
- 每个组件一个文件
- Props 类型内联定义（简单时）或导出 interface
- 优先使用函数式组件 + Hooks
- 状态管理: **Zustand**（全局） + **React Query**（服务端数据）

### 3.4 样式约定
- 使用 Tailwind utility classes，尽量不写自定义 CSS
- 颜色使用 Tailwind 内置色板（slate/green/blue/red/amber），匹配原 JSX 原型
- 窗口尺寸: 390×760（手机比例），外层深色背景

## 4. Git 规范

### 4.1 提交信息
使用 Conventional Commits:
```
feat: 添加定期执行日志轮转功能
fix: 修复 DPI 缩放时模板匹配失败
refactor: 将 AttachmentManager 抽离为独立模块
test: 添加 TaskManager 单元测试
docs: 更新架构设计文档
chore: 配置 ruff 和 mypy
```

### 4.2 分支策略
- `main` — 稳定可发布
- `develop` — 开发主线
- `feat/{功能名}` — 功能分支
- `fix/{问题}` — 修复分支

### 4.3 提交粒度
- 每个逻辑变更单独提交
- 不要将无关改动混在一个提交中
- 提交前通过 lint 和测试

## 5. 架构约束

### 5.1 依赖方向
```
UI → Adapters → Application → Domain ← Infrastructure
```
- 外层依赖内层，内层永远不依赖外层
- Domain 层是所有依赖的终点

### 5.2 新增消息平台
实现 `IMessagingPlatform` 接口，在 `infrastructure/automation/` 下创建对应模块。不修改 domain 和 application 层代码。

### 5.3 更换 UI 框架
只需替换 `ui/` 和 IPC 适配层。engine 核心零改动。

## 6. 文档要求

- 每个模块顶部的 docstring 用一句话说明模块职责
- 公共 API（接口方法、领域服务）需要参数和返回值类型注解
- 复杂算法（如模板匹配的 multi-scale search）需要在实现处写简短注释说明 WHY
- 不写冗余注释来解释 WHAT（代码本身应自解释）

---

*最后更新: 2026-05-04 | Phase 0*
