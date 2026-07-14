# Changelog

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
