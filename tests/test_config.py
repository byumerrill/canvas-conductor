"""Tests for the config loader and course resolution."""
from __future__ import annotations

import pytest

from canvas_conductor import config as cfg
from canvas_conductor.exceptions import ConfigError


def test_get_course_id_with_single_course(write_config):
    write_config(
        """
[courses.is402]
id = 35416
name = "IS 402"
"""
    )
    assert cfg.get_course_id(None) == 35416


def test_get_course_id_explicit(write_config):
    write_config(
        """
[courses.a]
id = 100
[courses.b]
id = 200
"""
    )
    assert cfg.get_course_id("b") == 200


def test_get_course_id_missing_raises(write_config):
    write_config(
        """
[courses.a]
id = 100
[courses.b]
id = 200
"""
    )
    with pytest.raises(ConfigError) as exc:
        cfg.get_course_id(None)
    assert "Multiple courses" in str(exc.value)


def test_get_course_id_unknown_key(write_config):
    write_config(
        """
[courses.a]
id = 100
"""
    )
    with pytest.raises(ConfigError) as exc:
        cfg.get_course_id("nope")
    assert "not found" in str(exc.value)


def test_get_course_id_no_config():
    with pytest.raises(ConfigError) as exc:
        cfg.get_course_id(None)
    assert "No courses are configured" in str(exc.value)


def test_require_credentials_missing(monkeypatch):
    monkeypatch.delenv("CANVAS_BASE_URL", raising=False)
    monkeypatch.delenv("CANVAS_TOKEN", raising=False)
    cfg.reset_caches()
    with pytest.raises(ConfigError) as exc:
        cfg.require_credentials()
    assert "CANVAS_BASE_URL" in str(exc.value)
    assert "CANVAS_TOKEN" in str(exc.value)


def test_require_credentials_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("CANVAS_BASE_URL", "https://example.com/")
    monkeypatch.setenv("CANVAS_TOKEN", " mytoken ")
    cfg.reset_caches()
    base, token = cfg.require_credentials()
    assert base == "https://example.com"
    assert token == "mytoken"


def test_redact_token():
    assert cfg.redact_token("") == ""
    assert cfg.redact_token("short") == "***"
    assert cfg.redact_token("7407~vCBu7Tuef") == "7407...Tuef"


def test_get_defaults(write_config):
    write_config(
        """
[defaults]
output_format = "json"
"""
    )
    assert cfg.get_defaults() == {"output_format": "json"}


def test_get_courses_when_none_configured(write_config):
    write_config(
        """
[defaults]
output_format = "table"
"""
    )
    assert cfg.get_courses() == {}


def test_conductor_config_env_var_override(tmp_path, monkeypatch):
    """CONDUCTOR_CONFIG should take precedence over the walk-up search."""
    external = tmp_path / "external.toml"
    external.write_text(
        """
[courses.foo]
id = 4242
name = "Foo 101"
"""
    )
    monkeypatch.setenv("CONDUCTOR_CONFIG", str(external))
    cfg.reset_caches()
    assert cfg.get_course_id("foo") == 4242


def test_conductor_config_env_var_missing_file(tmp_path, monkeypatch):
    """CONDUCTOR_CONFIG pointing at a non-existent file should raise."""
    monkeypatch.setenv("CONDUCTOR_CONFIG", str(tmp_path / "nope.toml"))
    cfg.reset_caches()
    with pytest.raises(ConfigError) as exc:
        cfg.find_config_file()
    assert "CONDUCTOR_CONFIG" in str(exc.value)
