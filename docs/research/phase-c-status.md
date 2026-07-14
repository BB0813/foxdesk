# Phase C 状态板（R3 / L3 入门 — 补丁栈）

**开始**：2026-07-14  
**版本**：FoxDesk **1.4.0-dev**  
**前提**：Phase B 门禁通过（字体/媒体/B-static 配置层）

---

## 目标

- 接入 **Patchright**（或等价）作为 Chromium 自动化后端  
- 降低 `navigator.webdriver` 等常见自动化泄漏（以 B-static 为准）  
- `chromium_backend`: `auto` | `playwright` | `patchright`  
- **不对用户保证**支付/过检；对内记录 B-static / 后续 B-compare  

---

## 交付勾选

| 项 | 状态 |
|---|---|
| `pip install patchright` 本机 | **done**（1.61.2） |
| Playwright 对齐版本 | **done**（1.61.0） |
| `chromium_backend` 档案字段 | **done** |
| `resolve_chromium_backend` / auto→patchright | **done** |
| `chromium_worker` 后端分发 | **done** |
| 单启 + 批量写 resolved backend | **done** |
| UI 后端选择 | **done** |
| `bstatic_probe --backend` + `--require-webdriver-false` | **done** |
| A/B PoC 归档 | **done** `_phase_c_poc_pw.json` / `_phase_c_poc_pr.json` |
| requirements / foxdesk.spec | **done** |
| 单元测试 Phase C | **done**（全量 49 passed） |
| B-static Phase C 门禁归档 | **done** `_bstatic_phase_c.json` |
| Worker 有头冒烟（patchright） | **done** `_smoke_phase_c_summary.json`（ready + webdriver=false） |
| 打包/许可笔记 | **done** `phase-c-packaging.md` |
| Phase C MVP 收口 | **done**（2026-07-14） |
| B-compare 商业对照 | → **Phase D / D1**（需人工环境） |
| 默认安装包捆绑 patchright 浏览器 | pending（体积/跟版；见 packaging） |

---

## 本机 A/B 结果（2026-07-14）

| 后端 | headed probe webdriver | 备注 |
|---|---|---|
| playwright | **true** | 库存自动化栈 |
| patchright | **false** | 本机；不保证全环境/全站点 |

### B-static Phase C 门禁

```bash
python tools/bstatic_probe.py --backend patchright --require-webdriver-false \
  --json-out docs/research/_bstatic_phase_c.json
```

| 项 | 结果 |
|---|---|
| backend | patchright |
| webdriver | **false** |
| phase_b_gate_ok | true |
| phase_c_needed | false（webdriver 已过） |
| high_fail | 无 |
| 备注 | ua_ch / media 偶发 medium/low，不挡 C 门禁；**无支付保证** |

命令：

```bash
python tools/poc_chromium_launch.py --backend playwright --headed --probe
python tools/poc_chromium_launch.py --backend patchright --headed --probe
python tools/bstatic_probe.py --backend auto --require-webdriver-false
```

---

## 许可与分发（R8 摘要）

| 项 | 笔记 |
|---|---|
| Patchright PyPI | 宣称 Apache-2.0（以包内 LICENSE 为准，发版前再核） |
| Google Chrome channel | **不**捆绑；用户本机可选 |
| 默认策略 | `chromium_backend=auto`：有 patchright 用 patchright，否则 playwright |

---

## 明确不做

- 支付通过率 SLA  
- 云控  
- 未授权生产支付打量  
- 宣称已对齐商业 L3（需 B-compare）  

---

## 下一步

1. ~~本机 B-static C 门禁 + worker 有头冒烟~~  
2. ~~Phase C MVP 收口~~ → 进入 **Phase D0**（`phase-d-status.md`）  
3. 有对照机时填 B-compare（D1）  
4. 发正式 1.4.0：Setup 体积、安装包内冒烟、文档版本号  


