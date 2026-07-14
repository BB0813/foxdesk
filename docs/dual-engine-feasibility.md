# FoxDesk 双引擎与「商业 Chromium 过检对齐」可行性 / 调研方案

**状态**：方案文档 · **定位已锁定**（见 `docs/research/engine-decision.md`）  
**版本锚点**：FoxDesk **1.4.0-dev** 代码基线（Phase A 已落地）  
**日期**：2026-07-14  
**已拍板**：**P-B**（本地双核指纹环境工作站）+ 路线含 **Phase D / R4**（深度对齐商业 Chromium 过检，对内 KPI，对外不保证）。

---

## 0. 目标分层（必须先对齐语言）

用户确认后的目标可以拆成三层，避免「做了双引擎却仍过不了」的预期落差：

| 层级 | 含义 | 是否当前已确认 |
|---|---|---|
| **L1 引擎可达** | 档案可选 Firefox(Camoufox) / Chromium，生命周期完整 | 隐含需要 |
| **L2 配置专业** | 代理/时区/语言/WebRTC/UA-CH/WebGL 等可配、可检测、可模板化 | 需要 |
| **L3 过检对齐** | 在目标站点/支付链路上，通过率**接近**主流商业 Chromium 指纹浏览器 | **是，已确认为目标** |

**关键区分**

| 说法 | 可否作为内部目标 | 可否作为对外承诺 |
|---|---|---|
| 「对齐商业 Chromium 过检率」 | **可以**（研发 KPI / 基准测试） | **不建议写成保证**（站点策略日更、IP/账号权重极大） |
| 「保证过某站支付」 | 否 | **否**（PRODUCT 原边界；法律与信誉风险） |

本方案把 **L3 作为产品研发目标（aspirational + measurable）**，同时保留对外 **「尽力 / 无担保」** 表述，除非日后单独做 SLA 产品线。

现有 `PRODUCT.md` 写有 *Out of scope: Guaranteed anti-detect outcomes*。若 L3 升级为正式产品主线，需要 **产品决议**：

- ~~P-A~~：主线仍是本地管理器…  
- **P-B（已选）**：本地双核指纹环境工作站，Chromium 线以过检质量为长期主线；**Phase D（R4）在路线图内**，非可选彩蛋。

下文按 **P-B + Phase D** 写投入与路线。决议正文：`docs/research/engine-decision.md`。

---

## 1. 现实差距：商业方案到底强在哪

商业 Chromium 指纹浏览器（各类「指纹浏览器 / 环境隔离」产品）通常不是「Playwright 开个 Chromium + 改 UA」，而是多层叠加：

| 能力层 | 商业常见做法 | 裸 Playwright Chromium | Camoufox（现网） |
|---|---|---|---|
| 浏览器内核 | 改过的 Chromium / Chrome 分支，长期跟版本 | 官方测试构建，自动化特征多 | **Firefox 魔改**，支付栈常不利 |
| 指纹注入深度 | JS 引擎 / 网络栈 / 字体 / WebGL / Audio / Canvas / Client Hints / 整流 | 上下文参数 + 有限 init script，**易被一致性检测** | 深（但在 Firefox 族） |
| 自动化隐蔽 | 去 webdriver、补丁 CDP/运行时泄漏 | 默认暴露自动化面 | 相对好（非 CDP 主路径） |
| 环境一致性 | IP 库 + 时区语言时区一键、WebRTC 策略、字体列表按 OS | 需自建 | geoip 等有一定支持 |
| 档案体系 | Cookie / 书签 / 扩展 / 预热 / 团队云（可选） | 自建 | 本地已有一部分 |
| 过检工程 | 专门对抗团队、版本跟随检测站 | 无 | 无（开源社区节奏） |

**结论（可行性总判）**

| 命题 | 判定 |
|---|---|
| 只加 Playwright Chromium 切换，就能对齐商业过检 | **不可行** |
| 在「管理器 + 外挂 Chromium 栈」上做到 **明显好于裸自动化、接近中端商业** | **困难但可行**（数月级 + 持续跟版本） |
| 短期（数周）对齐头部商业产品支付通过率 | **不可行** |
| 自研/维护补丁 Chromium 长期跟主线 | **可行，成本接近再做一个浏览器产品** |

因此：L3 不是「双引擎功能开关」，而是 **Chromium 反检测引擎产品线**；FoxDesk GUI 仍是控制面。

---

## 2. 技术路线谱系（按逼近 L3 的程度）

### 2.1 路线总览

```text
过检潜力（示意）     低 ──────────────────────────── 高
投入/风险            低 ──────────────────────────── 高

R0  仅 Camoufox（现状）
R1  Playwright Chromium 管理接通（L1）
R2  Playwright/Patchright + 深指纹配置 + 一致性引擎（L2 → 弱 L3）
R3  基于社区「undetected / rebrowser / patchright」等补丁栈 assembles（中 L3）
R4  自建或采购 Chromium 补丁分支 + 指纹驱动（强 L3，真·对齐商业）
R5  嵌入/OEM 商业内核（过检高，开源定位与授权冲突 → 默认否决）
```

