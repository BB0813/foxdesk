# Phase D 状态板（R4 / L3 深度对齐预研）

**开始**：2026-07-14  
**版本**：FoxDesk **1.4.0-dev**  
**前提**：Phase C MVP 完成（Patchright / `chromium_backend` / B-static C 门禁）  
**原则**：对内 KPI；**对外不做过检/注册/订阅保证**；无云控；无未授权滥用打量

---

## 目标场景与对照（用户确认 · 2026-07-14）

| 项 | 决议 |
|---|---|
| 用户对比对象 | **Multilogin**（主）、**GoLogin**（备） |
| 用途 | 正常注册 / 使用 / 订阅 **ChatGPT · Claude · Gemini** 等（自有账号） |
| 对内度量 | B-static → B-ai-signup → 可选 B-ai-subscribe；相对 Multilogin 算 Align |
| 对外 | **不保证** 注册成功、不保证订阅通过、不保证对齐 Multilogin |

---

## 为何启动 D（预研）

| 来源 | 内容 |
|---|---|
| 产品拍板 | P-B + R1→R4；D 为既定深度而非彩蛋（`engine-decision.md`） |
| Phase C 结果 | 本机 Patchright 可使 `navigator.webdriver=false`；**不等于** Multilogin 级环境 |
| 门禁逻辑 | 相对 Multilogin 若 Align &lt; 0.70 或 Δ_HF &gt; +15pt → **立项 D 实现**（`l3-kpi.md` 草案） |
| 当前 | 产品族已定；**具体版本与实测未做** → **D0 预研**；不立刻自研内核编码 |

---

## 阶段切分

| 子阶段 | 目标 | 状态 |
|---|---|---|
| **D0** 预研 | 差距矩阵、候选技术、成本、门禁、不做清单 | **in progress** |
| **D1** 对照 | 有商业对照机时跑 B-compare / B-static 并排 | pending（人工环境） |
| **D2** 选型 | 补丁 Chromium / rebrowser 系 / 采购组件 / 维持 C+配置 | pending |
| **D3** 实现 | 选定路径编码 + 回归流水线 | blocked on D1/D2 |
| **D4** 运营 | 跟 Chrome 发版、检测站变更、本地失败样本（脱敏） | later（≈ Phase E） |

---

## D0 交付勾选

| 项 | 状态 |
|---|---|
| 本状态板 | **done** |
| 差距矩阵骨架 `phase-d-gap-matrix.md` | **done** |
| 与 `l3-kpi.md` / B-* 对齐说明 | **done**（见下） |
| 工程 backlog `phase-d-engineering-backlog.md` | **done** |
| 候选栈桌面评估（不装危险载荷） | partial（backlog D-B*） |
| 对照产品族锁定 Multilogin / GoLogin | **done**（版本号 pending） |
| 场景锁定 AI 注册/订阅 | **done**（`l3-kpi.md` §0） |
| Multilogin/GoLogin 安装版本号 | pending（用户环境） |
| B-compare / B-ai-signup 实测 | pending |
| 内核/补丁编码 | **未开始**（等 D1 触发） |

---

## 与 KPI 的关系

| 里程碑 | 草案阈值 | Phase D 含义 |
|---|---|---|
| Phase C 结束 | Align ≥ 0.70 或 Δ_HF ≤ +15pt | 达则 **可不强推 D3**；仍可做 D0/D1 监控 |
| Phase D 目标 | Align ≥ 0.85 或 Δ_HF ≤ +5pt | D3 验收方向 |
| B-static / webdriver | C 已能在本机 false | D 关注更深泄漏面 + **AI 注册/订阅分类** |

> 阈值仍是草案；T1 实测后写入「已冻结」。

---

## 候选技术方向（评估用，未选型）

| ID | 方向 | 粗成本 | 风险 |
|---|---|---|---|
| D-A | 深挖 Patchright + channel=chrome + 配置层 | 低 | 可能仍远弱于商业 |
| D-B | rebrowser / 同类社区补丁栈升级 | 中 | 供应链、跟版、许可 |
| D-C | 自维护补丁 Chromium / CDP 面 | 高（季度+） | 人力与安全边界 |
| D-D | 采购/OEM 引擎组件 | 商务 | 已倾向否决纯 OEM 绑死（见既有决议） |

选型在 **D2**，需 B-compare 数据，禁止空喊「对齐商业」。

---

## 检测面（D 重点，相对 C）

见 `phase-d-gap-matrix.md`。摘要：

- CDP / Runtime.enable 类自动化痕迹  
- iframe / 跨框一致性  
- 权限与通知、传感器、电池等次要面  
- TLS / HTTP2 指纹（若纳入 B-leak）  
- 行为时序与预热剧本（非纯静态）  
- AI 场景：HARD_FAIL / CHALLENGE / INIT_OK / OTHER（仅自有账号与官方流程）

---

## 明确不做

- 对外注册/订阅/支付通过率 SLA  
- 绕过 AI 平台风控的 exploit、批量撞号、未授权自动化滥用  
- 盗卡/支付通道攻击  
- 云控、包内密钥  
- 无 Multilogin 实测时宣称「已对齐 Multilogin」  
- 把 D3 内核工作伪装成「配置开关」估期  

---

## 工具与文档入口

| 路径 | 用途 |
|---|---|
| `docs/research/phase-d-gap-matrix.md` | 差距清单 |
| `docs/research/l3-kpi.md` | B-* 与 Align |
| `docs/research/b-static-matrix.md` | 静态检测面 |
| `docs/research/phase-c-status.md` | C 完成基线 |
| `tools/bstatic_probe.py` | 静态门禁 |
| `tools/smoke_phase_c_headed.py` | C worker 有头冒烟 |

---

## 下一步（执行序）

1. 安装 **Multilogin**（主）与可选 **GoLogin**（备），记下**精确版本**写入 KPI §1  
2. 固定代理（尽量住宅）+ 同一 timezone/locale  
3. 同剧本 B-static 并排（FoxDesk patchright vs Multilogin）→ `phase-d-gap-matrix`  
4. 选 **一个** AI 平台先跑 B-ai-signup（建议先 ChatGPT 或 Claude 其一），n 小样本即可试剧本  
5. 需要时再 B-ai-subscribe（仅自有支付）；算 Align / Δ_HF  
6. 决定 **维持 C + 配置** 或 **D2 选型**；仅 D2 后开 D3 编码  

---

## 变更日志

| 日期 | 记事 |
|---|---|
| 2026-07-14 | D0 开板；C 收尾并行 |
| 2026-07-14 | 锁定对照 Multilogin/GoLogin；场景 AI 注册/订阅 |
