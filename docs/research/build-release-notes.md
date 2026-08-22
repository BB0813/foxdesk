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

### 2026-08-22 — v1.4.1 发布（CI）

| 项 | 值 |
|---|---|
| Release | https://github.com/BB0813/foxdesk/releases/tag/v1.4.1（CI 全绿：build-windows + bstatic-gate + release） |
| 资产 | `FoxDesk-1.4.1-Setup.exe` ~84 MB / `FoxDesk-windows-x64-1.4.1.zip` ~125 MB / `SHA256SUMS` |
| 本地 `build.bat` | 括号解析 bug 修复后 `[1/6]…[6/6]` 全链路自产 Setup |
| **CI 冻结 serve 限制** | GitHub 无头 runner 上冻结 exe 的 `--serve` 在 `import backend.app` 阶段无限停滞（连令牌文件都不落，疑与无桌面会话的设备枚举有关；非产物缺陷——真实桌面多轮验证通过）。CI 因此只做**源码层** HTTP 中间件断言（ping/421/404）+ 冻结进程级 `--worker` 快败检查；冻结 HTTP/GUI 以桌面实测为准 |
| bstatic 门禁 | CI 新增非阻塞 `bstatic-gate` job：playwright+patchright 装浏览器后跑 `--require-webdriver-false`，2m05s 通过 |

### 2026-07-22 — 安全加固后重打包（对应审计修复）

| 项 | 值 |
|---|---|
| 构建 | `build.bat`：PyInstaller 成功（collect pythonnet=97 binaries / clr_loader=2）；Inno 段静默跳过，**手动 ISCC 编译成功**（~160s） |
| Portable | `dist/FoxDesk`（`FoxDesk.exe` ~17.4 MB，含 pythonnet/clr_loader） |
| Setup | `installer_output/FoxDesk-1.4.0-Setup.exe` **~87.8 MB**（92082356 bytes） |
| 冻结冒烟 | `--serve`：ping / 外来 Host **421** / `/openapi.json` **404** / boot token 鉴权 / 令牌文件 — **全部 PASS** |
| 冻结 GUI | **原生 WebView 窗口修复**：中文路径 + 网络映射盘（`Z:\指纹浏览器` → UNC）与 ASCII 本地路径均 `MainWindowTitle=FoxDesk 1.4.0`、WebView2 子进程 5 个 |
| GUI 根因 | 双重：① netfx 按字节传程序集路径，非 ASCII 路径被按 ANSI 误解码；② 网络盘（IP UNC → Internet 区域）触发 .NET CAS `NotSupportedException` |
| GUI 修法 | `desktop._prepare_frozen_dotnet()`：pythonnet runtime 与 `webview/lib` 镜像到 `%TEMP%\FoxDesk\`（ASCII 本地），重指 `pythonnet.__file__` 与 `webview.util.interop_dll_path`；同盘 ASCII 安装路径零开销直通 |
| 版本回写 | `build.bat` 现已把 VERSION 同步进 `installer.iss`（`1.4.0 / 1.4.0.0`） |

### 2026-07-15 — 1.4.0 首次打包

| 项 | 值 |
|---|---|
| 首次 `build.bat` | PyInstaller **成功**；Inno 路径未命中（winget `-q` 冲突已修；ISCC 在 `%LOCALAPPDATA%\Programs\Inno Setup 6`） |
| 首次 Portable | `dist/FoxDesk` **~1.5 GB**（误打入 host `torch` 471M + `jedi` 335M 等） |
| 修复 | `foxdesk.spec` `excludes`；`build.bat` VERSION / winget / CRLF / Inno 用户路径 |
| 重打包 Portable | **~394 MB**（`FoxDesk.exe` ~15.4 MB；无 torch/jedi；playwright+patchright 包约 227 MB） |
| Setup | 手动 ISCC：`FoxDesk-1.4.0-Setup.exe` ~69.8 MB |
| 冒烟 | `FoxDesk.exe --serve 8765` + boot token → `/api/system` **ok** |
| GUI | pythonnet/`Python.Runtime.dll` 加载失败 → 回退（当时进程直接崩溃，现已优雅回退） |
