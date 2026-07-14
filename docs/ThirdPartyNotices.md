# Third-Party Notices (FoxDesk 1.4.0-dev)

This document summarizes third-party components relevant to the dual-engine
Chromium path. It is **not** legal advice. Recheck licenses before a formal
tagged release.

## Patchright

- Role: optional Chromium automation backend (`chromium_backend=auto|patchright`)
- License: Apache-2.0 (metadata for package 1.61.x)
- Notes: see `docs/research/phase-c-packaging.md`
- Browser binaries: downloaded by the user via `patchright install chromium`
  (not redistributed by FoxDesk by default)

## Playwright

- Role: Chromium automation fallback (`chromium_backend=playwright` or auto fallback)
- License: follow upstream Playwright / Microsoft notices
- Browser binaries: `playwright install chromium` (user machine cache)

## Google Chrome (optional channel)

- Role: optional `chromium_channel=chrome` when the user already has Chrome installed
- FoxDesk does **not** redistribute the Chrome installer

## Camoufox

- Role: Firefox-based engine (primary historical path)
- Follow existing Camoufox / project packaging notices

## Disclaimer

FoxDesk is a local fingerprint workstation. Nothing in this product or in these
notices is a guarantee of anti-detect success, signup success, subscription
success, or parity with commercial products such as Multilogin or GoLogin.
