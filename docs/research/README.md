# FoxDesk 调研索引

**状态**：Phase C MVP **已收口** · Phase D0 **预研中**  
**定位**：P-B + R1→R4（见 `engine-decision.md`）  
**版本**：1.4.0-dev · **开始**：2026-07-14

## 阶段状态

| 阶段 | 文档 | 状态 |
|---|---|---|
| Phase 0 | [phase0-status.md](./phase0-status.md) | 历史 |
| Phase A | smoke `_smoke_headed_summary.json` | done |
| Phase B | [phase-b-status.md](./phase-b-status.md) | done |
| Phase C | [phase-c-status.md](./phase-c-status.md) · [phase-c-packaging.md](./phase-c-packaging.md) | **MVP closed** |
| Phase D | [phase-d-status.md](./phase-d-status.md) · [phase-d-gap-matrix.md](./phase-d-gap-matrix.md) | **D0 in progress** |

## 文档

| 文件 | 内容 |
|---|---|
| [engine-decision.md](./engine-decision.md) | 产品/技术拍板（P-B、R1→R4） |
| [l3-kpi.md](./l3-kpi.md) | L3 内部 KPI 草案与冻结流程 |
| [baseline-camoufox-vs-commercial.md](./baseline-camoufox-vs-commercial.md) | 对照基线实验设计与结果表（待填） |
| [engine-fingerprint-matrix.md](./engine-fingerprint-matrix.md) | 检测面矩阵模板 |
| [b-static-matrix.md](./b-static-matrix.md) | B-static 检测面 |
| [patch-stack-eval.md](./patch-stack-eval.md) | Playwright / Patchright / channel=chrome 评估 |
| [engine-desktop-notes.md](./engine-desktop-notes.md) | 桌面调研摘录与链接 |
| [phase-d-gap-matrix.md](./phase-d-gap-matrix.md) | D 差距清单（对照后填） |
| [ai-platform-runbook.md](./ai-platform-runbook.md) | AI 注册/订阅实验手册（可选对照） |
| [phase-d-engineering-backlog.md](./phase-d-engineering-backlog.md) | D 工程 backlog（无商业机也可迭代） |

## 工具

| 路径 | 内容 |
|---|---|
| `tools/poc_chromium_launch.py` | Chromium 最小启动 PoC |
| `tools/poc_fingerprint_probe.py` | 页面内指纹字段采集 |
| `tools/bstatic_probe.py` | B-static 门禁（含 Phase C webdriver） |
| `tools/smoke_phase_a_headed.py` | Phase A 有头冒烟 |
| `tools/smoke_phase_c_headed.py` | Phase C worker + patchright 有头冒烟 |

## 总册

- `docs/dual-engine-feasibility.md` — 可行性 + 调研总方案  
- `PRODUCT.md` — P-B 产品定位  

## 当前执行序（Phase D0 → D1）

1. 读 `phase-d-status.md` / `l3-kpi.md` §0（场景）与 §1（Multilogin/GoLogin）  
2. 安装 Multilogin（+ 可选 GoLogin），写版本号  
3. 按 `ai-platform-runbook.md`：B-static 并排 → 单平台 B-ai-signup  
4. 用相对 Multilogin 的 Align / Δ_HF 决定维持 C 或 D2 选型（**再**谈内核编码）
