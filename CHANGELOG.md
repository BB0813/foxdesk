# Changelog

## 1.4.0 — 2026-07-15

Stable dual-engine release (Camoufox + Chromium/Patchright). Still **no cloud control**. Chromium is a local automation stack — **not** commercial anti-detect; **no** payment/signup/subscribe guarantee.

### Packaging / UX (this tag)
- Humanized Chromium install/launch errors; launch preflight; system install hints
- `foxdesk.spec` excludes host ML/IDE stacks (torch/jedi/…); collect pythonnet/clr_loader for WebView
- Desktop falls back to system browser + tray when frozen WebView/pythonnet fails
- Build notes: `docs/research/build-release-notes.md`; third-party: `docs/ThirdPartyNotices.md`
- Local portable ~394 MB; Setup ~70 MB (browser caches not bundled)

### Dual-engine base (Phase A)
- Profile field `engine`: `camoufox` | `chromium` (default camoufox)
- Optional `chromium_channel`: empty (bundled) | `chrome` | `msedge`
- `backend/chromium_worker.py` — Playwright persistent context, shared `.cmd.jsonl` / `.result.jsonl` control channel
- Single launch + **batch launch** route by per-profile engine
- Frozen `--worker` dispatches engine from runtime JSON (`desktop.py`)
- Chromium **rejects server mode** in Phase A; user_data path isolation warnings
- Soft `environment_risks` flag `engine_chromium_phase_a`
- UI: engine + channel selects; tags show engine; payment templates include Camoufox + experimental Chromium
- Headed smoke tool: `tools/smoke_phase_a_headed.py`

### Phase C (MVP closed on 1.4.0 — patch stack)
- `chromium_backend`: `auto` | `playwright` | `patchright` (auto prefers Patchright)
- Chromium worker resolves Patchright/Playwright at launch; batch/single write resolved backend
- UI: Chromium backend select; Checkout Chromium template uses `auto`
- B-static probe: `--backend` + `--require-webdriver-false` (Phase C gate)
- Deps: `playwright>=1.49`, `patchright>=1.49` in requirements; hiddenimports in foxdesk.spec
- Local A/B: patchright headed `webdriver=false`, stock playwright `webdriver=true` (not a payment guarantee)
- Headed worker smoke: `tools/smoke_phase_c_headed.py` → `_smoke_phase_c_summary.json`
- Packaging notes: `docs/research/phase-c-packaging.md` (Patchright Apache-2.0 metadata)
- Status: `docs/research/phase-c-status.md` (**MVP closed**)

### Phase D (started on 1.4.0 — R4 pre-research D0)
- Status board: `docs/research/phase-d-status.md`
- Gap matrix skeleton: `docs/research/phase-d-gap-matrix.md`
- Engineering backlog (no commercial install required): `docs/research/phase-d-engineering-backlog.md`
- Commercial references locked: **Multilogin** (primary), **GoLogin** (secondary) — direction only unless user runs compare
- Target scenario: normal **ChatGPT / Claude / Gemini** signup & subscription (own accounts)
- KPI: B-ai-signup / B-ai-subscribe in `docs/research/l3-kpi.md`
- No kernel coding yet; Internal KPI only — **no** signup/subscribe/payment or anti-detect SLA

### UX polish B → packaging A (1.4.0)
- Humanized Chromium install/launch errors (`humanize_chromium_launch_error`, worker hints)
- Launch preflight in UI: missing patchright/playwright, chrome channel mismatch, AI proxy soft hint
- System grid shows Chromium install command hint; channel option marks Chrome detected
- Session logs: backend/channel/AI notes; error-hint lines on worker failure
- validate_profile: chrome channel without Chrome is a hard error
- Packaging notes: `docs/research/build-release-notes.md`

### Productization (1.4.0 — stages 1–4 without Multilogin lab)
- Template **AI Workstation** (`ai-workstation`): Chromium + auto/patchright, fonts/media, warm-up checklist in notes
- Template create isolates `user_data` with engine suffix (`-chromium-` / `-camoufox-`)
- `/api/system` + diagnostics: playwright/patchright/chrome detection; profile engine summary in diagnostics
- Environment risks: AI-tag hints, chrome channel missing, honest no-guarantee copy (signup/subscribe)
- Chromium init: stronger UA-CH + mediaDevices hooks (config layer)
- UI system grid shows Chromium stack status; risk note covers signup/subscribe
- Docs: `docs/index.html` 1.4.0 install notes


### Phase B (1.4.0 — L2 config / commercial-style consistency)
- `consistency_policy`: `normal` | `strict` (strict promotes high `environment_risks` to launch errors)
- Chromium fingerprint fields: `user_agent`, `hardware_concurrency`, `device_memory`, `ua_ch_*`
- **Fonts**: `font_pack` (`auto`/`windows`/`macos`/`linux`) + `backend/fingerprint_presets.py`
- **Media**: `media_devices` empty/random applied on Chromium via `enumerateDevices` hook
- Chromium WebRTC disable flags (best-effort); `window.chrome` ensure; init-script WebGL/UA-CH
- Soft AutomationControlled flag (**`webdriver` may still be true** → Phase C)
- B-static matrix + probe: `docs/research/b-static-matrix.md`, `tools/bstatic_probe.py`
- UI: font pack + extended fingerprint form; Checkout Chromium template includes font/media
- Status: `docs/research/phase-b-status.md`


## 1.3.2 — 2026-07-14

Ops polish on 1.3.1 (still **no cloud control**).

### Fixes
- Session log download accepts **GET and POST** (UI was GET; older POST clients still work)
- Log download request now sends `X-FoxDesk-Token`

### UI wiring
- **Batch stop** selected running sessions (`POST /api/sessions/batch-stop`)
- Proxy **health-status** hint (last run, interval, auto-check on/off)

