# FoxDesk

Local dual-engine fingerprint browser manager — free, open source, privacy-first.

**Current version: `1.6.3` (Stable)**

<p align="center">
  <img src="static/logo.png" width="120" alt="FoxDesk Logo">
</p>

**Language:** [中文](README.md) | English

## Features

- **Dual engine** — pick Camoufox (Firefox) or Chromium (Playwright/Patchright; `auto` prefers Patchright) per profile
- **Profile management** — create, edit, clone, import/export, tag grouping
- **Fingerprint control** — parameter editing + random generation + live probe reports + static consistency scoring
- **Session control** — start/stop/logs, **live navigation**, concurrency limit, idle auto-stop
- **Server mode** — best-effort capture of `ws_endpoint` for external Playwright clients
- **Proxy pool** — health checks, sticky/round-robin/random healthy assignment; passwords sealed with DPAPI
- **Cookie management** — export SQLite cookies; import JSON / Netscape, injected on next launch
- **Scenario templates** — clean / e-commerce / automation / social / research / mobile window, etc.
- **Proxy-environment matching** — exit IP classification (residential/datacenter), one-click timezone/locale matching, batch environment application
- **Local backups** — password-encrypted `.fdk` export/restore (auto snapshot before restore)
- **In-app updates** — GitHub Releases + **ghproxy** mirror + optional token + SHA256
- **Diagnostics export** — one-click redacted diagnostics bundle from the System page
- **Local API token** — per-process `X-FoxDesk-Token` injected into the UI
- **First-run wizard / tray / bilingual UI / installer**

## Platform support

| Platform | Status | Distribution |
|---|---|---|
| Windows x64 | ✅ Full (Setup / portable / auto-update) | `FoxDesk-x.y.z-Setup.exe` |
| Linux x64 | ✅ Experimental (portable tar.gz; GUI needs WebKit/GTK libs) | `FoxDesk-linux-x64.tar.gz` |
| macOS x64 | ✅ Experimental (portable zip, unsigned) | `FoxDesk-macos-x.y.z.zip` |

**macOS Gatekeeper note** (if the first launch is blocked after downloading the zip):
1. Simplest: right-click `FoxDesk.app` → Open (first launch only)
2. Terminal: `xattr -cr /path/to/FoxDesk.app`
3. No bypass needed: `brew tap BB0813/foxdesk && brew install --cask foxdesk` (template in `tools/homebrew/`; update version/sha256 after each release)
4. Fully signed: requires the Apple Developer Program ($99/year) for Developer ID signing + notarization — CI flow documented in `docs/research/macos-signing.md`

Linux GUI needs `libwebkit2gtk-4.1` and GTK3 (`sudo apt install libwebkit2gtk-4.1-dev gir1.2-gtk-3.0`); on headless machines use `./FoxDesk --serve <port>` and open it in a browser. macOS builds are unsigned — first open via right-click → Open.

## Quick start

### Prebuilt (recommended)

