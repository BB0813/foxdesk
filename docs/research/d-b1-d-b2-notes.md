# D-B1 / D-B2 桌面调研：CDP 自动化痕迹 与 iframe/Worker 一致性

**状态**：D0 桌面调研完成 · 探针已落地 · **缓解实施待 D1 对照数据**
**对应 backlog**：`phase-d-engineering-backlog.md` D-B1（P1）/ D-B2（P1）
**FoxDesk**：1.4.1+ · Chromium 线 · `chromium_backend=auto`（优先 patchright）
**原则**：对内记录；**无对外保证**；无 Multilogin 实测不宣称对齐

---

## 1. D-B1 — CDP / Runtime 自动化痕迹

### 1.1 检测原理（桌面研究结论）

Playwright / Puppeteer 启动上下文时默认发送两类 CDP 命令：

| 命令 | 泄漏机制 |
|---|---|
| `Runtime.enable` | 使 CDP agent **深度序列化** console 参数：站点脚本 `console.debug(obj)` 且 `obj.toString` 被重写时，`toString` 会被 CDP 序列化器调用（正常 Chrome 不会）→ 稳定判据 |
| `Console.enable` | 控制台消息监听留下同类痕迹面 |

业界通行的检测套件（headless 检测 JS）即采用 "toString trick"：向 `console.debug` 传入重写了 `toString` 的对象并计数。

### 1.2 生态缓解方案对比

| 方案 | 思路 | 成本 | 对 FoxDesk 适用性 |
|---|---|---|---|
| **Patchright**（已集成，Phase C） | 协议层堵漏：hold back `Runtime.enable`，用 isolated execution contexts / `Runtime.addBinding` 替代 | 零（已 done） | **主路径**，维持 |
| fortress / rebrowser 系同类 | 同上，源码级变体 | 中（供应链/跟版） | D2 备选，不重复造 |
| stealth init 脚本 | JS 层伪装 | 低 | **无法**修 CDP 痕迹（协议层问题） |
| 源码级补丁 Chromium（D3/R4） | 编译期移除 | 高 | 仅触发条件满足后 |

### 1.3 FoxDesk 现状与结论

- `chromium_backend=auto` 默认优先 patchright → `Runtime.enable` 痕迹本机已消除（`navigator.webdriver=false` 同源验证）。
- `playwright` 回退仍会带 `Runtime.enable` 泄漏 → `environment_risks_for_profile` 已有 medium 提示（`engine_chromium_playwright`）。
- 运行中 `evaluate`/`screenshot` 走既有 patchright 通道，**不额外**触发 `Runtime.enable`；但 server 模式下外部 Playwright 直连 `ws_endpoint` 时泄漏面由外部客户端决定，文档已注明。
- **结论：D-B1 无需新编码，维持 patchright 主路径 + 测量门禁。**

### 1.4 测量（本次落地）

`tools/bstatic_probe.py` 新增 `probe_deep()`，其中 `cdp_console_tostring` 探针：

- `console.debug`/`console.log` 传入重写 `toString` 的对象，250ms 后计数；
- `hits === 0` → `cdp_runtime_no_leak = True`（无 Runtime.enable 型泄漏）；
- 评分器计入 `cdp_runtime_no_leak`（severity=medium，**不参与 gate**，仅测量）。

---

## 2. D-B2 — iframe / Worker 内 navigator 一致性

### 2.1 检测原理（桌面研究结论）

| 检测面 | 机制 |
|---|---|
| **srcdoc / sandbox iframe** | 已知 Chromium 边界：`Page.addScriptToEvaluateOnNewDocument`（Playwright `add_init_script` 的底层）在 `srcdoc`/`sandbox` iframe 中**不执行**（或部分场景不执行）→ 检测脚本建 srcdoc iframe，用 `iframe.contentWindow.navigator` 与主框对比；若 init 脚本只在主框 patch（实例级/主框 prototype 级），子 realm 出现 **webdriver=true / 插件为空 / UA-CH 缺失** 等不一致 |
| **跨 realm prototype** | 每个 iframe 是独立 realm、独立 `Navigator.prototype`；主框 prototype patch 不传播 |
| **dedicated Worker** | init 脚本**从不**进入 Worker realm；`navigator.userAgent`/`hardwareConcurrency`/`platform` 在 Worker 内是宿主真值。若主框 JS 覆写值与宿主真实值不同 → 检测脚本用 blob Worker 采样对比即穿 |

