# 对照基线：Camoufox vs 商业 Chromium 指纹浏览器

**状态**：实验设计已就绪 · **结果待填**  
**目的**：回答 R1/R2/R7 — 支付「直接拒」主因是内核族、配置，还是 IP？

---

## 1. 实验矩阵

固定：**同一出口代理**（填规格）、同一预热剧本（见 `l3-kpi.md` §3）。

| 运行 ID | 引擎 | 版本 | 代理 | 预热 | B-static 摘要 | B-webrtc | B-pay 结果码 | 备注 |
|---|---|---|---|---|---|---|---|---|
| B001 | Camoufox（FoxDesk） | _填_ | _填_ | Y/N | | | | |
| B002 | 商业对照主 | _填_ | 同 | 同 | | | | |
| B003 | 本机 Chrome 手动 | _填_ | 同 | 同 | | | | 上界 |
| B004 | Playwright Chromium 裸 | PoC | 同 | 同 | | | | 下界 |
| B005 | Camoufox | 同 B001 | **换 IP 类型** | 同 | | | | R7 |
| B006 | 商业对照 | 同 B002 | **同 B005 IP** | 同 | | | | R7 |

至少各引擎 **n=10** 支付沙箱（可分多日）。

---

## 2. 配置快照（每引擎贴一次）

### 2.1 FoxDesk / Camoufox

```
profile name:
os / headless / persistent:
proxy / geoip / timezone / locale:
block_webrtc / webrtc_mode:
block_webgl / humanize:
template: payment-checkout? 
```

### 2.2 商业对照

```
产品名 / 版本:
内核显示 (Chrome xx):
时区 / 语言 / WebRTC 策略:
是否「指纹噪声」默认开:
```

---

## 3. 单变量假设

| 假设 | 验证方式 | 结果 (待填) |
|---|---|---|
| H1：Firefox 族导致更多 HARD_FAIL | B001 vs B002 | |
| H2：裸 Chromium 自动化也 HARD_FAIL | B004 vs B002 | |
| H3：IP 权重大于内核 | B001 vs B005，B002 vs B006 | |
| H4：预热显著降低 HARD_FAIL | 同引擎预热 Y vs N | |

---

## 4. 结论模板（实验后填写）

```text
主因排序：1) …  2) …  3) …
是否支持进入 Phase A 双引擎：Y/N
是否支持 Phase C 补丁栈优先于改代理产品：Y/N
是否已能证明需要 Phase D：Y/N（通常 C 之后才判）
```

---

## 5. 操作步骤（执行者清单）

1. [ ] 记录代理：类型 / 国家 / `exit_ip`（用 FoxDesk 代理测试）  
2. [ ] 用 **结账/支付向** 模板启动 Camoufox，完成预热  
3. [ ] 跑 `tools/poc_chromium_launch.py --probe` 作 B004  
4. [ ] 对照机同代理同剧本  
5. [ ] 填表 §1–§3  
6. [ ] 更新 `phase0-status.md` 中 T1 勾选  
