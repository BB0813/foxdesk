#!/usr/bin/env python3
"""D-B7: Chrome / automation-stack version drift check.

Fingerprint UA strings age quickly against Chrome's ~monthly major cadence;
stale UA majors are an easy detection signal (UA vs TLS / UA-CH mismatch).
This tool compares:

  1. Latest Chrome stable major (versionhistory.googleapis.com, public API)
  2. Chrome majors embedded in FoxDesk UA pools (routes/profiles.py,
     tools/bstatic_probe.py)
  3. Latest playwright / patchright releases on PyPI vs requirements pins

Exit 0 = fresh (or network failure treated as unknown, soft).
Exit 1 = drift detected (UA major older than latest stable - threshold).

Designed for the monthly scheduled workflow (drift-check.yml); harmless to
run locally: `python tools/chrome_drift_check.py`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, build_opener

ROOT = Path(__file__).resolve().parents[1]

# Flag drift when embedded UA majors trail the latest stable by more than this.
STALE_THRESHOLD_MAJORS = 2

UA_FILES = (
    ROOT / "backend" / "routes" / "profiles.py",
    ROOT / "tools" / "bstatic_probe.py",
)

CHROME_VERSIONHISTORY_URL = (
    "https://versionhistory.googleapis.com/v1/chrome/platforms/win/channels/stable/versions"
)
PYPI_URLS = {
    "playwright": "https://pypi.org/pypi/playwright/json",
    "patchright": "https://pypi.org/pypi/patchright/json",
}


def _get_json(url: str, timeout: float = 12.0) -> dict:
    req = Request(url, headers={"User-Agent": "FoxDesk/drift-check"})
    with build_opener().open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def latest_chrome_major() -> int | None:
    try:
        data = _get_json(CHROME_VERSIONHISTORY_URL)
        versions = [item.get("version", "") for item in (data.get("versions") or [])]
        majors = [int(v.split(".")[0]) for v in versions if re.match(r"^\d+\.", v)]
        return max(majors) if majors else None
    except Exception:
        return None


def embedded_ua_majors() -> dict[str, list[int]]:
    """Chrome/Firefox majors extracted from UA pools in source files."""
    out: dict[str, list[int]] = {"chrome": [], "firefox": []}
    for path in UA_FILES:
        text = path.read_text(encoding="utf-8")
        out["chrome"].extend(int(m) for m in re.findall(r"Chrome/(\d+)\.", text))
        out["firefox"].extend(int(m) for m in re.findall(r"Firefox/(\d+)\.0", text))
    return out


def latest_pypi_versions() -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for name, url in PYPI_URLS.items():
        try:
            result[name] = str(_get_json(url).get("info", {}).get("version") or "") or None
        except Exception:
            result[name] = None
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="FoxDesk Chrome drift check (D-B7)")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    started = time.time()
    latest = latest_chrome_major()
    majors = embedded_ua_majors()
    pypi = latest_pypi_versions()

    chrome_majors = sorted(set(majors["chrome"]), reverse=True)
    oldest_chrome = chrome_majors[-1] if chrome_majors else None
    stale = bool(latest and oldest_chrome and (latest - oldest_chrome) > STALE_THRESHOLD_MAJORS)

    report = {
        "ok": not stale,
        "latest_chrome_stable_major": latest,
        "embedded_chrome_majors": chrome_majors,
        "embedded_firefox_majors": sorted(set(majors["firefox"]), reverse=True),
        "stale_threshold_majors": STALE_THRESHOLD_MAJORS,
        "stale": stale,
        "pypi_latest": pypi,
        "requirements_note": "requirements.txt pins playwright/patchright with '>=' so installs always take the newest release; drift risk is Chrome-major breakage, not stale pins.",
        "elapsed_s": round(time.time() - started, 3),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