### 2.2 各路线可行性

| 路线 | 说明 | L3 可达性 | 开源/合规 | 推荐 |
|---|---|---|---|---|
| **R1** | 档案 `engine` + 官方 Playwright Chromium | 低 | 好 | **必做底座**，不是终点 |
| **R2** | R1 + 完整指纹模型 + 启动前一致性校验 + 支付模板 | 低–中 | 好 | L2 主力 |
| **R3** | Patchright / rebrowser-patches / 类似 CDP 修补 + 持久化 + 真 Chrome channel | 中 | 需逐个审 LICENSE、供应链 | **L3 务实起点** |
| **R4** | 维护 fork 或私有补丁 Chromium，指纹在 C++/Blink 层 | 中–高 | 自研可控、成本极高 | **要对齐头部时必谈** |
| **R5** | 商业 OEM | 高 | 授权 $、闭源 | 与当前仓库定位冲突，单列商业版再说 |

**修订后的推荐策略（目标含 L3）**

1. **立即**：把 L3 写进产品目标，但交付仍分里程碑（不能一次 PR 完成）。  
2. **工程主线**：`R1 → R2 → R3`，用**基准测试**决定是否上 R4。  
3. **默认否决 R5**（除非单独商业实体/授权）。  
4. Camoufox **保留**为 Firefox 引擎线（爬虫/隔离/已有用户），支付向默认引导 **Chromium 引擎**。

---

## 3. 可行性方案（升级版）

### 3.1 产品成功标准（可度量，非口头）

建立 **内部基准套件**（Benchmark Suite），而不是「感觉过了」：

| 基准 ID | 类型 | 用途 |
|---|---|---|
| B-static | 静态页：webdriver、UA-CH、permissions、plugins | 回归自动化特征 |
| B-webrtc | WebRTC 是否漏真实 IP | 代理场景硬指标 |
| B-creep / B-leak | 公开指纹页评分（自选 2–3 个稳定站） | 版本间对比 |
| B-pay-sandbox | **自有或官方测试收银台** / 沙箱商户（合法） | 是否出现 3DS/挑战 vs 直接拒 |
| B-compare | 同 IP、同档案策略下 vs 指定对照商业浏览器 | **对齐度 KPI** |

**L3 内部 KPI 草案（需调研后冻结数字）**

- 在 **固定代理池 + 固定预热剧本** 下，B-pay-sandbox「进入验证/成功初始化支付」率  
  - 目标：≥ 对照商业浏览器的 **X%**（建议调研后定 X=70/85，不在未测前拍脑门）  
- B-static 关键项与对照机差异列表可解释、可工单化  
- 大版本 Chromium 升级后 **7 天内** 恢复基准不低于前一版的 90%

对外文案仍用：改进环境一致性与 Chromium 兼容；**不**写「保证支付成功」。

### 3.2 架构（控制面 vs 引擎面）

```text
┌──────────────── FoxDesk Control Plane（现有强化）──────────────┐
│ Profiles · Proxy · Backup · Update · Risks · Benchmark runner  │
│ engine = camoufox | chromium(-stack)                           │
└───────────────┬─────────────────────────────┬─────────────────┘
                │                             │
       camoufox_worker                 chromium_stack
       (Firefox L2 维持)               ┌──────────────────────┐
                                       │ Driver: Playwright / │
                                       │ Patchright / 自研 CD P│
                                       │ Fingerprint service  │
                                       │ Browser binary channel│
                                       │ (Chrome/Chromium fork)│
                                       └──────────────────────┘
```

**档案模型扩展（L3 向）**

```text
engine: camoufox | chromium
chromium_backend: playwright | patchright | custom   # 高级/隐藏项，默认随版本
fingerprint_profile: { ua, ua_ch, platform, ... }    # 与引擎解耦的指纹文档
consistency_policy: strict | normal                  # 启动拦截不一致
seed / noise: canvas/audio/webgl 策略
```

`user_data_dir` **按引擎强隔离**；支付向模板默认 `engine=chromium`。

### 3.3 分阶段交付（对齐 L3 的真路线）

#### Phase A — 底座（原 Phase 1，约 2–3 周）

- `engine` 切换、chromium 启停、代理/时区/语言、控制通道子集  
- 按需下载浏览器、目录隔离  
- **验收**：L1 完成；基准框架空跑  

#### Phase B — 专业配置与一致性（原 Phase 2，约 3–5 周）

