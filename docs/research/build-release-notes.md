# 1.4.0-dev 打包与发布说明（阶段 A）

**目标**：在 B（安装/错误体验）完成后，做可重复的打包与安装验证。  
**不保证**：注册/订阅/对齐 Multilogin。

---

## 1. 源码门禁（打包前）

```bash
python -m compileall backend tools desktop.py -q
python -m pytest tests -q -p no:sanic
python tools/smoke_phase_c_headed.py --backend patchright
python tools/bstatic_probe.py --backend patchright --require-webdriver-false
```

期望：pytest 全绿；smoke/bstatic ok。

---

## 2. 构建

```bat
build.bat
```

产物（以脚本为准）：

- `dist/FoxDesk/FoxDesk.exe`（便携）
- `installer_output/FoxDesk-*-Setup.exe`（若本机有 Inno Setup）

版本号来自仓库根目录 `VERSION`（当前 `1.4.0-dev`）。

### 体积策略

- 默认 **不**把 Playwright/Patchright 浏览器缓存打进安装包主体积  
- 用户首次 Chromium：按系统页提示执行  
  - `playwright install chromium`  
  - `patchright install chromium`  
- `foxdesk.spec` 已 collect patchright 模块；构建后人工看 `dist` 体积是否异常膨胀

---

## 3. 安装包冒烟清单

| # | 步骤 | 期望 |
|---|---|---|
| 1 | 安装/解压启动 FoxDesk | 主窗 + 本机 API |
| 2 | 系统页 | 显示 app_version=1.4.0-dev；Chromium 栈状态 |
| 3 | Camoufox Install/Fetch（若需） | 可启动 camoufox 档案 |
| 4 | 模板「AI 工作档案」 | 创建成功；user_data 路径含 `chromium` |
| 5 | 启动 AI 档案（有 patchright 时） | ready；日志含 `[chromium_backend]` |
| 6 | 故意未 install 浏览器时启动 | 错误文案含 `install chromium` 命令 |
| 7 | channel=chrome 且无 Chrome | 启动前校验失败，提示装 Chrome 或清空 channel |
| 8 | 导出诊断 | 含 playwright/patchright 字段，无密钥 |

---

## 4. 发行文案要点

- 本地双引擎；Chromium 可选 Patchright  
- **无** 注册/订阅/支付/反检测 SLA  
- 对标方向 Multilogin/GoLogin 仅为产品北极星，非本包实测证明  
- 第三方：Patchright Apache-2.0（见 `phase-c-packaging.md`）

---

## 5. 本机执行记录

| 项 | 值 |
|---|---|
| 构建日期 | 2026-07-15 |
| 构建机 OS | Windows 11 10.0.26200 / Python 3.12.10 / PyInstaller 6.21.0 |
| 首次 `build.bat` | PyInstaller **成功**；Inno 路径未命中（winget `-q` 冲突已修；ISCC 在 `%LOCALAPPDATA%\Programs\Inno Setup 6`） |
| 首次 Portable | `dist/FoxDesk` **~1.5 GB**（误打入 host `torch` 471M + `jedi` 335M 等） |
| 修复 | `foxdesk.spec` `excludes`；`build.bat` VERSION / winget / CRLF / Inno 用户路径 |
| 重打包 Portable | **~394 MB**（`FoxDesk.exe` ~15.4 MB；无 torch/jedi；playwright+patchright 包约 227 MB） |
| Setup | `installer_output/FoxDesk-1.4.0-dev-Setup.exe` **~69.8 MB**（73226756 bytes） |
| 冒烟 | `FoxDesk.exe --serve 8765` + boot token → `/api/system` **ok**（1.4.0-dev，pw+pr ready） |
| GUI | 直启 `FoxDesk.exe` 时 pythonnet/webview 加载 `Python.Runtime.dll` 失败（已知；serve 路径正常） |
| 备注 | 浏览器二进制仍不捆绑；正式 1.4.0 建议干净 venv + 修 pythonnet collect |
