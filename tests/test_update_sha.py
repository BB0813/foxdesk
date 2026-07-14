from __future__ import annotations

from backend.update_manager import parse_sha256sums


def test_parse_sha256sums_lowercases_keys() -> None:
    digest_a = "a" * 64
    digest_b = "b" * 64
    text = f"{digest_a}  FoxDesk-Setup.exe\n{digest_b} *Other.ZIP\n"
    mapping = parse_sha256sums(text)
    assert mapping["foxdesk-setup.exe"] == digest_a
    assert mapping["other.zip"] == digest_b
