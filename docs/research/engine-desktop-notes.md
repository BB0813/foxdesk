# 引擎桌面调研摘录

**日期**：2026-07-14

## Camoufox

- Firefox fork + Playwright 风格 Python API（`Camoufox` sync/async）。  
- **无** Chromium 模式；指纹/反检测在 Firefox/SpiderMonkey 路径。  
- FoxDesk 现状：`backend/camoufox_worker.py` 强耦合。  
- 参考：项目 README / PyPI `camoufox`（例：0.4.x 系）。

## Playwright Browsers

- 浏览器与 Playwright 版本绑定；`playwright install chromium`。  
- 缓存目录 Windows：`%LOCALAPPDATA%\ms-playwright`（本机已有 `chromium-1124`、`chromium-1228`）。  
- 可用 `PLAYWRIGHT_BROWSERS_PATH` 指到 `%APPDATA%\FoxDesk\browsers` 便于产品化。  
- Headed 与 headless shell 构建分离；支付向必须 **headed**。  
- 文档：https://playwright.dev/python/docs/browsers  

## Patchright

- PyPI：宣称 undetected Playwright，**仅补丁 Chromium**。  
- 安装：`pip install patchright` → `patchright install chromium`。  
- 建议：`channel="chrome"` + persistent context（其 README 实践）。  
- 本机 Phase 0 开始时 **未预装**，需隔离环境评估。  

## 商业指纹浏览器（对照用）

- 典型：改版 Chromium + 深指纹 + 账号/代理一体化。  
- 调研只做 **同代理行为对照**，不做破解/协议盗用。  

## 许可注意

- 捆绑 Chromium（开源）与捆绑 Google Chrome（不可）不同。  
- Patchright/Playwright 发行前核对 LICENSE 与依赖传递。  
