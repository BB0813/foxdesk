"""Unit tests for previously untested pure modules:
process_utils.parse_worker_event, netscape cookie parsing, DPAPI secret
round-trip, update version comparison, proxy line parsing."""

from __future__ import annotations

import pytest

from backend.app import _parse_netscape_cookies, _validate_task_args
from backend.process_utils import parse_worker_event
from backend.proxy_pool import normalize_proxy_server, parse_proxy_line
from backend.storage_util import is_protected_secret, protect_secret, unprotect_secret
from backend.update_manager import version_is_newer


class TestParseWorkerEvent:
    def test_valid_event(self):
        assert parse_worker_event('{"event":"ready","ws_endpoint":"ws://x"}') == {
            "event": "ready",
            "ws_endpoint": "ws://x",
        }

    def test_non_json(self):
        assert parse_worker_event("hello world") is None
        assert parse_worker_event("") is None

    def test_json_without_event_key(self):
        assert parse_worker_event('{"foo":1}') is None

    def test_json_array(self):
        assert parse_worker_event('[1,2]') is None

    def test_broken_json(self):
        assert parse_worker_event('{"event":') is None


class TestNetscapeCookies:
    def test_basic_line(self):
        rows = _parse_netscape_cookies(
            ".example.com\tTRUE\t/\tTRUE\t1735689600\tsid\tabc123"
        )
        assert rows == [
            {
                "domain": ".example.com",
                "host": ".example.com",
                "path": "/",
                "secure": True,
                "expires": 1735689600,
                "name": "sid",
                "value": "abc123",
                "httpOnly": True,  # dot-prefixed domain
            }
        ]

    def test_httponly_prefix(self):
        rows = _parse_netscape_cookies("#HttpOnly_.example.com\tTRUE\t/\tFALSE\t0\tk\tv")
        assert rows[0]["domain"] == ".example.com"
        assert rows[0]["httpOnly"] is True
        assert rows[0]["expires"] is None

    def test_comments_and_short_lines_skipped(self):
        text = "# comment\n\nshort\tline\n.example.com\tTRUE\t/\tFALSE\t0\ta\tb"
        rows = _parse_netscape_cookies(text)
        assert len(rows) == 1


class TestSecretRoundTrip:
    def test_protect_unprotect(self):
        sealed = protect_secret("s3cret-pw")
        assert sealed != "s3cret-pw"
        assert is_protected_secret(sealed)
        assert unprotect_secret(sealed) == "s3cret-pw"

    def test_empty_stays_empty(self):
        assert protect_secret("") == ""
        assert unprotect_secret("") == ""
        assert is_protected_secret("") is False

    def test_plaintext_passthrough(self):
        assert unprotect_secret("plain") == "plain"

    def test_idempotent_protect(self):
        once = protect_secret("pw")
        assert protect_secret(once) == once

    def test_garbage_sealed_value(self):
        assert unprotect_secret("enc:dpapi:not-base64!!") == ""


class TestVersionIsNewer:
    @pytest.mark.parametrize(
        "candidate,current,expected",
        [
            ("1.4.1", "1.4.0", True),
            ("1.4.0", "1.4.0", False),
            ("1.4.0", "1.4.1", False),
            ("1.10.0", "1.9.9", True),
            ("2.0.0", "1.9.9", True),
            ("1.4.0-beta.1", "1.3.2", True),
            ("1.4", "1.4.0", False),
        ],
    )
    def test_cases(self, candidate, current, expected):
        assert version_is_newer(candidate, current) is expected


class TestProxyParsing:
    def test_parse_line_full(self):
        row = parse_proxy_line("http://user:pass@1.2.3.4:8080")
        assert row["server"].startswith("http://1.2.3.4:8080")
        assert row["username"] == "user"

    def test_parse_line_bare(self):
        row = parse_proxy_line("1.2.3.4:8080")
        assert "1.2.3.4:8080" in row["server"]

    def test_normalize(self):
        assert "1.2.3.4:8080" in normalize_proxy_server("  1.2.3.4:8080  ")


class TestTaskArgsValidation:
    def test_ok_args(self):
        assert _validate_task_args(["--verbose", "camoufox==0.4.0"]) == ["--verbose", "camoufox==0.4.0"]

    def test_url_blocked(self):
        with pytest.raises(Exception):
            _validate_task_args(["--index-url", "http://evil.example.com/simple"])

    def test_dangerous_flag_blocked(self):
        with pytest.raises(Exception):
            _validate_task_args(["-e", "git+https://evil/x"])
        with pytest.raises(Exception):
            _validate_task_args(["--extra-index-url"])

    def test_weird_chars_blocked(self):
        with pytest.raises(Exception):
            _validate_task_args(["a;b"])
        with pytest.raises(Exception):
            _validate_task_args(["$(boom)"])
