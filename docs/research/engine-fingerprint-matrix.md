# 引擎检测面矩阵

**状态**：模板 · 用 PoC / 实机填写  
**关联**：`tools/poc_chromium_launch.py`、`tools/poc_fingerprint_probe.py`

字段以「页面 JS 可读」为准；商业机可用其导出或手工记录。

---

## 1. 环境元数据

| 项 | 值 |
|---|---|
| 日期 | |
| 代理 exit IP | |
| 配置的 timezone | |
| 配置的 locale | |

---

## 2. 矩阵

| 字段 | Camoufox | PW Chromium | Patchright | 商业对照 | 本机 Chrome |
|---|---|---|---|---|---|
| userAgent | | | | | |
| userAgentData.brands (UA-CH) | | | | | |
| platform | | | | | |
| webdriver | | | | | |
| languages | | | | | |
| hardwareConcurrency | | | | | |
| deviceMemory | | | | | |
| maxTouchPoints | | | | | |
| screen w×h×depth | | | | | |
| timezone (Intl) | | | | | |
| WebGL vendor | | | | | |
| WebGL renderer | | | | | |
| WebRTC local candidates | | | | | |
| WebRTC public candidates | | | | | |
| plugins length | | | | | |
| chrome runtime object | | | | | |

---

## 3. 解读提示

| 现象 | 可能含义 |
|---|---|
| webdriver=true | 自动化栈未打补丁 → Phase C 重点 |
| timezone ≠ 代理地区 | 一致性失败 → Phase B |
| WebRTC 出现真实 IP | 防漏失败 → 高优先级 |
| UA-CH 空（Chromium） | 不像真 Chrome → 补 channel 或 CH |

## 4. PoC 预填（Playwright Chromium headless smoke · 2026-07-14）

来源：`docs/research/_poc_smoke_playwright.json`

| 字段 | PW Chromium (headless 默认) |
|---|---|
| userAgent | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)…` |
| webdriver | **True** |
| platform | Win32 |
| languages | ['en-US'] |
| timezone | America/New_York |
| UA-CH brands | None |
| pluginsLength | 0 |
| hasChromeRuntime | False |
| WebGL vendor | Google Inc. (Intel) |
| screen | {'width': 1280, 'height': 720, 'colorDepth': 24, 'availWidth': 1280, 'availHeight': 720} |

**解读**：默认 headless 即暴露 `HeadlessChrome` + `webdriver=true` + 无 chrome runtime → 证明 **R1 裸栈不可作 L3 终点**；支付向 PoC 必须 `--headed`，Phase C 必须处理 webdriver。

## 5. Phase B headed B-static（2026-07-14）

来源：`docs/research/_bstatic_run.json` + `b-static-matrix.md`

| 字段 | PW Chromium headed + Phase B 配置 |
|---|---|
| HeadlessChrome | false |
| webdriver | **false**（本机；不保证全环境） |
| UA-CH | 有 brands + platform=Windows |
| hardwareConcurrency / deviceMemory | 8 / 8 |
| mediaDevices | 5（random 策略） |
| fonts check | Arial/Segoe UI/Times/Helvetica true |
| window.chrome | true |
| pluginsLength | 5 |
| phase_b_gate | **pass 10/10** |

**解读**：配置层（L2）可明显好于裸 headless；自动化隐蔽仍依赖环境与后续 **Phase C** 补丁栈，**不构成支付保证**。