Download the latest release from [GitHub Releases](https://github.com/BB0813/foxdesk/releases) and run the installer / portable build for your OS. On Linux there is also a one-line installer:

```bash
curl -fsSL https://raw.githubusercontent.com/BB0813/foxdesk/main/tools/install-linux.sh | sudo bash
```

### From source

```bash
git clone https://github.com/BB0813/foxdesk.git
cd foxdesk
python -m pip install -r requirements.txt
# Camoufox browser: use the System page "Install / Fetch" in the app,
# or follow the Camoufox documentation.
# Optional Chromium engine:
#   playwright install chromium
#   patchright install chromium   # recommended; chromium_backend=auto prefers it
python desktop.py
# or
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload
```

On Windows you can also double-click `Start-FoxDesk.bat` (the legacy name `Start-CamoufoxManager.bat` still works).

**Not** a pass-rate / payment guarantee. Research notes and gates live in `docs/research/` (`phase-c-status.md` / `phase-d-status.md`).

### Uninstall / clean reinstall

- **1.1.0+** installs to `%LOCALAPPDATA%\Programs\FoxDesk` (normally no admin rights needed)
- The uninstaller lets you choose whether to delete user data: `%APPDATA%\FoxDesk` (legacy `CamoufoxManager` is migrated automatically)
- If an old version lives in `C:\Program Files\FoxDesk`, run as administrator:

```powershell
powershell -ExecutionPolicy Bypass -File tools/clean-foxdesk.ps1 -Yes
# or right-click → Run as administrator: tools/purge-foxdesk-admin.bat
```

## Core concepts

| Concept | What it is |
|---|---|
| **Profile** | One browser identity: engine, startup URL, proxy, fingerprint parameters, storage dir. Sessions are launched from profiles. |
| **Engine** | `camoufox` (Firefox-based) or `chromium` (Playwright/Patchright). Chosen per profile; the Chromium backend (`auto`/`playwright`/`patchright`) is also per profile. |
| **Fingerprint** | The set of environment parameters a site can observe: UA, platform, screen, WebGL, timezone, locale, media devices, WebRTC behavior, etc. FoxDesk edits them, generates coherent random sets, and scores static consistency — a **coherence score**, not an anti-detect guarantee. |
| **Proxy** | Per-profile proxy (or a proxy-pool entry). Passwords are sealed locally (DPAPI on Windows). The proxy pool adds health checks and geo/organization classification. |
| **Session** | A running browser process launched from a profile, with logs, live navigation, fingerprint probe, screenshot and `evaluate` over a local control channel. |
| **Templates** | Preset bundles of profile settings for common scenarios (clean, e-commerce, automation, social, research, mobile). Applying one fills a new profile. |

## Configuration reference

All fields live in the profile editor (Basic / Proxy / Fingerprint environment / Advanced tabs). Values are stored in `%APPDATA%\FoxDesk` as local JSON.

### General

| Field | Values | Meaning |
|---|---|---|
| `name` | text (1–80 chars) | Display name, also used for the default data dir |
| `startup_url` | URL | Page opened when the session starts |
| `mode` | `browser` / `server` | Interactive browser vs. automation server (ws endpoint for external clients) |
| `engine` | `camoufox` / `chromium` | Browser engine for this profile |
| `chromium_backend` | `auto` / `playwright` / `patchright` | Chromium automation backend (`auto` prefers Patchright) |
| `chromium_channel` | text | Optional installed Chrome channel (e.g. `chrome`) |
| `os` | `auto` / `windows` / `macos` / `linux` | Target OS the fingerprint should look like |
| `headless` | bool | Run without a visible window |
| `persistent_context` | bool | Reuse the profile's user-data dir (cookies/storage persist) |
| `user_data_dir` | path | Storage directory; empty = default under the FoxDesk data dir |
| `humanize` | bool | Human-like cursor motion (Camoufox) |
| `geoip` | bool | Derive geo hints from the proxy exit IP (Camoufox) |
| `tags`, `notes` | text | Organization only |

### Locale and timezone

| Field | Values | Meaning |
|---|---|---|
| `locale` | BCP-47 tag, e.g. `en-US`, `zh-CN`, `de-DE`, `ja-JP` | **Browser** locale: `navigator.language`, `Intl` defaults, and the `Accept-Language` header. Empty = engine default. |
| `timezone` | IANA name, e.g. `America/New_York`, `Asia/Shanghai` | **Browser** timezone (`Intl.DateTimeFormat().resolvedOptions().timeZone`). Should match the proxy exit country. |

> **UI language vs. profile locale.** The desktop UI language is **not** controlled by any profile field. It follows the system/browser locale on first launch (Chinese locale → 中文, everything else → English), can be switched at any time via the **中 / EN toggle at the bottom-left of the sidebar**, and the choice is persisted locally. A profile's `locale` only affects the browser environment that profile launches.

### Fingerprint environment

| Field | Values | Meaning |
|---|---|---|
| `user_agent` | text | Explicit UA override (empty = generated) |
| `navigator_platform` | text | `navigator.platform` override |
| `navigator_vendor` | text | `navigator.vendor` override |
| `screen_width` / `screen_height` | px | Screen size presented to sites |
| `screen_color_depth` | bits | `screen.colorDepth` / `pixelDepth` |
| `device_pixel_ratio` | float | `devicePixelRatio` |
| `hardware_concurrency` | int | `navigator.hardwareConcurrency` |
| `device_memory` | GB | `navigator.deviceMemory` (Chromium) |
| `max_touch_points` | int | `-1` = engine default, `0+` = override |
| `canvas_noise` | bool | Canvas readback noise (Camoufox) |
| `audio_noise` | bool | Audio fingerprint noise |
| `webgl_vendor` / `webgl_renderer` | text | WebGL vendor/renderer strings |
| `fonts` / `font_pack` | list / preset | Font set exposed to the page |
| `webrtc_mode` | `default` / `disable` / `public_only` / `force_proxy` | WebRTC IP exposure policy |
| `media_devices` | `default` / `random` / `empty` | Camera/microphone/speaker enumeration |
| `ua_ch_platform` / `ua_ch_mobile` | text / bool | User-Agent Client Hints (Chromium) |

### Proxy and advanced

| Field | Values | Meaning |
|---|---|---|
| `proxy.server` | `scheme://host:port` | Proxy endpoint (`http`, `socks5`, …) |
| `proxy.username` / `proxy.password` | text | Credentials; sealed at rest (DPAPI on Windows) |
| `proxy_id` | pool entry id | Use a proxy-pool entry instead of an inline proxy |
| `block_images` / `block_webrtc` / `block_webgl` / `disable_coop` / `enable_cache` | bool | Engine switches |
| `addons` | list of paths | Firefox add-on paths (Camoufox) |
| `extra_args` | list of strings | Extra browser launch arguments |

## FAQ / Troubleshooting

**The app opens but the Camoufox session immediately fails with a protocol error.**
Fixed in 1.6.1. Older builds hit a Playwright Juggler incompatibility (`Browser.setDefaultViewport` with an unsupported `isMobile` field). Upgrade to 1.6.1+; the session log should show `no_viewport` in the launch kwargs.

**"camoufox is not installed" when launching.**
Open **System → Camoufox** and click Install / Fetch, or run `python -m camoufox fetch` with the same Python environment. Corporate proxies may need `HTTPS_PROXY` set during the fetch.

**Chromium sessions fail to start.**
Install the browser for the selected backend: `patchright install chromium` (preferred) or `playwright install chromium`. Check the session log for the exact missing path.

**Linux: the GUI doesn't start / WebKit errors.**
Install `libwebkit2gtk-4.1-0` and `gir1.2-gtk-3.0`; or run headless with `./FoxDesk --serve 8765` and use a normal browser.

**macOS: "FoxDesk.app is damaged" or Gatekeeper blocks it.**
The build is unsigned. Use right-click → Open, or `xattr -cr /path/to/FoxDesk.app`. Homebrew cask template is in `tools/homebrew/`.

**Profiles stored on a network drive behave oddly.**
SMB/NAS paths can drop mid-session (the app retries and shows a readable warning), and startup is noticeably slower. Prefer local disk for `user_data_dir`.

**Update check is rate-limited.**
GitHub API limits unauthenticated requests. Set `FOXDESK_GITHUB_TOKEN` / `GITHUB_TOKEN`, or paste a read-only token under **System → Update settings**. The app also falls back to the web/Atom endpoint via ghproxy.

**Where is my data?**
`%APPDATA%\FoxDesk` on Windows (legacy `CamoufoxManager` folders are migrated automatically). Backups are password-encrypted `.fdk` files created from the System page.

**How do I switch the UI to English?**
It auto-detects on first launch; otherwise use the **中 / EN** toggle at the bottom-left of the sidebar. The choice is remembered.

## Security & threat model (read this)

FoxDesk is a **local desktop tool**:

| Item | Behavior |
|---|---|
| Listen address | `127.0.0.1` only (do not expose it on `0.0.0.0`) |
| API auth | Per-process random `X-FoxDesk-Token`, injected into the UI |
| Data storage | `%APPDATA%\FoxDesk` (legacy `CamoufoxManager` migrated) |
| Proxy passwords | Sealed locally (Windows DPAPI; machine-local obfuscation elsewhere) |
| Auto-update | ghproxy mirror by default; optional GitHub token; SHA256 verified when `SHA256SUMS` exists |

**Never** map this service to the internet. Local malware can still read the data directory.

## Environment-quality measurements (internal, not a guarantee)

2026-08-28 static fingerprint comparison (probes: webdriver / CDP traces / iframe·Worker consistency / notification consistency / UA-CH; see [docs/research/phase-d-gap-matrix.md](docs/research/phase-d-gap-matrix.md) §2.5–2.6):

- **FoxDesk Chromium (patchright) matched commercial GoLogin Orbita 150** on all automatable static probes (webdriver=false, no CDP Runtime traces, srcdoc iframe/Worker consistency, notification surface).
- Against a real Google Chrome 151 baseline, two stale UA-CH GREASE brand strings and `platformVersion` were fixed.
- These are static-layer measurements only and **do not constitute** any guarantee of passing checks, registration, payments or subscriptions. Known boundaries (version truncation, kernel-level differences) are in the gap matrix.

## Known limitations

- Server mode may still fail/delay to capture `ws_endpoint` with some Camoufox builds (use "Refresh endpoint")
- Fingerprint checks are static consistency scoring, **not** an anti-detect guarantee; Chromium + Patchright only reduces some automation markers
- Without a token you may still hit GitHub rate limits; 1.2.0+ falls back to web/Atom + ghproxy
- Session `evaluate` / screenshots are limited to the local control channel for browser mode — this is **not** a remote RPA sandbox
- Upgrading from very old versions: install 1.6.1 directly; uninstall any `Program Files` install first

Full changelog: [CHANGELOG.md](CHANGELOG.md).

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+ / FastAPI / Pydantic |
| Desktop shell | pywebview + Windows WebView2 |
| Frontend | Vanilla HTML/CSS/JS |
| Browsers | Camoufox (Firefox) + Chromium (Playwright / Patchright) |
| Data | `%APPDATA%\FoxDesk` (local JSON; legacy dirs migrated) |
| Packaging | PyInstaller + Inno Setup |
| CI/CD | GitHub Actions |

## Project layout

```
foxdesk/
├── desktop.py              # desktop launcher / frozen worker entry
├── backend/                # FastAPI + setup/update/proxy
├── static/                 # frontend
├── tools/                  # helper scripts
├── foxdesk.spec            # PyInstaller
├── installer.iss           # Inno Setup
└── .github/workflows/      # CI packaging & releases
```

## License

See [LICENSE](LICENSE).

## Updates & GitHub token

- **Default mirror**: ghproxy (switch to GitHub directly on the System page)
- **Optional token** (raises `api.github.com` quota, not required):
  1. Environment variable `FOXDESK_GITHUB_TOKEN` or `GITHUB_TOKEN` (recommended; never committed)
  2. Or paste a Personal Access Token under **System → Update settings** (sealed locally)
- **Never** commit a token or bundle one into an installer

Create a token (with your own GitHub account): https://github.com/settings/tokens
Only **public_repo** read access (classic) or fine-grained read-only Contents/Metadata on `BB0813/foxdesk` is needed.