### Session control
- Browser-mode **screenshot** (PNG base64, size-capped) + **evaluate** (bounded expression)
- Worker rejects host-escape-ish evaluate tokens; expression max 1500 chars

### Environment / payment readiness
- Launch + fingerprint-check return soft **environment_risks** (proxy/geoip/WebRTC/headless, etc.)
- New **Checkout / Payment** profile template (visible, persistent, geoip, WebRTC off; no pass guarantee)
- UI shows risks on fingerprint check and high-risk toast snippet on launch

### Docs
- `docs/index.html` brought in line with 1.3.x (launcher, data dir, API surface)
- CHANGELOG 1.1.0 known-limitations note corrected for later DPAPI / FoxDesk data dir


## 1.3.1 — 2026-07-14

Follow-up polish on 1.3.0 (still **no cloud control**).

### Backup
- Password-encrypted `.fdk` backups (PBKDF2 + encrypt-then-MAC, stdlib-only)
- **Restore** API + UI (with pre-restore snapshot; legacy 1.3.0 zip still readable)
- Backup list under System panel

### Server mode
- Stronger `ws_endpoint` scraping (labels, bare host:port fallback, incomplete buffer scan)
- Sidecar `.ws` file + session **refresh endpoint** API/button
- Server-mode worker commands: `ping` / `endpoint` / `stop`

### Ops / docs
- CI runs `pytest` (plugin autoload disabled for clean env)
- Release notes data dir text: `%APPDATA%\FoxDesk` (+ legacy migrate)
- Docs alignment for launcher / data dir naming


## 1.3.0 — 2026-07-14

Local-only control plane improvements (still **no cloud control**).

### Session control
- Live **navigate** + **fingerprint probe** for browser-mode sessions via worker command channel (`.cmd.jsonl` / `.result.jsonl`)
- Server mode stdout tee to capture **ws_endpoint** when Camoufox prints it
- **Max concurrent sessions** (default 8) and **idle auto-stop** (minutes, 0=off)
- Session resource hint API (`/api/system/resources`)

### Proxy pool
- Background **proxy health scheduler** (interval + enable in settings)
- Assign modes: **sticky** | **round_robin** | **random_healthy**
- One-click “check now” in UI

### Data & ops
- Local **backup zip** under `data_dir/backups` (password integrity stamp; not strong encryption)
- Activity log atomic writes
- Extra profile templates (social / research / mobile window)
- Launcher rename: `Start-FoxDesk.bat` / `.ps1` (legacy names forward)
- Unit tests for settings, session control, SHA256SUMS, navigate URL validation

### UI
- Settings: sessions / idle / proxy mode & interval
- Sessions: navigate, probe, idle display, fingerprint report
- Proxies: health-now button

## 1.2.0 — 2026-07-14

Local-only quality release (no cloud control).

### Updates
- Default update mirror: **ghproxy** (with multi-prefix failover + official fallback)
- Optional **GitHub Token** via UI / `FOXDESK_GITHUB_TOKEN` / `GITHUB_TOKEN` (never committed)
- Token is stored encrypted at rest (Windows DPAPI)

### Security & data
- Proxy passwords encrypted at rest (DPAPI on Windows)
- Atomic JSON writes for profiles / proxies / settings / channels
- Data directory prefers `%APPDATA%\FoxDesk` with auto-migration from `CamoufoxManager`

### Ops
- System → update settings panel
- One-click **diagnostics export** (redacted) under `data_dir/logs`


## 1.1.1 — 2026-07-14

Hotfix: GitHub update check no longer fails hard on API rate limit (HTTP 403).

- Fall back to github.com web JSON + releases.atom when `api.github.com` is rate-limited
- Short in-process check cache + quieter auto-check interval
- Clearer Chinese error when the API quota is exhausted


## 1.1.0 — 2026-07-14 (Stable)

First stable release after the 1.1.0-beta series.

### Highlights
- Guided first-run setup (auto install/fetch Camoufox in frozen builds)
- In-app update check + one-click Windows installer update with **SHA256** verification when `SHA256SUMS` is present
- Proxy pool, templates, system tray, session error UX
- Local API protection via per-process `X-FoxDesk-Token` (injected into the UI shell)
- Default install path: `%LOCALAPPDATA%\Programs\FoxDesk` (no admin required for uninstall)

### Security / packaging
- Bundle `camoufox` + `apify_fingerprint_datapoints` data files in PyInstaller build
- CI smoke checks for bundled packages and datapoint zips
- Uninstaller can optionally remove `%APPDATA%\CamoufoxManager`

### Known limitations (historical at 1.1.0; superseded later)
- Local API has no multi-user auth model (token only protects casual local abuse) — **still true**
- ~~Proxy credentials stored in local JSON in clear text~~ → **1.2+**: sealed with Windows DPAPI / local obfuscation
- Server mode may not surface a real `ws_endpoint` for all Camoufox versions — **still true** (1.3.1+ refresh endpoint helps)
- ~~Data directory still uses historical name `CamoufoxManager`~~ → **1.2+**: `%APPDATA%\FoxDesk` with auto-migration

## 1.1.0-beta.6
- Fix missing fingerprint datapoints in frozen bundle
- Cleaner uninstall + admin purge helpers

## 1.1.0-beta.5
- In-process Camoufox path/fetch for frozen setup
- Localized setup step status

## 1.1.0-beta.4
- In-app update manager (check/download/install)

## 1.1.0-beta.3
- Guided first-run wizard auto setup

## 1.1.0-beta.2
- Proxy pool, tray, templates, session UX, health/cleanup

## 1.1.0-beta.1
- Fingerprint/worker fixes, frozen worker, CI installer pipeline
