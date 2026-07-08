# Camoufox Manager 交接文档

## 项目目标

这是一个本地桌面端 Camoufox 指纹浏览器管理器。目标是用 GUI 管理 Camoufox profile、代理、持久化目录、启动参数、运行会话和安装维护任务。

当前实现方式：

- 后端：FastAPI
- 桌面壳：pywebview + Windows WebView2
- 前端：原生 HTML/CSS/JS
- 数据存储：本地 JSON 文件
- Camoufox 启动：后端起独立 Python worker 进程

## 当前运行状态

依赖已经安装过：

- `camoufox 0.4.11`
- `pywebview 6.2.1`
- `fastapi`
- `uvicorn`
- `playwright`

Camoufox 浏览器文件已经 fetch 成功：

- Camoufox browser: `v135.0.1-beta.24`
- 安装路径：`C:\Users\hbq30\AppData\Local\camoufox\camoufox\Cache`

桌面端已验证可启动：

```powershell
python desktop.py
```

或双击：

```text
Start-CamoufoxManager.bat
```

如果只跑 Web 模式：

```powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload
```

打开：

```text
http://127.0.0.1:8765
```

## 已完成功能

### 桌面端

- `desktop.py` 会自动找可用端口。
- 优先用 `pywebview` 打开原生桌面窗口。
- 如果 `pywebview` 不可用，会回退到系统浏览器。
- Windows 下实际使用的是 WebView2。

### UI/UX

- 默认中文。
- 支持中文 / English 双语切换。
- 桌面管理器风格布局，不是营销页。
- 左侧导航：配置档案、运行会话、系统安装。
- 响应式布局已做，移动窄屏不会明显溢出。

### Profile 管理

- 创建 profile
- 编辑 profile
- 删除 profile
- 复制 profile
- 导入 profile JSON
- 导出 profile JSON
- 打开 profile 数据目录

Profile 数据文件：

```text
data/profiles.json
```

运行时 profile 临时文件：

```text
data/runtime/
```

### Camoufox 启动参数

当前 profile 支持字段：

- `name`
- `startup_url`
- `mode`: `browser` / `server`
- `os`: `auto` / `windows` / `macos` / `linux`
- `headless`
- `persistent_context`
- `user_data_dir`
- `humanize`
- `geoip`
- `locale`
- `proxy`
- `block_images`
- `block_webrtc`
- `block_webgl`
- `disable_coop`
- `enable_cache`
- `addons`
- `extra_args`
- `notes`

### 代理支持

代理地址现在支持：

- `http://host:port`
- `https://host:port`
- `socks4://host:port`
- `socks5://host:port`

如果用户只填：

```text
127.0.0.1:8080
```

后端会自动规范化为：

```text
http://127.0.0.1:8080
```

相关代码：

- `backend/app.py` 里的 `ProxyConfig.normalize_server`
- `static/index.html` 里的代理输入框 placeholder

### 安装/维护任务

系统面板支持：

- `install`: `python -m pip install camoufox`
- `fetch`: `camoufox fetch`
- `version`: `camoufox version`
- `path`: `camoufox path`
- `test`: `camoufox test`

注意：`python -m camoufox test` 曾经在本机卡住超过 3 分钟，并留下 Camoufox 进程。真实 GUI 启动 profile 是正常的。

### 会话管理

- 后端通过 `backend/camoufox_worker.py` 启动 Camoufox。
- 每个 GUI 启动的浏览器是一个独立 worker 进程。
- GUI 可查看 worker 日志。
- GUI 可停止进程。

已验证：

- 默认 profile 能启动。
- 能导航到 `https://browserleaks.com/javascript`。
- worker 日志会输出：

```json
{"event":"ready","mode":"browser"}
```

## 关键文件

```text
backend/app.py
```

FastAPI 主服务。负责：

- 静态页面服务
- profile CRUD
- profile import/export/clone
- 打开数据目录
- install/fetch/test/version/path 任务
- session 启停
- Camoufox 安装状态检测

```text
backend/camoufox_worker.py
```

实际启动 Camoufox 的 worker。负责：

- 从 runtime JSON 读取 profile
- 组装 Camoufox kwargs
- 启动 browser/server
- 导航到 startup_url
- 输出 JSON 日志

重要点：

- 如果 `disable_coop=true`，会自动传 `i_know_what_im_doing=True`，避免 Camoufox 的 `LeakWarning`。

```text
desktop.py
```

桌面启动器。负责：

- 找可用端口
- 启动 uvicorn 后端
- 等待后端可用
- 用 pywebview 打开窗口
- 关闭窗口时终止后端

