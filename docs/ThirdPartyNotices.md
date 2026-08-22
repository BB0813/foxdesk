# Third-Party Notices (FoxDesk)

This document lists third-party components bundled with or used by FoxDesk.
It is **not** legal advice. Recheck licenses before a formal tagged release.

## Bundled / distributed components

| Component | License | Role |
|---|---|---|
| Camoufox | MIT — https://camoufox.com/python | Firefox-based engine (primary) |
| Playwright | Apache-2.0 — https://github.com/Microsoft/playwright-python | Chromium automation fallback |
| Patchright | Apache-2.0 — https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python | Patched Chromium backend (auto-preferred) |
| BrowserForge | Apache-2.0 — https://github.com/daijro/browserforge | Fingerprint generation (bundled data) |
| apify_fingerprint_datapoints | Apache-2.0 — https://docs.apify.com/academy/anti-scraping/techniques/fingerprinting | Bayesian network data zips (bundled) |
| pywebview | BSD 3-Clause — https://pywebview.flowrl.com | Desktop shell |
| pythonnet / clr_loader | MIT — https://github.com/pythonnet/pythonnet | .NET bridge for WebView2 shell |
| certifi | MPL-2.0 | CA bundle |

Notes:
- Playwright/Patchright **browser binaries are NOT bundled** — downloaded by
  the user via `playwright install chromium` / `patchright install chromium`.
- Google Chrome (optional `chromium_channel=chrome`) is user-installed
  machine software; FoxDesk does **not** redistribute the Chrome installer.

## Other runtime dependencies

FastAPI/Starlette/Pydantic (MIT), uvicorn (BSD), requests (Apache-2.0),
Pillow (MIT-CMU), pystray (LGPL-3.0), and their transitive dependencies as
published on PyPI.

## Disclaimer

FoxDesk is a local fingerprint workstation. Nothing in this product or in
these notices is a guarantee of anti-detect success, signup success,
subscription success, or parity with commercial products such as Multilogin
or GoLogin.
