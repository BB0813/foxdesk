# 1.4.0-dev 发布/交付检查清单

**范围**：产品化阶段 1–5 + UX B + 打包说明 A（**不含** Multilogin 实机对照、不含 Setup 正式打 tag）

## 工程门禁

| 项 | 命令/证据 | 状态 |
|---|---|---|
| 单元测试 | `python -m pytest tests -q -p no:sanic` | 见本机构建记录（含 `test_chromium_error_ux`） |
| Phase C worker 冒烟 | `python tools/smoke_phase_c_headed.py` | `_smoke_phase_c_summary.json` ok |
| B-static C 门禁 | `python tools/bstatic_probe.py --backend patchright --require-webdriver-false` | `_bstatic_productization.json` 10/10 |

## 功能交付

| 项 | 证据 |
|---|---|
| 版本 1.4.0-dev | `VERSION`, `APP_VERSION`, `installer.iss` |
| AI 模板 | `backend/templates_data.py` id=`ai-workstation` |
| 模板 user_data 引擎隔离 | `create_from_template` 路径含 `-chromium-`/`-camoufox-` |
| 系统 Chromium 栈 | `/api/system` → playwright/patchright/chrome + `hint` |
| 诊断增强 | `/api/system/diagnostics` 引擎摘要 |
| 环境风险 AI 文案 | `environment_risks_for_profile` |
| UA-CH/media init | `build_fingerprint_init_script` |
| **Stage B** 安装/错误 UX | `humanize_chromium_launch_error`、launch preflight、系统页 install hint、chrome channel 校验 |
| **Stage A** 打包说明 | `docs/research/build-release-notes.md`；`build.bat` 体积/浏览器缓存提示 |
| D backlog | `phase-d-engineering-backlog.md` |
| 文档 | `docs/index.html`, README, CHANGELOG |

## 仍属正式版/人工

- [ ] 打 Windows Setup 并测体积（见 `build-release-notes.md` 记录表）  
- [ ] 安装包内 smoke（同文档 §3）  
- [ ] 发行说明 ThirdPartyNotices（Patchright Apache-2.0 见 `phase-c-packaging.md`）  
- [ ] 可选：Multilogin 实机 B-compare（**非本清单阻塞**）

## 明确不保证

注册/订阅/支付/对齐 Multilogin 成功率。
