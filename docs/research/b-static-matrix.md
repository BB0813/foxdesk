# B-static 检测站 / 静态指纹矩阵（Phase B）

**版本**：FoxDesk **1.4.0-dev**  
**工具**：`tools/bstatic_probe.py`  
**原则**：对标商业机的是 **配置一致性清单**，不是「保证过检」。`webdriver` 彻底消除属 **Phase C**。

---

## 1. 公开检测面清单（可人工对照）

仅使用 **公开指纹页 / 自有脚本**，禁止未授权对生产支付打量。

| ID | 检测面 | 关注字段 | 商业机常见期望 | Phase B 目标 | Phase C 目标 |
|---|---|---|---|---|---|
| S1 | 本机 probe / about:blank | webdriver, UA, platform | webdriver 不可读/false | 记录；配置层对齐 | webdriver 不可直接读 |
| S2 | UA / Headless | `HeadlessChrome` 子串 | 无 | **必须无**（有头） | 同左 |
| S3 | UA-CH | brands / platform / mobile | 有 brands，platform 与 OS 一致 | init-script / channel | 与真 Chrome 一致 |
| S4 | languages / locale | `navigator.languages` | 与代理地区一致 | 可配置 | 同左 |
| S5 | timezone | `Intl` | 与代理地区一致 | 可配置 + strict | 同左 |
| S6 | screen / dpr | w×h×depth | 常见桌面分辨率 | 可配置 | 同左 |
| S7 | hardwareConcurrency / deviceMemory | 数值 | 非 0、合理 | 可配置 | 同左 |
| S8 | WebGL | vendor/renderer | 稳定、与 OS 故事一致 | 可配置 | 同左 |
| S9 | WebRTC | local/public candidates | 代理场景无真实 IP | disable + flags | 补丁级 |
| S10 | plugins / mimeTypes | length | Chromium 常 >0 | 尽力（bundled 可能弱） | channel=chrome 改善 |
| S11 | `window.chrome` | runtime 对象 | 存在 | ensureChrome init | 真 runtime |
| S12 | mediaDevices | enumerateDevices | 桌面有 mic/speaker/cam | random/empty 策略 | 同左 |
| S13 | fonts | check / 枚举 | OS 字体集 | font_pack + check hook | 系统字体注入 |
| S14 | Canvas/Audio | 噪声策略 | 稳定或可控噪声 | 字段保留（Camoufox 深） | Chromium 深注入 |

---

## 2. 推荐公开页（人工 B-leak，可选）

| 页 | 用途 | 注意 |
|---|---|---|
| browserleaks.com/javascript | 综合 JS | 仅观察，不提交敏感信息 |
| browserleaks.com/webrtc | WebRTC | 对照 S9 |
| creepjs / 同类开源页（自托管更佳） | 综合熵 | 分数仅作版本 diff，不作 SLA |

---

## 3. 本机自动跑法

```bash
python tools/bstatic_probe.py --headed --json-out docs/research/_bstatic_run.json
# 可选系统 Chrome：
python tools/bstatic_probe.py --channel chrome --headed
```

**Phase B 门禁（工具内 `phase_b_gate_ok`）**

- 失败即挡：出现 `HeadlessChrome`、配置层崩溃等（**不含** webdriver=true）
- 记录但不挡 Phase B：`webdriver=true` → 标记 `phase_c_needed`

---

## 4. 矩阵填写（引擎列）

| 字段 | Camoufox | PW Chromium headed + Phase B（2026-07-14 本机） | channel=chrome | 商业对照 | 本机 Chrome |
|---|---|---|---|---|---|
| userAgent | | Chrome/127 Win64（无 Headless） | | | |
| HeadlessChrome | | **false** | | | |
| webdriver | | **false**（本机 headed+flags；不保证全环境） | 待测 | 期望 false | false |
| UA-CH | n/a / 弱 | brands Chromium+Chrome+Not.A/Brand；platform=Windows | 待测 | 完整 | 完整 |
| platform | | Win32 | | | |
| languages | | en-US | | | |
| timezone | | America/New_York | | | |
| hardwareConcurrency | | 8 | | | |
| deviceMemory | | 8 | | | |
| screen | | 1920×1080×24 | | | |
| WebGL | | Intel UHD 630（配置覆盖） | | | |
| mediaDevices count | | **5**（random 策略） | | | |
| fonts check | | Arial/Segoe UI/Times/Helvetica true | | | |
| window.chrome | | true | | | |
| pluginsLength | | 5 | | | |
| B-static score | | **10/10** gate ok（`_bstatic_run.json`） | | | |

来源：`docs/research/_bstatic_run.json`。不同机器/版本可能 webdriver 仍为 true → 仍以 Phase C 为自动化隐蔽主战场。

---

## 5. 商业对齐差距（诚实）

| 层 | 商业常见 | FoxDesk 1.4.0-dev Phase B | 缺口阶段 |
|---|---|---|---|
| 配置一致性 | 强 | **有**（字段+strict+模板） | B 收口 |
| 字体/媒体故事 | 强 | **有策略**（pack / enumerate hook） | B；深度注入 C/D |
| 自动化隐蔽 | 内核补丁 | **弱**（webdriver 仍可能 true） | **C** |
| 支付过检 | 工程化 | **无保证** | C/D + IP |

---

## 6. 预热 checklist（支付向，配置层）

1. `engine=chromium`，**有头**，`persistent_context=true`  
2. 独立 `user_data_dir`（`*-chromium`）  
3. 住宅代理 + `locale`/`timezone` 对齐地区  
4. `webrtc_mode=disable` + `block_webrtc`  
5. `font_pack=windows`（或对应 OS）+ `media_devices=random`  
6. 固定 screen / WebGL / hardwareConcurrency  
7. `consistency_policy=strict`（配齐后）  
8. 冷启动一次再进业务页  
9. **不**把 B-static 绿勾当成支付通过  

---

## 7. 结果归档

| 文件 | 含义 |
|---|---|
| `docs/research/_bstatic_run.json` | 最近一次自动 B-static |
| `docs/research/_smoke_headed_summary.json` | Phase A 有头冒烟 |
| 本文件 | 清单与门禁说明 |
