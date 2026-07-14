from __future__ import annotations

from backend.app import Profile, ProxyConfig, environment_risks_for_profile


def _base(**kwargs):
    data = dict(
        id="p1",
        name="t",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        mode="browser",
        os="windows",
        headless=False,
        persistent_context=True,
        humanize=True,
        geoip=True,
        block_webrtc=True,
        webrtc_mode="disable",
        locale="en-US",
        timezone="America/New_York",
        proxy=ProxyConfig(server="socks5://1.2.3.4:1080"),
    )
    data.update(kwargs)
    return Profile(**data)


def test_payment_like_profile_has_no_high_risks():
    risks = environment_risks_for_profile(_base())
    high = [r for r in risks if r["level"] == "high"]
    assert high == []


def test_proxy_without_geoip_is_high():
    risks = environment_risks_for_profile(_base(geoip=False))
    codes = {r["code"] for r in risks if r["level"] == "high"}
    assert "proxy_without_geoip" in codes


def test_headless_is_high():
    risks = environment_risks_for_profile(_base(headless=True))
    codes = {r["code"] for r in risks if r["level"] == "high"}
    assert "headless" in codes
