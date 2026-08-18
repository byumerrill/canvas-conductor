"""Tests for the playbook extension's per-course config resolver.

These don't exercise any Canvas API calls; they only validate that the
helper functions read from `[courses.<alias>.playbook]` correctly and
fall back / error in the right ways.
"""
from __future__ import annotations

import pytest

from canvas_conductor import config as cfg_module
from canvas_conductor.exceptions import ConfigError
from canvas_conductor.extensions import playbook as pb


def test_per_course_section_resolves_explicit_alias(write_config, tmp_path):
    content_dir = (tmp_path / "content").resolve()
    local_media_cache = (tmp_path / "cache").resolve()
    media_urls_file = (tmp_path / "media-urls.toml").resolve()
    write_config(
        f"""
[courses.is-career-playbook]
id = 35416

[courses.is-career-playbook.playbook]
content_dir = "{content_dir.as_posix()}"
local_media_cache = "{local_media_cache.as_posix()}"
media_urls_file = "{media_urls_file.as_posix()}"
"""
    )
    paths = pb._playbook_paths("is-career-playbook")
    assert paths["content_dir"] == content_dir
    assert paths["local_media_cache"] == local_media_cache
    assert paths["media_urls_file"] == media_urls_file
    assert paths["canvas_media_folder"] == "playbook-media"  # default


def test_per_course_schedule_resolves_explicit_alias(write_config):
    write_config(
        """
[courses.is-career-playbook]
id = 35416

[courses.is-career-playbook.playbook.schedule]
week_1_page = "2026-09-08"
week_2_page = "2026-09-15"
"""
    )
    sched = pb._playbook_schedule("is-career-playbook")
    assert sched == {
        "week_1_page": "2026-09-08",
        "week_2_page": "2026-09-15",
    }


def test_alias_auto_resolves_when_only_one_course_has_playbook(write_config):
    write_config(
        """
[courses.is566]
id = 33431

[courses.is-career-playbook]
id = 35416

[courses.is-career-playbook.playbook]
content_dir = "/abs/content"
"""
    )
    # Only is-career-playbook has a playbook block, so course=None should pick it.
    assert pb._resolve_playbook_alias(None) == "is-career-playbook"


def test_alias_resolution_errors_when_multiple_have_playbook(write_config):
    write_config(
        """
[courses.a]
id = 1
[courses.a.playbook]
content_dir = "/a"

[courses.b]
id = 2
[courses.b.playbook]
content_dir = "/b"
"""
    )
    with pytest.raises(ConfigError) as exc:
        pb._resolve_playbook_alias(None)
    assert "Multiple courses" in str(exc.value)


def test_alias_resolution_errors_when_no_course_has_playbook(write_config):
    write_config(
        """
[courses.is566]
id = 33431
"""
    )
    with pytest.raises(ConfigError) as exc:
        pb._resolve_playbook_alias(None)
    assert "playbook" in str(exc.value)


def test_unknown_alias_raises(write_config):
    write_config(
        """
[courses.is566]
id = 33431
"""
    )
    with pytest.raises(ConfigError) as exc:
        pb._resolve_playbook_alias("nope")
    assert "not found" in str(exc.value)


def test_relative_paths_resolve_against_config_file(tmp_path, monkeypatch):
    """A relative path in [playbook] resolves relative to config.toml's dir."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        """
[courses.is-career-playbook]
id = 35416

[courses.is-career-playbook.playbook]
content_dir = "../content"
"""
    )
    # Pretend we're invoking from somewhere unrelated; loader walk-up should
    # find this config because tmp_path is our cwd.
    cfg_module.reset_caches()
    paths = pb._playbook_paths("is-career-playbook")
    assert str(paths["content_dir"]) == str((tmp_path.parent / "content").resolve())
