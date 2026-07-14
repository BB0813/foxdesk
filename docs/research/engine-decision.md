# 引擎与产品定位决议

**日期**：2026-07-14  
**状态**：**已拍板**  
**关联**：`docs/dual-engine-feasibility.md`

---

## 1. 产品定位

| 项 | 决议 |
|---|---|
| **定位代码** | **P-B** |
| **一句话** | FoxDesk 从「Camoufox 本地管理器」升级为 **本地双核指纹环境工作站**（Firefox/Camoufox + Chromium 线） |
| **Chromium 线目标** | 以 **过检质量** 为长期主线，内部对齐商业 Chromium 指纹浏览器（L3） |
| **Camoufox 线** | **保留**；适合隔离/自动化/Firefox 场景；支付向默认引导 Chromium |
| **云控** | **不做** |
| **对外保证过检/支付** | **不做**（无 SLA、无「保证通过」营销） |
| **对内 KPI** | **做**（基准套件 B-* + 与对照机 B-compare） |
| **商业 OEM 内核（R5）** | **默认否决**（除非未来独立商业实体/授权） |

---

## 2. 技术深度

| 项 | 决议 |
|---|---|
| **路线** | **R1 → R2 → R3 → R4（Phase D）** 为**既定主路径**，不是「可选彩蛋」 |
| **Phase D** | **纳入路线图**：当 Phase C（补丁栈）在 B-compare 上仍显著落后对照机时，**默认进入**自研/维护补丁 Chromium 或等价深度方案的立项，而不是停在「尽力配置」 |
| **Phase D 触发** | Phase C 完成后跑冻结 KPI；若对齐度 &lt; 决议阈值（阈值在 `l3-kpi.md` 冻结前用草案），启动 D |
| **Phase D 也可预研并行** | 允许在 Phase C 后期并行预研 R4（补丁源、跟版成本），避免 C 结束才零启动 |
| **进度（2026-07-14）** | Phase C **MVP 收口**；Phase **D0 预研**已开板（`phase-d-status.md`）。B-compare 仍待对照机 |
| **止损** | 仅当 R7（IP 权重）等证明内核投入无效，或编制/合规否决时，书面修订本决议 |

### 阶段与路线映射

| 阶段 | 路线 | 目标层级 |
|---|---|---|
| Phase A | R1 | L1 引擎可达 |
| Phase B | R2 | L2 专业配置 |
| Phase C | R3 | L3 入门（补丁栈） |
| **Phase D** | **R4** | **L3 深度对齐（对标商业）** |
| Phase E | 运营 | 持续跟版与基准 |

---

## 3. 默认工程参数（可被后续 KPI 文档覆盖）

| 参数 | 值 |
|---|---|
| 默认 `engine` | `camoufox`（兼容）；**支付/结账模板默认 `chromium`** |
| Chromium MVP 实现 | Phase A：Playwright Chromium；Phase C：评估 Patchright 等后切换默认 backend |
| 浏览器二进制 | 按需下载 → `%APPDATA%\FoxDesk\browsers` |
| user_data | 按引擎隔离，禁止混用 |
| server 模式 | Phase A/B：仅 camoufox；Chromium server/CDP 另议 |

---

## 4. 文档与产品文案

| 文档 | 动作 |
|---|---|
| `PRODUCT.md` | 更新 Purpose 为双核工作站；Out of scope 保留「不保证过检结果」，删除「永不做深度 Chromium」的暗示 |
| `docs/dual-engine-feasibility.md` | 状态改为定位已锁定 P-B + Phase D 在途 |
| 对外 README | 后续发版时写「Chromium 引擎 / 环境质量改进」，禁止「保证支付」 |

---

## 5. 立即下一步（执行序）

1. **Phase 0 / S2（已启动）**：见 `docs/research/README.md` 与 `phase0-status.md`  
2. **Phase A**：与调研可并行（引擎字段 + chromium_worker 底座）— 待 S3 或单独开工指令  
3. **Phase D 预算意识**：按季度级内核工程预留，不按「功能开关」估期  

---

## 6. 签字栏（会话决议）

| 角色 | 内容 |
|---|---|
| 产品方向 | 用户确认 **P-B** |
| 深度对齐 | 用户确认纳入 **Phase D（R4）** |
| 记录 | 2026-07-14 · FoxDesk 会话写入本文件 |
