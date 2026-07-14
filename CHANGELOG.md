# Changelog

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

### Known limitations
- Local API has no multi-user auth model (token only protects casual local abuse)
- Proxy credentials stored in local JSON in clear text
- Server mode may not surface a real `ws_endpoint` for all Camoufox versions
- Data directory still uses historical name `CamoufoxManager`

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