```text
static/index.html
static/styles.css
static/app.js
```

前端界面。没有构建步骤，直接静态加载。

```text
requirements.txt
```

Python 依赖。

```text
Start-CamoufoxManager.bat
Start-CamoufoxManager.ps1
```

Windows 启动入口。

## 已知问题 / 注意事项

### 1. 当前不是完整打包的 exe

现在是 Python 桌面壳，不是单文件安装包。后续如果要发给别人用，建议做：

- PyInstaller 打包
- 图标
- 配置目录迁移到 `%APPDATA%`
- 自动升级或版本显示

### 2. 多实例端口问题

`desktop.py` 会自动找端口，但如果同时开多个实例，会各自占用不同端口，状态不共享。

建议后续加单实例锁：

- Windows mutex
- lock file
- 如果已有实例，直接聚焦已有窗口或打开已有端口

### 3. profile 数据目录当前在项目路径下

默认 profile 的 `user_data_dir` 目前可能是 UNC 路径：

```text
\\192.168.1.122\fnosdrive\指纹浏览器\data\profiles\default
```

这能用，但性能和锁行为不如本机路径。后续建议迁移到：

```text
%APPDATA%\CamoufoxManager\profiles\
```

### 4. `camoufox test` 不可靠

本机跑 `python -m camoufox test` 曾经超时。GUI 真实启动 profile 正常，所以后续可以：

- 把 Test 改成自定义轻量健康检查
- 或给 task 加超时和强制清理
- 或在 UI 上提示 test 可能打开/挂起浏览器窗口

### 5. 任务进程历史不会持久化

当前进程 registry 在内存中。重启应用后会话历史丢失，这是可接受的 MVP 行为。

### 6. 没有认证

当前监听 `127.0.0.1`，本地桌面工具可以接受。如果以后开放到局域网，需要加认证。

## 建议下一步开发

### 优先级 P0

1. 单实例锁，避免多开桌面端导致多端口、多状态。
2. 把用户数据和 profiles 移到 `%APPDATA%\CamoufoxManager`。
3. 增加 task timeout，尤其是 `test`。
4. 启动 session 前增加更清楚的错误提示：代理不可达、路径不可写、Camoufox 未安装。

### 优先级 P1

1. Profile 表单分组：
   - 基础
   - 代理
   - 指纹/环境
   - 高级参数
2. 代理测试按钮：
   - 测试 TCP 连通
   - 测试 HTTP CONNECT 或普通 HTTP 请求
   - 显示出口 IP
3. 启动前预检：
   - user data dir 可写
   - proxy 格式合法
   - startup_url 合法
   - Camoufox browser path 存在
4. Session 详情页：
   - PID
   - 启动时间
   - profile 快照
   - 日志下载

### 优先级 P2

1. PyInstaller 打包。
2. 托盘图标。
3. 深色模式。
4. Profile 分组/标签。
5. 批量启动/停止。
6. 导入代理池。
7. 多 profile 并发启动队列。

## 常用命令

安装依赖：

```powershell
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 60 --retries 5
```

下载 Camoufox 浏览器：

```powershell
python -m camoufox fetch
```

查看版本：

```powershell
python -m camoufox version
```

查看浏览器路径：

```powershell
python -m camoufox path
```

启动桌面端：

```powershell
python desktop.py
```

启动 Web 调试模式：

```powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload
```

语法检查：

```powershell
python -m compileall backend desktop.py
node --check static/app.js
```

## API 速查

```text
GET  /api/system
GET  /api/profiles
POST /api/profiles
PUT  /api/profiles/{profile_id}
DELETE /api/profiles/{profile_id}
POST /api/profiles/{profile_id}/clone
POST /api/profiles/{profile_id}/open-data-dir
GET  /api/profiles/export
POST /api/profiles/import
POST /api/tasks/{install|fetch|test|version|path}
GET  /api/tasks
POST /api/sessions
GET  /api/sessions
POST /api/processes/{process_id}/stop
```

## 当前验证记录

已验证：

- 依赖安装成功。
- Camoufox fetch 成功。
- `/api/system` 正常返回 installed/path/version。
- 默认 profile 可启动。
- 启动后日志可到 `ready`。
- 代理地址可填 `http://`。
- 代理地址不写协议时会自动补 `http://`。
- 桌面窗口可启动，标题为 `Camoufox Manager`。

截图：

```text
artifacts/run-installed-session.png
artifacts/desktop-polished.png
artifacts/mobile-polished.png
```
