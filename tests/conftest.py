"""Shared fixtures for the test suite.

These fixtures isolate every test from the user's real `.env`/`config.toml`
and provide an HTTP mock via the `responses` library.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import responses as _responses

from canvas_conductor import config as cfg_module


TEST_BASE_URL = "https://test.instructure.com"
TEST_TOKEN = "test-token-12345"
API_ROOT = f"{TEST_BASE_URL}/api/v1"


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path, monkeypatch):
    """Pin CWD to a tmp dir so config lookup never finds the real config.toml.

    Tests that want a real config can write their own config.toml/.env to
    `tmp_path` before invoking commands.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CANVAS_BASE_URL", TEST_BASE_URL)
    monkeypatch.setenv("CANVAS_TOKEN", TEST_TOKEN)
    cfg_module.reset_caches()
    yield
    cfg_module.reset_caches()


@pytest.fixture
def write_config(tmp_path: Path):
    """Write a `config.toml` to the tmp CWD and reset the loader cache."""

    def _write(content: str) -> Path:
        path = tmp_path / "config.toml"
        path.write_text(content)
        cfg_module.reset_caches()
        return path

    return _write


@pytest.fixture
def mock_responses():
    """Yield an active `responses.RequestsMock` for the test."""
    with _responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


@pytest.fixture
def api():
    """Return the API root URL string for assembling test URLs."""
    return API_ROOT