### 2.2 缓解方案对比

| 方案 | 能修 iframe？ | 能修 Worker？ | 成本 | 备注 |
|---|---|---|---|---|
| 主框实例 patch（当前部分做法） | 否 | 否 | — | 最弱 |
| init 脚本 patch `Navigator.prototype`（当前） | 部分（常规 iframe 可；srcdoc/sandbox 边界不行） | 否 | 低 | 维持 |
| `context.add_init_script`（Playwright 层，当前已用） | 同上 | 否 | 零 | |
| **策略层：只 spoof 宿主能自洽的值** | — | **是** | 低 | Worker 不可达 ⇒ 别在主框伪造 Worker 可采样的宿主真值（hardwareConcurrency/userAgent/platform 建议"留默认或与宿主一致"） |
| CDP `Page.setDocumentContent`/frame 级注入逐 iframe 补 | 是（常规） | 否 | 中 | 需 frame 树遍历，易碎 |
| 源码级补丁（D3） | 是 | 是 | 高 | 触发后才做 |

### 2.3 FoxDesk 现状与结论

- init 脚本（`build_fingerprint_init_script`）patch 的是 `Navigator.prototype` + `navigator` 实例双保险 → 常规同源 iframe（继承主文档后重建 realm 的场景除外）多数已覆盖；**srcdoc/sandbox 边界未知 → 待测**。
- `hardware_concurrency` / `device_memory` / `user_agent` 这类 **Worker 可采样** 的字段，若用户覆写值与宿主不一致，存在 Worker 通道泄漏 → 建议（配置层，低成本）：
  - 在 `environment_risks_for_profile` 增加 **medium/low** 风险提示：`worker_exposed_override`（chromium 引擎 + 覆写了 worker 可采样字段时提示 "Worker scope will report host truth; overrides may be detectable"）。
  - 文档引导：AI/支付场景对 `hardware_concurrency=0`（默认，取宿主真值）比硬编码更稳。
- **结论：D-B2 采取 "测量 + 风险提示" 路线；iframe 逐-frame 注入与 Worker 补丁留待 D1 对照数据证明其必要后，再评估 frame 树遍历方案的成本。**

### 2.4 测量（本次落地）

`probe_deep()` 新增：

- `iframe_srcdoc_consistent`：主框内建 `srcdoc` iframe（隐藏），加载后对比 `webdriver / hardwareConcurrency / userAgent / platform / userAgentData.platform`；全部一致 → `True`。
- `worker_consistent`：blob Worker 上报 `userAgent / hardwareConcurrency / platform`，与主框对比（platform/UA 为强判据）→ 一致 `True`。
- 两者均计入评分器（severity=medium，**不参与 gate**）。

---

## 3. 执行清单（本调研产出）

| 项 | 状态 |
|---|---|
| D-B1 桌面调研 + 方案对比 | done（本文档） |
| D-B2 桌面调研 + 方案对比 | done（本文档） |
| `probe_deep()` 三个探针落地 `tools/bstatic_probe.py` | done |
| 评分器接入（medium，不 gate） | done |
| 本机跑探针，回填 gap-matrix 第 2 节 CDP / iframe 两行 | pending（需 headed 环境） |
| `environment_risks_for_profile` 增加 worker 可采样字段覆写提示 | pending（小改动，可与下轮迭代） |
| D1 对照（Multilogin 同探针并排） | pending（用户环境） |

## 4. 明确不做

- 不宣称修好 srcdoc iframe / Worker 泄漏（探针只测量）
- 不为过检目的添加攻击性规避；不承诺任何通过率
- 不在无 D1 数据时启动 frame 树遍历注入或源码级补丁

## 变更

| 日期 | 记事 |
|---|---|
| 2026-08-28 | 初稿：桌面调研 + 探针落地（D-B1/D-B2），缓解路线定为 patchright 维持 + 配置层提示 |
