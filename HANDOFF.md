# FoxDesk 交接文档

## 项目目标

本地桌面端 Camoufox 指纹浏览器管理器（产品名 **FoxDesk**）。用 GUI 管理 profile、代理、持久化目录、启动参数、运行会话和安装维护任务。

实现方式：

- 后端：FastAPI
- 桌面壳：pywebview + Windows WebView2
- 前端：原生 HTML/CSS/JS
- 数据存储：`%APPDATA%\FoxDesk` 本地 JSON（旧 `%APPDATA%\CamoufoxManager` 自动迁移）
- Camoufox 启动：独立 worker 进程（`backend/camoufox_worker.py`）
- 会话控制：runtime 旁路 `.cmd.jsonl` / `.result.jsonl`（可选 `.ws`）

## 启动

```powershell
python desktop.py
# 或
.\Start-FoxDesk.bat
# 旧名仍可用
.\Start-CamoufoxManager.bat
```

开发 API：

```powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload
```

## 当前版本

见 `VERSION`（发布线：`1.3.1`+）。

## 关键本地能力

- Profile CRUD / 标签 / 模板 / Cookie 导入导出
- 指纹参数 + 随机生成 + 静态一致性评分 + 运行中探测
- 会话：启动停止、日志、并发上限、空闲自动停止、实时导航
- Server 模式：尽量捕获 `ws_endpoint`，可刷新端点
- 代理池：加密存盘、健康巡检、sticky / round_robin / random_healthy
- 更新：ghproxy 默认 + 可选 GitHub Token（环境变量优先，不内置）
- 备份：密码加密 `.fdk` 创建/列表/恢复（恢复前 pre-restore 快照）
- 诊断导出、本机 `X-FoxDesk-Token`

## 明确不做

- 云控平台
- 在仓库/安装包内嵌 GitHub Token

## 测试

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -m pytest tests -q
```

CI（tag `v*`）会 compileall、pytest、打包、发 Release。

## 数据目录

- 主目录：`%APPDATA%\FoxDesk`
- 备份：`%APPDATA%\FoxDesk\backups\foxdesk-backup-*.fdk`
- 旧目录：`%APPDATA%\CamoufoxManager`（首次启动迁移）

## 发布

```bash
git tag v1.3.1
git push origin main
git push origin v1.3.1
```
