# FoxDesk

本地 Camoufox 指纹浏览器管理器 — 免费、开源、隐私优先。

<p align="center">
  <img src="static/logo.png" width="120" alt="FoxDesk Logo">
</p>

## 功能特性

- **Profile 管理** — 创建、编辑、克隆、导入导出、标签分组
- **指纹控制** — 13 项指纹参数精确编辑 + 一键随机生成
- **指纹检测** — 自动分析指纹一致性，0-100 分评分
- **代理支持** — HTTP/HTTPS/SOCKS4/SOCKS5，内置测试 + 批量导入
- **Cookie 管理** — 导入导出 Cookie
- **会话管理** — 启动/停止/日志查看/批量操作
- **下载源切换** — GitHub 官方 / 镜像 / 自定义
- **深浅色模式** — 一键切换，自动保存
- **中英文双语** — 完整 i18n 支持
- **键盘快捷键** — Ctrl+1/2/3 切换标签，Ctrl+N 新建，Ctrl+S 保存
- **右键菜单** — 档案右键快速操作
- **PyInstaller 打包** — 支持 Windows exe 构建

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/yourname/foxdesk.git
cd foxdesk

# 安装依赖
python -m pip install -r requirements.txt

# 启动桌面端
python desktop.py

# 或启动 Web 调试模式
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload
```

## 构建 exe

```bash
# 双击 build.bat
# 或手动执行
python -m PyInstaller foxdesk.spec --noconfirm --clean
```

产物位于 `dist/FoxDesk/FoxDesk.exe`。

## 技术栈

| 组件 | 技术 |
|---|---|
| 后端 | Python 3.12+ / FastAPI / Pydantic |
| 桌面壳 | pywebview + Windows WebView2 |
| 前端 | 原生 HTML/CSS/JS（无框架） |
| 浏览器 | Camoufox（Firefox 隐蔽模式） |
| 数据存储 | 本地 JSON 文件 |
| 打包 | PyInstaller |
| CI/CD | GitHub Actions |

## 项目结构

```
foxdesk/
├── desktop.py              # 桌面启动器
├── backend/
│   ├── app.py              # FastAPI 主服务
│   └── camoufox_worker.py  # Camoufox worker 进程
├── static/
│   ├── index.html          # 前端 SPA
│   ├── styles.css          # 样式（双主题）
│   ├── app.js              # 前端逻辑
│   └── logo.png            # 品牌 Logo
├── docs/
│   └── index.html          # GitHub Pages 文档站
├── data/                   # 用户数据（运行时生成）
├── foxdesk.spec            # PyInstaller 配置
├── build.bat               # 本地构建脚本
└── requirements.txt        # Python 依赖
```

## 文档

📖 **[在线文档](https://yourname.github.io/foxdesk/)**

## License

MIT
