# L3 内部 KPI 草案

**状态**：草案（对照机产品族已锁定；具体版本/T1 未冻结）  
**原则**：对内可度量；**对外不做过检/注册/订阅通过率保证**  
**进度**：Phase C 本机 B-static webdriver 门禁已绿；对照产品族已定 → 见 `phase-d-status.md`

---

## 0. 目标场景（用户确认）

| 项 | 决议 |
|---|---|
| 用户会对比的产品 | **Multilogin**（主）、**GoLogin**（备） |
| 实际用途 | **正常**注册与订阅 **ChatGPT / Claude / Gemini** 等 AI 平台（自有账号、合规流程） |
| 不是 | 批量撞号、卡头/盗卡、绕过平台 ToS 的自动化滥用、支付通道 exploit |
| 对外文案 | 只谈「本地多档案环境 / 一致性」；**禁止**「保证注册成功 / 保证订阅通过」 |

场景权重（对内排期，非 SLA）：

1. **注册 / 登录**（邮箱或官方 OAuth、人机验证出现率）  
2. **订阅收银台**（官方订阅页能否进入支付步骤；仅用**自有合法支付方式**）  
3. 静态环境（webdriver、UA、WebRTC 等）作为诊断层，服务 1–2  

---

## 1. 对照与环境规格

| 项 | 值 | 备注 |
|---|---|---|
| **主对照** | **Multilogin** · 版本 _安装后填写_ | 用户侧第一对比对象 |
| **备对照** | **GoLogin** · 版本 _安装后填写_ | 防单一产品偏差 |
| 技术侧面基线 | 本机 **Google Chrome** 稳定版 + FoxDesk **Camoufox** | 非商业指纹浏览器；仅辅助 |
| FoxDesk 被测配置 | Chromium · `chromium_backend=auto/patchright` · headed · persistent | 与对照同 OS/分辨率尽量一致 |
| 代理规格 | _住宅优先 / 国家 / 协议_ · 全程同一出口 | 机房 IP 单独记账（R7） |
| 预热剧本 | 见 §3 | 所有引擎 + 对照机相同 |
| 测试账号 | **仅自有**邮箱/手机/订阅；禁止未授权批量 | 平台 ToS 自担 |

版本冻结前：产品族已定，**具体 Multilogin/GoLogin 版本号**在首次 D1 实验日记入。

---

## 2. 基准套件 B-*

| ID | 名称 | 通过标准（草案） | 频率 |
|---|---|---|---|
| **B-static** | webdriver / UA / UA-CH / platform / languages | 关键自动化泄漏项有清单；Phase C 后 webdriver 对常见脚本不可直接为 true（以矩阵为准） | 每引擎构建 |
| **B-webrtc** | WebRTC IP | 配置「代理 + 防漏」时 **不出现真实本地/公网 IP** | 每构建 |
| **B-leak** | 自选公开指纹页 2 个 | 记录分数/异常项；版本间 diff 可解释 | 每构建 |
| **B-ai-signup** | AI 平台**注册/登录**（ChatGPT / Claude / Gemini 中选测） | 结果分类见下；**n≥10**/平台·同剧本；仅自有账号 | 里程碑 |
| **B-ai-subscribe** | AI 平台**官方订阅/升级页**（自有合法支付） | 能否打开订阅流、是否环境层直接拒绝；**不**追求盗刷/绕过；n 与平台政策允许范围 | 里程碑 |
| **B-compare** | 同代理同剧本 vs Multilogin（主）/ GoLogin（备） | 对齐度见 §4 | Phase D 门禁 |

> 历史名称 **B-pay-sandbox** 在本产品线映射为 **B-ai-subscribe**（官方订阅流）。通用支付沙箱若另有，可并列，不替代 AI 场景。

### 结果分类（B-ai-signup / B-ai-subscribe）

