# Phase D 工程 Backlog（无商业机实装对照版）

**状态**：D0 文档 backlog · **非** D3 内核开工令  
**对标方向**：Multilogin（主）/ GoLogin（备）· AI 注册订阅场景  
**原则**：无 Multilogin 实测不宣称对齐；无 SLA

---

## 已由 Phase C + 产品化吸收（不必等 D3）

| 项 | 状态 |
|---|---|
| `chromium_backend` auto/patchright | done |
| webdriver 本机可 false（patchright） | done（本机） |
| AI 工作档案模板 + 预热 notes | done |
| 系统页 Playwright/Patchright/Chrome 探测 | done |
| 诊断导出含引擎摘要 | done |
| UA-CH / mediaDevices init 加固 | done（配置层） |
| user_data 模板按引擎隔离后缀 | done |

---

## Backlog（工程向 · 按痛感排序）

| ID | 项 | 为何像商业机常做 | 依赖 | 优先级 |
|---|---|---|---|---|
| D-B1 | CDP / Runtime 自动化痕迹调研与缓解评估 | 商业栈常处理 | 桌面研究 | P1 |
| D-B2 | iframe / Worker 内 navigator 一致性 | 部分站点嵌框检测 | init 深化 | P1 |
| D-B3 | 权限/Notification/传感器默认面 | 桌面像真机 | 配置策略 | P2 |
| D-B4 | TLS / HTTP2 / JA3 侧面（可选 B-leak） | 深度对照 | 工具链 | P2 |
| D-B5 | channel=chrome 一键建议 + 启动失败可读 | 真 Chrome 指纹 | 本机 Chrome | P2 |
| D-B6 | 代理质量提示（住宅 vs 机房）产品化 | R7 IP 权重大 | 代理池 | P1 |
| D-B7 | 跟 Chrome 大版本的 patchright/playwright 跟版流水线 | 防折旧 | CI | P2 |
| D-B8 | 自维护补丁 Chromium（真 R4） | 仅当 B1–B4 仍不够 | 编制 3–12+ 人月 | **P0 仅触发后** |

---

## 触发 D3（内核）的书面条件

满足 **全部** 再开编码分支：

1. 有自愿对照数据 **或** 大量用户可复现「仅 FoxDesk 环境层 HARD_FAIL、同代理 Multilogin 可过」  
2. 根因分层指向 **内核/CDP/协议** 而非 IP/邮箱  
3. 书面预算与维护人  

否则维持 **C + 配置 + 本 backlog 的 P1/P2**。

---

## 近期默认迭代（与「全做」产品线对齐）

1. 发布固化 1.4.0-dev 文档/安装说明  
2. AI 模板与风险文案  
3. 静态指纹缺口（UA-CH/media/fonts）  
4. 控制面诊断与隔离  
5. 本文件跟踪 D-B*，不空开内核  

---

## 变更

| 日期 | 记事 |
|---|---|
| 2026-07-14 | 初稿；配合产品阶段 1–5 |
