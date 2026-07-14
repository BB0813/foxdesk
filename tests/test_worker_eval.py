from __future__ import annotations

import pytest

from backend.camoufox_worker import validate_evaluate_expression, validate_nav_url


def test_validate_evaluate_expression_ok() -> None:
    assert validate_evaluate_expression("document.title") == "document.title"
    assert validate_evaluate_expression("  location.href  ") == "location.href"


def test_validate_evaluate_expression_rejects_empty() -> None:
    with pytest.raises(ValueError):
        validate_evaluate_expression("   ")


def test_validate_evaluate_expression_rejects_long() -> None:
    with pytest.raises(ValueError):
        validate_evaluate_expression("x" * 1501)


def test_validate_evaluate_expression_rejects_banned_tokens() -> None:
    with pytest.raises(ValueError):
        validate_evaluate_expression("import('fs')")
    with pytest.raises(ValueError):
        validate_evaluate_expression("require('child_process')")
    with pytest.raises(ValueError):
        validate_evaluate_expression("__import__('os')")


def test_validate_nav_url_still_ok() -> None:
    assert validate_nav_url("https://example.com") == "https://example.com"