| 代码 | 含义（注册/登录） | 含义（订阅） |
|---|---|---|
| `HARD_FAIL` | 环境/自动化层直接拒绝，无验证码/邮件步骤 | 无法进入官方订阅/支付步骤（环境层拒） |
| `CHALLENGE` | 出现验证码、邮件/短信、额外认证 | 出现 3DS/强验证/额外风控挑战 |
| `INIT_OK` | 完成注册或登录到可用会话（对内成功类） | 订阅会话初始化成功（**不要求**必须完成扣款才算样本） |
| `OTHER` | 账号已存在、密码错、地区政策、库存等非环境主因 | 卡组织/账单地址/地区不卖等非浏览器环境主因 |

记录时：**平台名 + 日期 + 代理国家 + 浏览器版本** 必填。禁止把 `OTHER` 算进环境失败率分子而不标注。

---

## 3. 标准预热剧本（草案 · AI 场景）

所有引擎、Multilogin、GoLogin 共用（可修订）：

1. 新建持久化档案 + 指定代理 + 对齐 timezone/locale 与目标平台常见地区  
2. 启动**可见**窗口（禁止 headless）  
3. 空白页 → 公开指纹/检测页（记录 B-static / B-webrtc）  
4. 浏览 2–3 个普通站点各 ≥30s（新闻/文档类即可；**先不要**直接冲注册）  
5. 冷启动一次（关进程再开同一 user_data）  
6. **B-ai-signup**：官方注册或登录页，人工完成验证（记录是否出现挑战）  
7. 需要时 **B-ai-subscribe**：官方订阅/Upgrade 页，仅自有支付方式；记录分类码  

对照机（Multilogin / GoLogin）步骤必须与 FoxDesk **字面同一剧本**，只换浏览器产品。

---

## 4. 对齐度定义（B-compare）

对同一代理、同一预热后，在 **B-ai-signup**（主）与可选 **B-ai-subscribe** 上：

\[
\text{Align} = \frac{\#\{\text{FoxDesk 非 HARD\_FAIL}\}}{\#\{\text{Multilogin 非 HARD\_FAIL}\}}
\]

备对照 GoLogin 同样各算一列，不与主对照混样本。

若对照机样本中非 HARD_FAIL 为 0，则改用 HARD_FAIL 率差：

\[
\Delta_{\text{HF}} = \text{HF rate}_{\text{FoxDesk}} - \text{HF rate}_{\text{对照}}
\]

### 阈值草案（T4 冻结）

| 里程碑 | 建议阈值 | 动作 |
|---|---|---|
| Phase B 结束 | Align 不做硬性；HF 应 **低于** 裸 Playwright 基线 | 进入 C |
| Phase C 结束 | Align ≥ **0.70** 或 Δ_HF ≤ **+15pt**（相对 Multilogin） | 未达 → **Phase D 实现向** |
| Phase D 目标 | Align ≥ **0.85** 或 Δ_HF ≤ **+5pt** | 持续运营 |

> 数字为草案；**无 Multilogin 实测前不得对外引用**。T1 校准后写入「已冻结」。

---

## 5. 非指纹否决项（R7）

若 **同一浏览器** 仅换机房 IP → 住宅 IP 时 HARD_FAIL 率下降 ≥30pt，则：

- 优先产品化代理质量/检测提示  
- 内核 L3 仍可做，但 **不得** 把 AI 注册/订阅失败全归咎于未做 R4  
- 平台账号历史、邮箱质量、地区政策单独记账为 `OTHER`

---

## 6. 冻结检查表

- [x] 主对照产品族：**Multilogin**  
- [x] 备对照产品族：**GoLogin**  
- [ ] Multilogin / GoLogin **具体版本号**  
- [ ] 代理规格  
- [ ] B-ai-signup 平台子集（建议先 1 个平台跑通）  
- [ ] B-ai-subscribe 是否纳入本轮（可选）  
- [ ] n 与时间窗  
- [ ] Align / Δ_HF 最终数字  
- [ ] 签字日期与责任人  

**冻结状态**：产品族已锁定 · 版本与 T1 **未冻结**
