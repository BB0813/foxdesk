# FoxDesk

本地 Camoufox 指纹浏览器管理器 — 免费、开源、隐私优先。

**当前版本：`1.1.0-beta.5`**

<p align="center">
  <img src="static/logo.png" width="120" alt="FoxDesk Logo">
</p>

## 功能特性

- **Profile 管理** — 创建、编辑、克隆、导入导出、标签分组
- **指纹控制** — 指纹参数编辑 + 一键随机生成（映射到 Camoufox config）
- **指纹检测** — 静态一致性评分（0-100）
- **代理池** — 统一管理 HTTP/SOCKS 代理，档案可引用；支持认证测试与批量导入
- **Cookie 管理** — 导出 SQLite Cookie；导入 JSON / Netscape，下次启动注入
- **会话管理** — 启动/停止/日志、错误展示、Server 模式端点复制、批量操作
- **系统托盘** — 隐藏到托盘、停止全部会话、退出时清理
- **档案模板** — 一键创建纯净 / 电商 / 自动化等预设
- **傻瓜式首次引导** — 安装后自动检测并安装/下载 Camoufox 环境，无需手动点安装
- **应用内一键更新** — 启动自动检测 GitHub Release，弹窗提醒，下载 Setup 并启动安装
- **健康检查 & 运行时清理** — 轻量自检、过期 runtime 清理
- **下载源切换** — GitHub 官方 / 镜像 / 自定义
- **深浅色模式** — 一键切换，自动保存
- **中英文双语** — 完整 i18n 支持
- **键盘快捷键** — Ctrl+1/2/3/4 切换标签，Ctrl+N 新建，Ctrl+S 保存
- **右键菜单** — 档案右键快速操作
- **Windows 安装包** — PyInstaller + Inno Setup + GitHub Actions 自动构建

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/BB0813/foxdesk.git
cd foxdesk

# 安装依赖
python -m pip install -r requirements.txt

# 启动桌面端
python desktop.py

# 或启动 Web 调试模式
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload
```

Windows 也可双击 `Start-CamoufoxManager.bat`。

## 构建 Windows 安装包

```bat
build.bat
```

或手动：

```bash
python make_ico.py
python -m PyInstaller foxdesk.spec --noconfirm --clean
# 需要 Inno Setup 6
iscc installer.iss
```

产物：

- 便携版：`dist/FoxDesk/FoxDesk.exe`
- 安装包：`installer_output/FoxDesk-1.1.0-beta.5-Setup.exe`

### CI/CD

推送 tag 或手动触发 workflow 会自动构建并发布 Release：

```bash
git tag v1.1.0-beta.5
git push origin v1.1.0-beta.5
```

- Workflow：`.github/workflows/build.yml`
- 触发：`v*` tag / `workflow_dispatch`
- 产物：Setup.exe + portable zip
- 含 `beta|alpha|rc` 的版本会标记为 **pre-release**

## 技术栈

| 组件 | 技术 |
|---|---|
| 后端 | Python 3.12+ / FastAPI / Pydantic |
| 桌面壳 | pywebview + Windows WebView2 |
| 前端 | 原生 HTML/CSS/JS（无框架） |
| 浏览器 | Camoufox（Firefox 隐蔽模式） |
| 数据存储 | `%APPDATA%\CamoufoxManager`（本地 JSON） |
| 打包 | PyInstaller + Inno Setup |
| CI/CD | GitHub Actions |

## 项目结构

```
foxdesk/
├── desktop.py              # 桌面启动器 / frozen worker 入口
├── backend/
│   ├── app.py              # FastAPI 主服务
│   └── camoufox_worker.py  # Camoufox worker
├── static/                 # 前端 SPA + 离线图标
├── docs/                   # GitHub Pages 文档站
├── foxdesk.spec            # PyInstaller 配置
├── installer.iss           # Inno Setup 脚本
├── build.bat               # 本地构建脚本
├── VERSION                 # 当前版本号
└── requirements.txt
```

## 数据目录

用户数据默认位于：

```text
%APPDATA%\CamoufoxManager\
  profiles.json
  profiles\
  runtime\
  channels.json
  activity.json
```

旧版项目内 `data/` 会在首次启动时自动迁移。

## License

MIT — 见 [LICENSE](./LICENSE)
