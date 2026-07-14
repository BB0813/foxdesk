# Phase B 状态板（R2 / L2）

**开始**：2026-07-14  
**版本**：FoxDesk **1.4.0-dev**  
**前提**：Phase A 双引擎底座 + 有头 Chromium 冒烟通过

---

## 目标（来自 feasibility）

- 完整 Chromium 指纹字段 + UA-CH（best-effort）
- WebRTC / 字体 / 屏幕 / 启动前一致性
- `consistency_policy`: `normal` | `strict`
- 支付模板与预热 checklist
- **验收方向**：L2；B-static 配置层门禁；**仍可能弱于商业机**；非 L3

---

## 交付勾选

| 项 | 状态 |
|---|---|
| `consistency_policy` 字段 | **done** |
| `user_agent` / hardware / deviceMemory / UA-CH | **done** |
| Chromium worker init-script | **done** |
| AutomationControlled 软化 | **done**（webdriver 仍可能 true） |
| strict 启动拦截 | **done** |
| UI 指纹表单扩展 | **done** |
| **字体包** `font_pack` + OS 目录 | **done**（`fingerprint_presets.py`） |
| **媒体设备** empty/random 策略 | **done**（enumerateDevices hook） |
| WebRTC Chromium flags（disable） | **done**（best-effort） |
| `window.chrome` ensure | **done**（浅） |
| B-static 检测站表 | **done** → `b-static-matrix.md` |
| B-static 自动探针 | **done** → `tools/bstatic_probe.py` |
| 商业对齐差距诚实表 | **done**（矩阵 §5） |
| 预热 checklist | **done**（矩阵 §6） |
| 单元测试 presets / B-static score | **done** |
| 本机 B-static 实跑归档 | **done** `_bstatic_run.json` **10/10** gate ok |
| 字体系统级注入 / 真插件表 | **out** → C/D |
| Patchright / 跨环境 webdriver 硬化 | **Phase C** |

---

## Phase B 门禁（进入 Phase C 前）

| 门禁 | 状态 |
|---|---|
| 有头冒烟 L1 | **pass**（`_smoke_headed_summary.json`） |
| 字体/媒体策略可配置 | **pass** |
| B-static 清单文档 | **pass** |
| `bstatic_probe` phase_b_gate_ok | **pass**（本机 10/10；media=5） |
| 单元测试 | **pass**（42） |
| 对外无过检保证文案 | **pass** |
| 商业内核级对齐 | **不要求**（C/D） |

**结论**：Phase B 配置层交付完成，**可以进入 Phase C**（补丁栈 / 自动化隐蔽）。

---

## 有头冒烟 / B-static 归档

| 文件 | 含义 |
|---|---|
| `_smoke_headed_summary.json` | Phase A 有头 worker/PoC |
| `_bstatic_run.json` | B-static 自动跑 |
| `b-static-matrix.md` | 检测面 + 商业差距 |

---

## 明确不做（本阶段）

- 保证过支付 / 去 webdriver 彻底  
- 云控 / 嵌 Token  
- 未授权生产支付压测  

---

## 下一步（Phase C）

**已进入 Phase C**（见 `phase-c-status.md`）：`chromium_backend` / Patchright / B-static `--require-webdriver-false`。

1. ~~评估 Patchright / rebrowser 许可与打包~~ → 进行中（PyPI 宣称 Apache-2.0；发正式版前核 LICENSE）  
2. ~~B-static 将 `webdriver_false` 纳入门禁~~ → 可选门禁已落地  
3. `channel=chrome` 默认路径评估（仍可选，不捆绑）  
4. B-compare 对照商业机（需人工环境）
