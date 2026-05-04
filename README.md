# 智推助手 WeChat Auto v4

微信智能群发工具 — 通过计算机视觉（OpenCV）和键鼠模拟（PyAutoGUI）实现微信消息自动定时发送。

## 功能

- **定时任务** — 创建群聊 × 时段的批量推送计划
- **自动化发送** — 模板匹配定位微信元素 → 模拟点击 → 粘贴内容 → 回车发送
- **附件管理** — 图片/视频文件导入、去重、清理
- **模板管理** — 浅色/深色微信主题模板切换，自定义模板上传
- **调度系统** — 后台 5 秒轮询，到期自动执行
- **日志系统** — 实时运行日志，每步操作详细记录

## 技术栈

| 层 | 技术 |
|----|------|
| 自动化引擎 | Python 3.12 + OpenCV + PyAutoGUI + mss |
| WebSocket 服务 | websockets + asyncio |
| 前端 UI | React 18 + TypeScript + Tailwind CSS v4 |
| 桌面壳 | Electron |
| 存储 | SQLite |
| 依赖管理 | Python: uv / UI: npm |

## 项目结构

```
wechat_auto/
├── engine/                    # Python 引擎核心
│   ├── domain/                # 领域模型、接口、事件（纯业务逻辑）
│   ├── application/           # 用例编排（任务管理、调度、队列）
│   ├── infrastructure/        # 平台适配、自动化引擎、存储
│   │   ├── automation/        # vision / input / clipboard / window / wechat
│   │   ├── platform/          # Windows 平台适配器
│   │   ├── storage/           # SQLite 仓库 + 文件存储
│   │   └── attachment_manager.py
│   ├── adapters/              # WebSocket JSON-RPC 服务
│   ├── templates/             # 微信视觉匹配模板图片
│   └── main.py                # 引擎入口
├── ui/                        # React 前端
│   └── src/
│       ├── components/        # tasks / create / settings / shared
│       ├── hooks/             # useWebSocket / useTasks / useConfig
│       ├── store/             # Zustand 全局状态
│       └── services/          # WebSocket API 客户端
├── desktop/                   # Electron 桌面壳
├── docs/                      # 文档
│   ├── STARTUP.md             # 启动指南
│   ├── ISSUES.md              # 遗留问题
│   └── CONVENTIONS.md         # 编码规范
└── tests/                     # 测试
```

## 快速开始

### 环境要求
- Python 3.12+（通过 uv 管理）
- Node.js >= 20
- Windows 11 + 微信桌面版

### 安装

```bash
cd wechat_auto

# Python 依赖
uv sync

# 前端依赖
cd ui && npm install && cd ..

# Electron 依赖
cd desktop && npm install && cd ..
```

### 启动

```bash
# 完整桌面应用
cd desktop && npm start

# 或分步启动（调试用）
uv run python -m engine.main          # 终端 1：引擎
cd ui && npm run dev                  # 终端 2：前端
```

打开后确保微信已登录并可见，在设置页点击"重新校准微信窗口"，然后创建任务即可使用。

## 自动化流程

```
校准窗口 → 截图 → 模板匹配搜索框 → 点击搜索 → 输入群名
→ 模板匹配群聊标签 → 点击进入 → 点击输入框 → 粘贴内容 → 回车发送
```

模板图片位于 `engine/templates/`，分浅色/深色两套。可在设置页上传自定义模板。

## 文档

- [启动指南](docs/STARTUP.md)
- [遗留问题](docs/ISSUES.md)
- [编码规范](docs/CONVENTIONS.md)

## License

MIT
