# Phase D 差距矩阵（骨架）

**状态**：D0 骨架 · 实测待填  
**主对照**：**Multilogin** · 版本 _待填_  
**备对照**：**GoLogin** · 版本 _待填_  
**场景**：AI 平台正常注册 / 登录 / 订阅（ChatGPT · Claude · Gemini）  
**FoxDesk**：1.4.0-dev · Chromium · `chromium_backend=patchright`（除非另注）  
**原则**：对内记录；**无对外保证**

---

## 1. 环境对齐（跑任何 B-* 前）

| 项 | FoxDesk | Multilogin | GoLogin（可选） | 一致？ |
|---|---|---|---|---|
| 产品版本 | 1.4.0-dev | | | |
| OS / 分辨率 | | | | |
| 代理出口 / 国家 | | | | |
| timezone / locale | | | | |
| 预热剧本版本 | `l3-kpi.md` §3 | 同左 | 同左 | |
| 日期 | | | | |

---

## 2. B-static / 自动化面

| 信号 | Phase C 本机（patchright） | Multilogin | GoLogin | 差距 | D 动作候选 |
|---|---|---|---|---|---|
| `navigator.webdriver` | **false**（`_bstatic_phase_c.json`） | _待测_ | _待测_ | | 维持 / 加固 |
| `window.chrome` | 有（ensure） | | | | |
| UA / 无 Headless | 配置层 OK | | | | |
| UA-CH brands | 偶发缺失（medium） | | | | init / context |
| plugins | 本机非空 | | | | |
| mediaDevices | 策略 random；偶发 0 | | | | hook 加固 |
| fonts.check | pack 有效 | | | | |
| CDP / Runtime 痕迹 | **无泄漏**（CI 2026-08-28：`cdp_console_tostring=true`，patchright） | _待测_ | _待测_ | | 维持 patchright 主路径 |
| iframe 一致性 | **srcdoc 一致**（CI 2026-08-28：`iframe_srcdoc_consistent=true`）· Worker 一致（`worker_consistent=true`） | | | | 已测通过；跨域 iframe 待 B-leak |
| Permissions / Notification | 未系统测 | | | | D |
| WebRTC 真 IP | 软 flags；待 B-webrtc | | | | B+D |

评分栏：`OK` / `GAP` / `UNKNOWN` / `N/A`

---

## 2.5 D1 技术侧基线（Chrome 151 真机 · 2026-08-28）

用 `tools/d1_probe_server.py` 采集的本机 Google Chrome 151.0.7922.175 真值（l3-kpi §1 技术侧基线）：

| 信号 | 真机 Chrome 151 值 | FoxDesk patchright 现状 | 对齐动作 |
|---|---|---|---|
| UA-CH brands | `Not=A?Brand:99 → Google Chrome:151 → Chromium:151`（GREASE 在前） | ~~`Chromium → Not.A/Brand:24 → Google Chrome`（旧格式）~~ | **已修**：init 脚本改为真机格式 |
| UA-CH platformVersion (Windows) | `19.0.0` | ~~`15.0.0`~~ | **已修**：默认 19.0.0 |
| Notification / query | `default` / `prompt`（一致） | D-B3 已内置一致性对齐 | 维持 |
| webdriver | false | false（CI 实测） | 维持 |
| CDP 痕迹 / iframe / Worker | 三探针全净 | 三探针全净（CI 实测） | 维持 |
| plugins | 5 | 本机非空 | 维持 |

> 基线原始 JSON：`docs/research/_d1_chrome-151.json`（gitignored，留存本地）

---

## 3. B-leak（公开指纹页，选 2）

| 站点 | FoxDesk 记录 | 对照机 | 异常 diff | 说明 |
|---|---|---|---|---|
| _待选_ | | | | 仅记录分数/红项 |
| _待选_ | | | | |

---

## 4. B-ai-signup / B-ai-subscribe（仅自有账号 · 官方流程）

平台子集（建议先锁定一个）：_ChatGPT / Claude / Gemini_

### 4.1 注册/登录（B-ai-signup）

| 样本 # | 产品 | 平台 | 结果码 | 备注（验证码/邮件/地区） |
|---|---|---|---|---|
| 1…n | FoxDesk chromium+patchright | | HARD_FAIL / CHALLENGE / INIT_OK / OTHER | |
| 1…n | Multilogin | | | |
| 可选 | GoLogin | | | |

### 4.2 订阅（B-ai-subscribe，可选）

| 样本 # | 产品 | 平台 | 结果码 | 备注（仅自有合法支付） |
|---|---|---|---|---|
| | FoxDesk | | | **禁止**盗卡/绕过 |
| | Multilogin | | | |

### 4.3 汇总（相对 Multilogin）

| 指标 | FoxDesk | Multilogin | GoLogin | Δ (FD−ML) |
|---|---|---|---|---|
| HARD_FAIL 率 | | | | |
| 非 HARD_FAIL 率 | | | | |
| Align（定义见 l3-kpi） | | | | |

---

## 5. 行为与运营面（非纯静态）

| 项 | 状态 | 笔记 |
|---|---|---|
| 预热时长/站点集合 | 草案 | 两引擎必须相同 |
| 冷启动同一 user_data | 待测 | |
| 多开隔离 | Phase A 路径隔离 | 支付场景再压 |
| 跟 Chrome 大版本 | 未建流水线 | D4 |

---

## 6. 根因分层（填完对照后勾）

| 层 | 是否主因 | 证据 |
|---|---|---|
| IP / 代理质量 | | |
| 账号 / 风控历史 | | |
| 静态自动化泄漏 | | |
| 内核/协议指纹 | | |
| 行为时序 | | |
| 配置不一致 | | |

---

## 7. 进入 D3 编码的触发

满足任一条且 D2 选型完成：

- [ ] 相对 **Multilogin** Align &lt; 0.70（或 Δ_HF &gt; +15pt）且业务坚持 L3  
- [ ] 差距集中在 **内核/CDP/协议** 而非纯 IP/邮箱/账号历史  
- [ ] 有编制/时间预算（见 feasibility 人月表）  

未满足 → **维持 Phase C + 配置运营**，本表继续积累样本。

---

## 归档文件（填测后挂）

| 文件 | 含义 |
|---|---|
| `_bstatic_phase_c.json` | C 门禁本机 |
| `_smoke_phase_c_summary.json` | C worker 有头 |
| `_bcompare_*.json` | 待产出 |
