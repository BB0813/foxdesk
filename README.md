# FoxDesk

本地 Camoufox 指纹浏览器管理器 — 免费、开源、隐私优先。

**当前版本：`1.3.1`（Stable）**

<p align="center">
  <img src="static/logo.png" width="120" alt="FoxDesk Logo">
</p>

## 功能特性

- **Profile 管理** — 创建、编辑、克隆、导入导出、标签分组
- **指纹控制** — 参数编辑 + 随机生成 + 运行中探测报告 + 静态一致性评分
- **会话控制** — 启动/停止/日志、**实时导航**、并发上限、空闲自动停止
- **Server 模式** — 尽量捕获 `ws_endpoint`，便于外部 Playwright 连接
- **代理池** — 健康巡检、粘性/轮询/随机健康分配；密码 DPAPI 加密
- **Cookie 管理** — 导出 SQLite Cookie；导入 JSON / Netscape，下次启动注入
- **场景模板** — 纯净 / 电商 / 自动化 / 社媒 / 调研 / 移动窗口 等
- **本地备份** — 密码加密 `.fdk` 导出/恢复（恢复前自动快照）
- **应用内更新** — GitHub Release + **ghproxy** + 可选 Token + SHA256
- **诊断导出** — 系统页一键导出脱敏诊断包
- **本机 API 令牌** — UI 注入 `X-FoxDesk-Token`
- **首次引导 / 托盘 / 双语 / 安装包**

## 快速开始

```bash
git clone https://github.com/BB0813/foxdesk.git
cd foxdesk
python -m pip install -r requirements.txt
python desktop.py
# 或
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload
```

Windows 也可双击 `Start-FoxDesk.bat`（旧名 `Start-CamoufoxManager.bat` 仍可用）。

### 卸载 / 重装清理

- **1.1.0+** 默认安装到：`%LOCALAPPDATA%\Programs\FoxDesk`（一般无需管理员）
- 卸载时可选择是否删除用户数据：`%APPDATA%\FoxDesk`（旧版 `CamoufoxManager` 会自动迁移）
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
- 安装包：`installer_output/FoxDesk-1.3.1-Setup.exe`

### CI/CD

```bash
git tag v1.3.1
git push origin v1.3.1
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
| 数据存储 | `%APPDATA%\FoxDesk`（旧版 `CamoufoxManager` 自动迁移） |
| 代理密码 | 本机加密存储（Windows DPAPI；非 Windows 为机器本地混淆） |
| 自动更新 | 默认 ghproxy 镜像；可选 GitHub Token；存在 `SHA256SUMS` 时校验哈希 |

**不要**把本服务端口映射到公网。本机恶意软件仍可能读取数据目录。

## 已知限制

- Server 模式在部分 Camoufox 版本下仍可能延迟/无法捕获 `ws_endpoint`（可点「刷新端点」）
- 指纹检测为静态一致性评分，**不是**反检测保证
- 无 Token 时仍可能遇到 GitHub 限流；1.2.0+ 会回退网页/Atom + ghproxy
- 从旧版升级：建议直接装 1.3.1；Program Files 旧安装请先卸载

完整变更见 [CHANGELOG.md](CHANGELOG.md)。

## 技术栈

| 组件 | 技术 |
|---|---|
| 后端 | Python 3.12+ / FastAPI / Pydantic |
| 桌面壳 | pywebview + Windows WebView2 |
| 前端 | 原生 HTML/CSS/JS |
| 浏览器 | Camoufox |
| 数据 | `%APPDATA%\FoxDesk`（本地 JSON；旧版目录自动迁移） |
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


## 更新与 GitHub Token

- **默认镜像**：`ghproxy`（可在系统页改为 GitHub 官方）
- **可选 Token**（提高 `api.github.com` 配额，非必须）：
  1. 环境变量 `FOXDESK_GITHUB_TOKEN` 或 `GITHUB_TOKEN`（推荐，不写进仓库）
  2. 或在 **系统 → 更新设置** 粘贴 Personal Access Token（本机加密保存）
- **请勿**把 Token 提交到 git / 打包进安装包

创建 Token（需你自己的 GitHub 账号）：
https://github.com/settings/tokens  
权限只需 **public_repo** 读公开 Release 即可（classic）或 fine-grained 对 `BB0813/foxdesk` 只读 Contents/Metadata。