- 完整 Chromium 指纹字段 + UA-CH  
- WebRTC 策略、字体/屏幕、启动前 `environment_risks` **可拦截**（严格模式）  
- 支付模板、预热 checklist  
- **验收**：L2；B-static/B-webrtc 达标；支付仍可能差商业一截  

#### Phase C — 反自动化补丁栈（L3 入门，约 4–8 周）

- 评估并接入 **Patchright 或同等**；优先 `channel=chrome` + persistent  
- 消除/降低 webdriver、典型 CDP 泄漏（以基准为准）  
- 与商业对照机跑 B-compare  
- **验收**：B-pay-sandbox 相对 Phase B **显著提升**；记录与对照机的剩余差距  

#### Phase D — 深度对齐（L3 主力，季度级）

- 若 Phase C 仍明显落后对照机 → 立项 **R4**：补丁 Chromium / 采购引擎组件  
- 指纹在实现层注入、跟 Chrome 发版节奏  
- 专门「支付环境」回归流水线  
- **验收**：内部 KPI 达到决议中的 X% 对齐度  

#### Phase E — 运营化（持续）

- 检测站变更监控、引擎热更新、失败样本库（本地、脱敏）  
- 文档：过检是概率工程，IP/账号/行为权重大  

### 3.4 工作量与团队（L3 诚实估算）

| 范围 | 人月（约） | 说明 |
|---|---|---|
| Phase A | 0.5–1 | 现有团队可做 |
| Phase B | 1–1.5 | 含测试与 UI |
| Phase C | 1.5–3 | 依赖补丁栈稳定性 |
| Phase D | 3–12+ | 等同小型浏览器安全团队 |
| 持续跟版本 | 0.25–1 / 月 | 检测对抗有折旧 |

**单人兼职「几个周末对齐商业过检」：不可行。**

### 3.5 与现行 PRODUCT 边界的冲突处理

| 原边界 | L3 目标下的处理 |
|---|---|
| Guaranteed anti-detect outcomes | 改为：**不对用户保证**；**对内有基准 KPI** |
| 无云控 | 保持；基准与指纹库本地 |
| 不嵌 Token | 保持 |
| 成功 = 管配置不写脚本 | 成功定义扩展为：**管配置 + Chromium 环境质量可度量** |

建议同步改 `PRODUCT.md` 的 Purpose / Out of scope 文案（待你拍板 P-A vs P-B 后改代码仓产品文档）。

### 3.6 法律与伦理（必须写进方案）

- 工具用于 **本人账户、授权测试、兼容性验证** 与用于欺诈的边界由用户自负；产品不做「绕过银行风控教程」。  
- 基准测试仅使用 **自有沙箱、公开检测页、授权环境**。  
- 不实现针对特定支付机构的专用 bypass exploit。  
- L3 优化方向是 **环境一致性与减少虚假自动化指纹**，不是攻击支付协议。

---

## 4. 调研方案（服务 L3，不只服务「能不能开 Chromium」）

### 4.1 调研目标

1. 量化 **现状 Camoufox vs 对照商业 Chromium 浏览器** 在相同代理下的差距  
2. 量化 **R1/R2/R3** 每跃迁的收益，决定是否砸 R4  
3. 选定 Chromium 补丁栈与发版策略  
4. 冻结内部 KPI（X%）与对照产品名单  

### 4.2 对照物选择（调研时定 1 主 + 1 备）

| 类型 | 作用 |
|---|---|
| 用户口中的「正常指纹浏览器」 | 主对照（需可复现版本号） |
| 另一主流商业 Chromium 指纹浏览器 | 防单一对照偏差 |
| 本机 Chrome 手动 + 同代理 | 上界参考（非指纹浏览器） |
| 裸 Playwright Chromium | 下界参考 |

### 4.3 必答问题（升级）

| # | 问题 | 方法 | 决策用途 |
|---|---|---|---|
| R1 | 同代理下 Camoufox vs 商业机：支付是「直接拒」还是「挑战失败」 | 沙箱支付 / 可重复剧本 | 确认内核族是否主因 |
| R2 | 商业机关闭「高级指纹」只留 Chromium 时是否仍过 | 对照机设置对照 | 判断要 R3 还是 R4 |
| R3 | Playwright vs Patchright vs channel=chrome 的 B-static 差异 | PoC | 选 Phase C 后端 |
| R4 | WebRTC / 时区 / UA-CH 不一致是否单独导致直接拒 | 单变量实验 | Phase B 优先级 |
| R5 | 商业方案是否依赖自定义扩展 / 字体包 / 内核小版本 | 目录与进程观察（合法） | R4 范围 |
| R6 | 持久化档案预热（登录浏览 24h）对支付的影响幅度 | A/B | 产品是否强引导预热 |
| R7 | IP 类型（住宅/机房/手机）权重大于指纹的程度 | 同浏览器换 IP | 避免只卷指纹 |
| R8 | 补丁栈 LICENSE 与 PyInstaller 分发合规 | 法务级阅读 | 能否进安装包 |
| R9 | 跟 Chrome 发版：补丁滞后是否导致过检断崖 | 版本矩阵 | 维护编制 |
| R10 | 用户可接受的安装体积与首次下载时间 | 问卷/自己计量 | P1/P2 打包 |
| R11 | 开源仓库公开「对齐商业过检」是否带来滥用与下架风险 | 政策评估 | 文档与功能暴露度 |
| R12 | 若 L3 失败，产品是否接受「仅 L2 + 诚实文案」 | 决策 | 止损线 |

