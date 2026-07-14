# Phase C 打包与许可笔记

**版本**：1.4.0-dev  
**日期**：2026-07-14  
**状态**：发正式版前复核清单（非法律意见）

---

## 依赖

| 包 | requirements | 本机实测 | 角色 |
|---|---|---|---|
| playwright | `>=1.49` | 1.61.0 | 回退 / 兼容 |
| patchright | `>=1.49` | 1.61.2 | Phase C 优先（auto） |

浏览器二进制**不**打进 git；用户/CI 需：

```bash
pip install -r requirements.txt
playwright install chromium
# Phase C 推荐
patchright install chromium
```

可选：本机 Google Chrome → 档案 `chromium_channel=chrome`（**不**捆绑 Chrome）。

---

## PyInstaller（`foxdesk.spec`）

- `hiddenimports`：`patchright` / `patchright.sync_api` / `patchright.async_api`
- `collect_all` / `collect_submodules`：含 `patchright`（与 playwright 并列）
- 注意：collect 会显著增大包体；正式版需量体积并决定是否「按需下载浏览器」而非全量塞进 Setup

---

## 许可（发版前必做）

| 项 | 笔记 | 状态 |
|---|---|---|
| Patchright | `License-Expression: Apache-2.0`（1.61.2 metadata）；包内 `…/licenses/LICENSE` + driver ThirdPartyNotices | **元数据已核**；发行说明仍附 NOTICE 路径 |
| Playwright | 随上游 Apache-2.0 等 | 跟上游 |
| Google Chrome channel | 用户本机软件；**禁止**再分发 Chrome 安装包 | 策略已定 |
| Camoufox | 既有产品路径 | 不变 |

复核命令备忘：

```bash
python -c "import patchright, pathlib; print(pathlib.Path(patchright.__file__).parent)"
# 在 site-packages/patchright 与上游仓库核 LICENSE / NOTICE
```

---

## 运行时解析

| 档案字段 | 行为 |
|---|---|
| `chromium_backend=auto` | 有 patchright → patchright，否则 playwright |
| `patchright` | 强制；未安装则启动失败 |
| `playwright` | 强制库存栈 |

Worker 在 `launching`/`ready` 事件中 emit `backend=`，便于日志审计。

---

## 用户可见文案边界

- 可写：可选 Patchright 后端、降低常见自动化标记（如 webdriver）
- **不可写**：保证过支付、对齐某商业指纹浏览器、反检测 SLA

---

## 发正式 1.4.0 前勾选

- [x] Patchright Apache-2.0 元数据 + LICENSE 路径确认（2026-07-14）
- [x] 发行说明附 ThirdPartyNotices 摘要 → `docs/ThirdPartyNotices.md`（正式 tag 前再核）
- [ ] 测量 Setup 体积（含/不含浏览器缓存策略）— 见 `build-release-notes.md`
- [ ] 冻结安装路径与 `FOXDESK_BROWSERS_PATH` / Playwright browsers dir
- [x] 源码树冒烟：`python tools/smoke_phase_c_headed.py` → `_smoke_phase_c_summary.json` **ok**
- [x] 打包脚本提示不捆绑浏览器缓存（`build.bat`）
- [ ] 安装包内再冒烟一次
- [x] `docs/index.html` 注明 1.4.0-dev 开发线 + Chromium/Patchright 安装（稳定线 1.3.2 仍可并存描述）

## 体积策略（建议默认）

- **不**把 Playwright/Patchright 浏览器缓存打进 Setup 默认体积预算  
- 首次使用 Chromium 时提示用户/文档执行 `playwright install` / `patchright install`  
- `foxdesk.spec` 已 collect patchright 模块；CI 需观察 dist 体积回归
