# D-B3 / B4 / B5 / B6 / B7 实现与调研记录

**状态**：backlog 收口（除 D-B8 触发条件未满足）· 无商业机依赖项全部落地
**对应 backlog**：`phase-d-engineering-backlog.md`
**原则**：对内记录；**无对外保证**；探针/提示只做测量与风险呈现

---

## D-B6 (P1) — 代理质量提示产品化

**为何 P1**：IP 权重是支付/AI 风控的大头，指纹层无法补偿机房出口 IP。

**实现**：

| 组件 | 内容 |
|---|---|
| `backend/proxy_quality.py` | 出口 IP 分级（`residential` / `datacenter` / `mobile` / `unknown`）。数据源：`https://ipwho.is/{ip}` 主、`https://ipinfo.io/{ip}/json` 备（均为 https 免费无 key）；ASN/org 关键词启发式 |
| `ProxyPoolStore.mark_quality()` | 质量记录落盘（`quality` / `quality_org` / `quality_source` / `quality_checked_at`） |
| `POST /api/proxies/{id}/quality-check` | 代理测试 → 出口 IP 分级 → 存档，返回 test+quality |
| `environment_risks_for_profile` | 绑定池代理后：`datacenter_proxy`（**medium**，机房出口提示换住宅/移动）；`residential_proxy`（**low**，正向信号） |

**偏差设计**：关键词故意偏向漏报（机房误判为住宅会隐藏真实风险；反向只多一条提示）。分级是启发式，**不是 IP 信誉保证**。

---

## D-B5 — channel=chrome 一键建议 + 启动失败可读

- 启动失败可读：Phase C 已有（`humanize_chromium_launch_error`），维持。
- 一键建议（本轮新增）：
  - 风险条目支持 `suggestion` 字段（`chromium_bundled_build` → `"chromium_channel=chrome"`，仅本机检测到 Chrome 时附带）。
  - `POST /api/profiles/{id}/apply-suggestion` `{"code": "chromium_bundled_build"}`：白名单应用（非 chromium 档案 409；未检测到 Chrome 409；未知 code 400）。
- 后续可扩展：UI 指纹检查面板渲染 `suggestion` 字段 + 调用该端点（后端契约已就绪）。

---

## D-B3 — 权限 / Notification 默认面

**检测原理**：真实桌面 Chrome 为 `Notification.permission='default'` + `permissions.query({name:'notifications'}).state='prompt'`；headless Chromium 泄漏 `denied` + `prompt` **不一致**组合，是经典 headless 判据之一。

**实现**（`build_fingerprint_init_script` 内置，无新配置字段）：
- 仅在 `Notification.permission === 'denied'` 时，把 `permissions.query('notifications')` 返回的 `prompt` 状态对齐为 `denied`（消除不一致）。
- **刻意不伪造 `granted`/`default`**：日常浏览档案上覆写用户真实授权会破坏站点行为，也超出"一致性对齐"边界。
- 传感器（加速度计等）：桌面 Chrome 本就默认关闭，无不一致面，不做。

**边界声明**：只修不一致，不承诺过检；跨域 iframe 内权限面未覆盖（同 D-B2 边界，待 D1 数据）。

---

## D-B4 — TLS / HTTP2 / JA3 侧面（可选 B-leak）

**桌面研究结论**：
- 自动化栈（Playwright/Patchright）**不改 TLS**——流量走 Chromium 原生网络栈，JA3/JA4 与同版本真 Chrome 一致。
- 真正的风险面是**版本偏移**：捆绑 Chromium 落后 stable 时，TLS 指纹（版本、扩展、ALPN）随内核版本走 → 与 UA 声称的版本错位。
- headless 特定的 ALPN/扩展序差异偶发，需实测记录。

**工具**：`tools/tls_probe.py`（手动，不入 CI）
- 走 chromium_backend=auto/playwright/patchright 访问 `https://tls.peet.ws/api/all`，记录 `ja3 / ja3_hash / ja4 / akamai_fingerprint_hash / UA`。
- 用法：同机三跑对比 —— `--label plain`（真 Chrome）vs `--label fd-patchright` vs 旧捆绑 Chromium；diff 即版本偏移证据。
- 产物 `docs/research/_tls_leak.json` 已被 gitignore 覆盖。

---

## D-B7 — 跟 Chrome 大版本的跟版流水线

- **UA 池刷新**：原 Chrome 131 → **153/152**（Win/macOS/Linux），Firefox → 154，Safari → 19.2（按 drift check 实测的当前 stable 校准）；bstatic 探针 UA 同步；init 脚本 UA-CH 兜底 major 同步。
- **`tools/chrome_drift_check.py`**：
  - 最新 Chrome stable major（versionhistory.googleapis.com 公开 API）vs 源码内嵌 UA major（自动提取 profiles.py / bstatic_probe.py）；
  - PyPI 最新 playwright/patchright 版本报告（requirements 用 `>=`，风险是大版本兼容而非钉死过期）；
  - 内嵌 major 落后 stable 超过 **2 个大版本** → exit 1（stale）。
- **`.github/workflows/drift-check.yml`**：每月 3 日 03:23 UTC 定时 + 手动 dispatch，失败即通知维护者刷新 UA 池/栈。

---

## 执行清单更新

| 项 | 状态 |
|---|---|
| D-B6 代理质量分级 + 端点 + 风险提示 | done |
| D-B5 suggestion 字段 + 一键应用端点 | done |
| D-B3 Notification/Permissions 一致性对齐 | done（init 脚本内置） |
| D-B4 TLS 研究结论 + tls_probe 工具 | done（工具手动运行） |
| D-B7 UA 池刷新 + drift 检测脚本 + 月度 CI | done |
| D-B1/B2 | done（`d-b1-d-b2-notes.md`） |
| D-B8 自维护补丁内核 | ⛔ 触发条件未满足（by design） |
| D1/D2/D3 | ⛔ 等待 Multilogin 对照（用户环境） |

## 变更

| 日期 | 记事 |
|---|---|
| 2026-08-28 | D-B3/B4/B5/B6/B7 全部收口；backlog 仅剩被阻塞项 |