### 4.4 调研任务与交付物

| 任务 | 交付物 | 预计 |
|---|---|---|
| T0 目标签字 | 本文件目标层 + P-A/P-B 决议 | 0.5d |
| T1 对照基线实验 | `docs/research/baseline-camoufox-vs-commercial.md` | 2–4d |
| T2 Chromium 栈 PoC | `tools/poc_chromium_*.py` + 矩阵 | 2–3d |
| T3 补丁栈评估 | `docs/research/patch-stack-eval.md`（Patchright 等） | 2d |
| T4 KPI 冻结 | `docs/research/l3-kpi.md`（X%、剧本、代理规格） | 1d |
| T5 路线决策 | `docs/research/engine-decision.md`：R3 止步 or 启动 R4 | 1d |
| T6 产品文档修订草案 | PRODUCT/README 定位补丁（先草案不落库也可） | 0.5d |

### 4.5 进入各 Phase 的门禁

| 进入 | 条件 |
|---|---|
| Phase A 编码 | T0 完成；默认引擎与目录隔离方案批准 |
| Phase B | Phase A 稳定；R4/R7 初步结论 |
| Phase C | T3 许可通过；B-static 显示 R1 不足 |
| Phase D（R4） | Phase C 后 B-compare **仍显著落后** 且业务坚持 L3；有编制预算 |
| **止损** | R7 证明纯 IP 问题 → 优先代理产品而不是内核；或 R11 否决公开 L3 |

### 4.6 调研期明确不做

- 逆向破解商业浏览器授权/云协议  
- 针对特定银行/卡组的攻击性绕过  
- 未授权对第三方生产支付打量  

---

## 5. 与「只做双引擎切换」旧方案的差异

| 项 | 旧方案（L1 中心） | 本方案（含 L3） |
|---|---|---|
| 成功标准 | 能切换启动 | 基准接近商业对照 |
| Playwright Chromium | 终点候选 | **仅底座** |
| Patchright 等 | 可选调研 | **L3 关键路径** |
| 自研内核 | 几乎不提 | Phase D 候选 |
| 工期 | 数周 | **数月～持续** |
| 对外保证 | 无 | 仍无；对内有 KPI |
| 支付模板 | 配置建议 | 配置 + 引擎默认 chromium + 基准 |

---

## 6. 决议状态（已拍板）

| # | 项 | 状态 |
|---|---|---|
| 1 | 定位 **P-B** 双核指纹工作站 | **已确认** |
| 2 | 对外无担保 / 对内 B-* KPI | **已确认** |
| 3 | 技术 **R1→R2→R3→R4（Phase D）** | **已确认**（D 为既定深度，非可有可无） |
| 4 | Camoufox 保留；支付模板默认 Chromium | **已确认** |
| 5 | 不做 R5 OEM（默认） | **已确认** |
| 6 | 下一步 Phase 0（S2） | **已启动**（`docs/research/`） |

详见 `docs/research/engine-decision.md`。

---

## 7. 下一步行动选项

| 选项 | 内容 |
|---|---|
| **S1** | 仅锁定文档（当前） |
| **S2（推荐）** | 启动 Phase 0：基线对照 + PoC + `l3-kpi.md` 草案 |
| **S3** | Phase 0 与 Phase A（引擎切换编码）并行 |
| **S4** | PRODUCT 已随 P-B 修订；可再补 README 发版说明 |

---

## 附录 A — 现状代码锚点

| 区域 | 路径 |
|---|---|
| Profile | `backend/app.py` `ProfileIn` |
| 启动 / risks | `launch_session` / `environment_risks_for_profile` |
| Worker | `backend/camoufox_worker.py` |
| 控制通道 | `backend/session_control.py` |
| 支付向模板（配置级） | `backend/templates_data.py` `payment-checkout` |
| 产品边界 | `PRODUCT.md` Out of scope |

## 附录 B — 术语

| 术语 | 含义 |
|---|---|
| L1/L2/L3 | 引擎可达 / 专业配置 / 过检对齐 |
| 对照机 | 用于 B-compare 的商业 Chromium 指纹浏览器 |
| R1–R5 | 技术路线强度 |
| 基准套件 | 可重复、可回归的检测与沙箱剧本 |
