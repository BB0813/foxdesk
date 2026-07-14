# FoxDesk

本地 Camoufox 指纹浏览器管理器 — 免费、开源、隐私优先。

**当前版本：`1.1.0`（Stable）**

<p align="center">
  <img src="static/logo.png" width="120" alt="FoxDesk Logo">
</p>

## 功能特性

- **Profile 管理** — 创建、编辑、克隆、导入导出、标签分组
- **指纹控制** — 指纹参数编辑 + 一键随机生成（映射到 Camoufox config）
- **指纹检测** — 静态一致性评分（0-100）
- **代理池** — 统一管理 HTTP/SOCKS 代理，档案可引用；支持认证测试与批量导入
- **Cookie 管理** — 导出 SQLite Cookie；导入 JSON / Netscape，下次启动注入
- **会话管理** — 启动/停止/日志、错误展示、Server 模式、批量操作
- **系统托盘** — 隐藏到托盘、停止全部会话、退出时清理
- **档案模板** — 一键创建纯净 / 电商 / 自动化等预设
- **傻瓜式首次引导** — 安装后自动检测并安装/下载 Camoufox 环境
- **应用内一键更新** — 检测 GitHub Release，下载 Setup，**校验 SHA256** 后安装
- **本机 API 令牌** — UI 注入 `X-FoxDesk-Token`，降低本机其它进程随意调用风险
- **健康检查 & 运行时清理**
- **下载源切换** — GitHub 官方 / 镜像 / 自定义
- **深浅色模式 / 中英文双语 / 快捷键 / 右键菜单**
- **Windows 安装包** — PyInstaller + Inno Setup + GitHub Actions

## 快速开始

```bash
git clone https://github.com/BB0813/foxdesk.git
cd foxdesk
python -m pip install -r requirements.txt
python desktop.py
# 或
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload
```

Windows 也可双击 `Start-CamoufoxManager.bat`。

### 卸载 / 重装清理

- **1.1.0+** 默认安装到：`%LOCALAPPDATA%\Programs\FoxDesk`（一般无需管理员）
- 卸载时可选择是否删除用户数据：`%APPDATA%\CamoufoxManager`
- 旧版若装在 `C:\Program Files\FoxDesk`，请以管理员运行：

```powershell
powershell -ExecutionPolicy Bypass -File tools/clean-foxdesk.ps1 -Yes
# 或右键管理员运行 tools/purge-foxdesk-admin.bat
```

## 构建 Windows 安装包

```bat
build.bat
```

产物：

- 便携版：`dist/FoxDesk/FoxDesk.exe`
- 安装包：`installer_output/FoxDesk-1.1.0-Setup.exe`

### CI/CD

```bash
git tag v1.1.0
git push origin v1.1.0
```

- Workflow：`.github/workflows/build.yml`
- 产物：Setup.exe + portable zip + **SHA256SUMS**
- 含 `beta|alpha|rc` 的版本标记为 pre-release

## 安全与威胁模型（请阅读）

FoxDesk 是**本机桌面工具**：

| 项 | 行为 |
|---|---|
| 监听地址 | 仅 `127.0.0.1`（不要改成 `0.0.0.0` 暴露到局域网） |
| API 鉴权 | 每个进程随机 `X-FoxDesk-Token`，由首页注入给 UI |
| 数据存储 | `%APPDATA%\CamoufoxManager`（历史目录名） |
| 代理密码 | 本地 JSON **明文**存储 |
| 自动更新 | 下载 GitHub Release 的 Setup，并在存在 `SHA256SUMS` 时校验哈希 |

**不要**把本服务端口映射到公网。本机恶意软件仍可能读取数据目录。

## 已知限制

- Server 模式在部分 Camoufox 版本下可能无法自动捕获 `ws_endpoint`
- 指纹检测为静态一致性评分，**不是**反检测保证
- GitHub API 未认证，极端情况下可能触发速率限制
- 从 beta 升级：建议卸载旧版（尤其 Program Files 安装）后装 1.1.0

完整变更见 [CHANGELOG.md](CHANGELOG.md)。

## 技术栈

| 组件 | 技术 |
|---|---|
| 后端 | Python 3.12+ / FastAPI / Pydantic |
| 桌面壳 | pywebview + Windows WebView2 |
| 前端 | 原生 HTML/CSS/JS |
| 浏览器 | Camoufox |
| 数据 | `%APPDATA%\CamoufoxManager`（本地 JSON） |
| 打包 | PyInstaller + Inno Setup |
| CI/CD | GitHub Actions |

## 项目结构

```
foxdesk/
├── desktop.py              # 桌面启动器 / frozen worker 入口
├── backend/                # FastAPI + setup/update/proxy
├── static/                 # 前端
├── tools/                  # 清理脚本
├── foxdesk.spec            # PyInstaller
├── installer.iss           # Inno Setup
└── .github/workflows/      # CI 打包发布
```

## License

见 [LICENSE](LICENSE)。
