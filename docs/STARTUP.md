# 启动指南

## 前置条件

- Python 3.11+（通过 uv 管理）
- Node.js >= 20
- uv 已安装：`C:\Users\vv339\.local\bin\uv.exe`

## 首次启动

```bash
cd D:\0Learn\myself\vibe-coding\claude-code-desktop\wechat_auto

# 1. 安装 Python 依赖（仅首次）
uv sync

# 2. 安装前端依赖（仅首次）
cd ui && npm install && cd ..

# 3. 安装 Electron 依赖（仅首次）
cd desktop && npm install && cd ..
```

## 日常启动

### 方式 1：完整 Electron 桌面应用
```bash
cd D:\0Learn\myself\vibe-coding\claude-code-desktop\wechat_auto\desktop
npm start
```

### 方式 2：分步启动（调试用）
```bash
# 终端 1 — 启动引擎
cd D:\0Learn\myself\vibe-coding\claude-code-desktop\wechat_auto
uv run python -m engine.main

# 终端 2 — 启动前端开发服务器
cd D:\0Learn\myself\vibe-coding\claude-code-desktop\wechat_auto\ui
npm run dev
# 浏览器打开 http://localhost:5173
```

## 重启前务必清理旧进程

端口 9876 常被旧进程占用，重启前清理：

```bash
cd D:\0Learn\myself\vibe-coding\claude-code-desktop\wechat_auto
uv run python -c "
import subprocess
out = subprocess.run(['netstat','-ano'], capture_output=True).stdout
for line in out.splitlines():
    if b':9876' in line:
        parts = line.split()
        pid = int(parts[-1])
        subprocess.run(['taskkill','/f','/pid',str(pid)], capture_output=True)
        print(f'killed {pid}')
"
```
```bash
uv run python -c "import subprocess; out = subprocess.run(['netstat','-ano'], capture_output=True).stdout; [subprocess.run(['taskkill','/f','/pid',str(int(line.split()[-1]))]) for line in out.splitlines() if b':9876' in line]"
```

## 端口

- 引擎 WebSocket: `ws://127.0.0.1:9876`
- 前端开发服务器: `http://localhost:5173`
