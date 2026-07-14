# Chromium 补丁栈评估

**状态**：Phase C 结论已填 · 发正式版前再核 LICENSE/体积  
**环境快照（2026-07-14）**

| 包 | 本机 |
|---|---|
| playwright | **1.61.0**（已装，Phase C 升级） |
| ms-playwright chromium | 随 install 更新 |
| patchright | **1.61.2**（已装） |
| camoufox | 已装 |

---

## 1. 候选对比

| 维度 | A Playwright Chromium | B Patchright | C channel=chrome |
|---|---|---|---|
| 角色 | Phase A 底座 | Phase C 默认候选 | A/B 增强选项 |
| 安装 | `playwright install chromium` | `pip install patchright` + install | 依赖本机 Google Chrome |
| 许可 | Apache-2.0 等（随包） | Apache-2.0（PyPI 宣称） | Google Chrome 条款（分发受限） |
| 打包进安装包 | Chromium 可按需下载 | 同 Playwright 系 | **不宜**捆绑 Chrome |
| 反自动化 | 弱（测试浏览器） | 宣称修补 chromium 泄漏 | 真 Chrome 指纹 + 仍可能有自动化面 |
| Firefox | N/A | **不支持** | N/A |
| 与 FoxDesk | 直接 | drop-in API 接近 | `channel="chrome"` |
| 风险 | 过检差 | 供应链/跟版 | 用户机必须装 Chrome |

---

## 2. 决议倾向（Phase 0 末确认）

| 阶段 | 倾向 |
|---|---|
| Phase A | **A** Playwright Chromium（本机已具备） |
| Phase C | 实装 **B** 对比矩阵后，若 B-static/B-pay 明显优于 A → 默认 backend=patchright |
| 增强 | 高级选项 **C**（检测本机 Chrome，不捆绑） |
| Phase D | A/B/C 皆不足对照机 → R4 补丁内核 |

---

## 3. 实机任务

- [x] `pip install patchright` 并 `patchright install chromium`  
- [x] 同一 `poc` 参数跑 A vs B（见 `_phase_c_poc_*.json`）  
- [ ] 记录体积与启动耗时（跟版时补）  
- [ ] LICENSE 全文过目，确认可随 FoxDesk 发行（发正式版前）  

### 命令备忘

```bash
# A
python tools/poc_chromium_launch.py --backend playwright --probe --headed

# B（安装 patchright 后）
python tools/poc_chromium_launch.py --backend patchright --probe --headed

# C
python tools/poc_chromium_launch.py --backend playwright --channel chrome --probe --headed
```

### 本机结果（2026-07-14 headed）

| 后端 | webdriver | 归档 |
|---|---|---|
| playwright | true | `_phase_c_poc_pw.json` |
| patchright | **false** | `_phase_c_poc_pr.json` |

---

## 4. 结论

```text
推荐 Phase C 默认 backend：auto（优先 patchright，回退 playwright）
否决项：无（R5 OEM 仍否决）
产品默认：chromium_backend=auto；不捆绑 Google Chrome
进入 Phase C 编码：Y（已落地 worker/UI/probe）
```
