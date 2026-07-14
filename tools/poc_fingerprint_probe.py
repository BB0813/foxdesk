"""Shared in-page fingerprint probe for Phase 0 PoCs.

Returns a JSON-serializable dict of browser-facing signals.
"""

from __future__ import annotations

PROBE_JS = """
() => {
  const out = {};
  const nav = navigator || {};
  out.userAgent = nav.userAgent || '';
  out.platform = nav.platform || '';
  out.language = nav.language || '';
  out.languages = Array.from(nav.languages || []);
  out.webdriver = !!nav.webdriver;
  out.hardwareConcurrency = nav.hardwareConcurrency || 0;
  out.deviceMemory = nav.deviceMemory || null;
  out.maxTouchPoints = nav.maxTouchPoints || 0;
  out.vendor = nav.vendor || '';
  out.pluginsLength = (nav.plugins && nav.plugins.length) || 0;

  try {
    if (nav.userAgentData && nav.userAgentData.brands) {
      out.uaChBrands = nav.userAgentData.brands.map(b => ({
        brand: b.brand,
        version: b.version,
      }));
      out.uaChMobile = !!nav.userAgentData.mobile;
      out.uaChPlatform = nav.userAgentData.platform || '';
    } else {
      out.uaChBrands = null;
    }
  } catch (e) {
    out.uaChError = String(e);
  }

  const s = window.screen || {};
  out.screen = {
    width: s.width || 0,
    height: s.height || 0,
    colorDepth: s.colorDepth || 0,
    availWidth: s.availWidth || 0,
    availHeight: s.availHeight || 0,
  };

  try {
    out.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
  } catch (e) {
    out.timezone = '';
  }

  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (gl) {
      const dbg = gl.getExtension('WEBGL_debug_renderer_info');
      out.webglVendor = dbg ? (gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) || '') : '';
      out.webglRenderer = dbg ? (gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) || '') : '';
    }
  } catch (e) {
    out.webglError = String(e);
  }

  out.hasChromeRuntime = typeof window.chrome === 'object' && window.chrome !== null;
  out.href = location.href || '';
  return out;
}
"""


def probe_page(page) -> dict:
    return page.evaluate(PROBE_JS)
