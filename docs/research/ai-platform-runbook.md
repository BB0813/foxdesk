# AI 平台场景实验手册（对内）

**场景**：正常注册 / 登录 / 订阅 ChatGPT · Claude · Gemini  
**对照**：Multilogin（主）· GoLogin（备）  
**FoxDesk**：Chromium + `chromium_backend=patchright`（推荐）  
**边界**：**仅自有账号与官方流程**；无通过率保证；禁止批量撞号/盗卡/绕过 exploit

---

## 1. 开测前

| 检查 | 说明 |
|---|---|
| 对照已装 | Multilogin 版本记入 `l3-kpi.md` §1 |
| 代理 | 同一出口；尽量住宅；国家与档案 timezone 一致 |
| 档案 | 新 persistent user_data；FoxDesk 与对照**各建新档**，勿复用脏档 |
| 窗口 | 全程 headed |
| 邮箱 | 自有、干净；少用一次性 junk 除非你在测邮箱质量（记 `OTHER`） |

---

## 2. 推荐顺序

1. **B-static** 并排（公开指纹页）— 先确认不是「webdriver 裸奔」  
2. **B-webrtc**（若走了代理）  
3. 预热 §3（普通站 2–3 个）  
4. **B-ai-signup** 只选 **一个** 平台先跑通剧本  
5. 需要再 **B-ai-subscribe**（官方 Upgrade；自有卡）  

---

## 3. 单次样本怎么记

```text
date:
platform: chatgpt|claude|gemini
product: foxdesk|multilogin|gologin
product_version:
proxy_country:
result: HARD_FAIL|CHALLENGE|INIT_OK|OTHER
notes: 验证码类型 / 邮件 / 地区文案 / 截图文件名
```

- `HARD_FAIL`：环境层直接挡，几乎无正常验证路径  
- `CHALLENGE`：有验证但仍在官方流程内  
- `INIT_OK`：进到已登录或可用会话 / 订阅流初始化  
- `OTHER`：密码错、账号已存在、地区不卖等  

---

## 4. 诚实归因

| 现象 | 优先怀疑 |
|---|---|
| 只换机房→住宅就过 | IP（R7），别急着怪内核 |
| Multilogin 也 HARD_FAIL | 代理/地区/平台政策，非 FoxDesk 独有 |
| 仅 FoxDesk HARD_FAIL | 自动化/指纹面 → 记入 gap matrix |
| 邮箱验证环 | 邮箱质量 → `OTHER` 或单独标签 |

---

## 5. 明确不做

- 保证「一定能注册 ChatGPT/Claude/Gemini」  
- 未授权批量注册、接码滥用文档化成产品功能  
- 支付/卡组攻击、伪造账单  

---

## 6. 相关文档

- `l3-kpi.md` — 分类与 Align  
- `phase-d-status.md` / `phase-d-gap-matrix.md` — D 进度与填表  
- `phase-c-status.md` — 当前 patchright 基线  
