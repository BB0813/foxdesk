# Phase 0 状态板（S2）

**开始**：2026-07-14  
**目标**：完成调研门禁，再开 Phase A 编码  

---

## 交付物勾选

| 交付物 | 状态 |
|---|---|
| `engine-decision.md`（P-B + Phase D） | **done** |
| `l3-kpi.md` 草案 | **done**（未冻结数字） |
| `baseline-camoufox-vs-commercial.md` 设计 | **done** · 结果 **pending** |
| `engine-fingerprint-matrix.md` 模板 | **done** · 数据 **pending** |
| `patch-stack-eval.md` 初稿 | **done** · 实机 B **pending** |
| `engine-desktop-notes.md` | **done** |
| `tools/poc_chromium_launch.py` | **done** |
| `tools/poc_fingerprint_probe.py` | **done** |
| PoC smoke 本机跑通 | **done**（headless；见运行记录） |
| `l3-kpi` 阈值冻结 | pending |
| 对照商业机实测填表 | pending（需你的对照环境） |

---

## 本机环境快照

| 项 | 值 |
|---|---|
| playwright | 1.45.0 |
| patchright | 未安装 |
| ms-playwright chromium | chromium-1124, chromium-1228 存在 |
| camoufox | 已安装 |

---

## 门禁（进 Phase A）

来自 `dual-engine-feasibility.md` / 决议：

- [x] T0 定位签字（P-B + Phase D）  
- [x] PoC 脚本就绪  
- [x] R1 PoC smoke 一次通过（50 次压测 optional）  
- [ ] R3/R5/R8 补丁栈与许可（patchright 可选后置，不挡 A）  
- [x] user_data 隔离方案书面确认（决议已有约定；Phase A 校验路径 marker）  
- [x] 默认 engine=camoufox、支付模板 chromium 文案确认  
- [x] chromium MVP 不做 server 确认  

**说明**：对照商业机填表（T1）对 **Phase C/D KPI** 关键，**不阻塞** Phase A 底座编码；但阻塞「宣称 L3 进度」。

---

## Phase A 编码进度（2026-07-14）

| 项 | 状态 |
|---|---|
| `Profile.engine` / `chromium_channel` | **done** |
| `chromium_worker.py` | **done** |
| `launch_session` + `batch_launch` 按 engine 路由 | **done** |
| `desktop.py` frozen worker 分发 | **done** |
| UI engine / channel | **done** |
| 支付模板 camoufox + chromium 实验 | **done** |
| 单元测试 engine 路由 | **done** |
| 实机有头 Chromium 会话冒烟 | **done**（`tools/smoke_phase_a_headed.py`） |
| L3 / 商业对齐 | **out of Phase A**（Phase D） |

**后续**：版本 **1.4.0-dev**；**Phase B 已启动** → `phase-b-status.md`

---

## 运行记录

| 时间 | 命令 | 结果 |
|---|---|---|
| 2026-07-14 | `python tools/poc_chromium_launch.py --probe` | **ok** headless；webdriver=true；UA=HeadlessChrome/127；elapsed 2.2s |
| 2026-07-14 | Phase A 代码落地（engine 字段 / worker / UI） | **in tree**（未 tag） |

---

## 下一步建议

1. 本机：`playwright install chromium` 后启动一个 chromium 档案做有头冒烟  
2. 用支付向 Camoufox 档案填 baseline B001  
3. 有对照机时填 B002  
4. 可选：venv 装 patchright 做 A/B（Phase B+）  
5. Phase A 收口后进 Phase B（指纹对齐补丁，非 L3 终点）  
