"""Tests for the HTTP client: pagination, errors, rate limiting, retries."""
from __future__ import annotations

import pytest
import responses

from canvas_conductor import client as client_module
from canvas_conductor.client import CanvasClient
from canvas_conductor.exceptions import (
    CanvasAuthError,
    CanvasNotFoundError,
    CanvasPermissionError,
    CanvasRateLimitError,
    CanvasServerError,
    CanvasValidationError,
)


def make_client(verbose: bool = False) -> CanvasClient:
    return CanvasClient("https://test.instructure.com", "tok", verbose=verbose)


class TestBasicMethods:
    def test_get_returns_json(self, mock_responses, api):
        mock_responses.get(f"{api}/courses/1", json={"id": 1, "name": "Test"})
        c = make_client()
        result = c.get("/courses/1")
        assert result == {"id": 1, "name": "Test"}

    def test_post_sends_json(self, mock_responses, api):
        def echo(request):
            return (201, {}, request.body)

        mock_responses.add_callback(
            responses.POST,
            f"{api}/courses/1/modules",
            callback=echo,
            content_type="application/json",
        )
        c = make_client()
        result = c.post("/courses/1/modules", data={"name": "M1"})
        assert result == {"name": "M1"}

    def test_put_updates(self, mock_responses, api):
        mock_responses.put(f"{api}/courses/1", json={"id": 1, "name": "X"})
        c = make_client()
        result = c.put("/courses/1", {"course[name]": "X"})
        assert result["name"] == "X"

    def test_delete_returns_true(self, mock_responses, api):
        mock_responses.delete(f"{api}/courses/1/modules/5", status=204)
        c = make_client()
        assert c.delete("/courses/1/modules/5") is True


class TestPagination:
    def test_get_all_follows_link_next(self, mock_responses, api):
        page1 = [{"id": 1}, {"id": 2}]
        page2 = [{"id": 3}]
        mock_responses.get(
            f"{api}/courses/1/modules",
            json=page1,
            headers={
                "Link": (
                    f'<{api}/courses/1/modules?page=2>; rel="next", '
                    f'<{api}/courses/1/modules?page=1>; rel="first"'
                )
            },
        )
        mock_responses.get(
            f"{api}/courses/1/modules?page=2",
            json=page2,
        )
        c = make_client()
        out = c.get_all("/courses/1/modules")
        assert [m["id"] for m in out] == [1, 2, 3]

    def test_get_all_no_link_header(self, mock_responses, api):
        mock_responses.get(f"{api}/foo", json=[{"id": 1}])
        c = make_client()
        assert c.get_all("/foo") == [{"id": 1}]

    def test_get_all_dict_response_passes_through(self, mock_responses, api):
        mock_responses.get(f"{api}/foo", json={"id": 1})
        c = make_client()
        assert c.get_all("/foo") == [{"id": 1}]


class TestErrors:
    @pytest.mark.parametrize(
        "status,exc",
        [
            (401, CanvasAuthError),
            (403, CanvasPermissionError),
            (404, CanvasNotFoundError),
            (422, CanvasValidationError),
        ],
    )
    def test_error_mapping(self, mock_responses, api, status, exc):
        mock_responses.get(
            f"{api}/courses/99",
            json={"errors": [{"message": "boom"}]},
            status=status,
        )
        c = make_client()
        with pytest.raises(exc) as excinfo:
            c.get("/courses/99")
        assert excinfo.value.status_code == status
        assert "boom" in str(excinfo.value)

    def test_extract_message_with_dict_errors(self):
        body = {"errors": {"name": [{"message": "is required"}]}}
        msg = CanvasClient._extract_message(body)
        assert "name" in msg and "is required" in msg

    def test_extract_message_fallback_to_text(self):
        msg = CanvasClient._extract_message("plain text problem")
        assert msg == "plain text problem"


class TestRetryAndRateLimit:
    def test_retry_on_429_then_success(self, mock_responses, api, monkeypatch):
        # Speed the test up; don't actually sleep between retries.
        monkeypatch.setattr(client_module, "RETRY_BACKOFF_BASE", 0)
        mock_responses.get(f"{api}/foo", status=429, json={"errors": ["slow"]})
        mock_responses.get(f"{api}/foo", status=200, json={"ok": True})
        c = make_client()
        assert c.get("/foo") == {"ok": True}

    def test_retry_exhausted_raises_rate_limit(self, mock_responses, api, monkeypatch):
        monkeypatch.setattr(client_module, "RETRY_BACKOFF_BASE", 0)
        for _ in range(4):  # initial + 3 retries
            mock_responses.get(f"{api}/foo", status=429, json={"errors": ["slow"]})
        c = make_client()
        with pytest.raises(CanvasRateLimitError):
            c.get("/foo")

    def test_retry_on_500_then_success(self, mock_responses, api, monkeypatch):
        monkeypatch.setattr(client_module, "RETRY_BACKOFF_BASE", 0)
        mock_responses.get(f"{api}/foo", status=500, json={"error": "oops"})
        mock_responses.get(f"{api}/foo", status=200, json={"ok": True})
        c = make_client()
        assert c.get("/foo") == {"ok": True}

    def test_500_exhausted_raises_server_error(self, mock_responses, api, monkeypatch):
        monkeypatch.setattr(client_module, "RETRY_BACKOFF_BASE", 0)
        for _ in range(4):
            mock_responses.get(f"{api}/foo", status=500, json={})
        c = make_client()
        with pytest.raises(CanvasServerError):
            c.get("/foo")

    def test_low_rate_limit_triggers_sleep(self, mock_responses, api, monkeypatch):
        sleeps: list[float] = []
        monkeypatch.setattr(client_module.time, "sleep", lambda s: sleeps.append(s))
        mock_responses.get(
            f"{api}/foo",
            json={"ok": True},
            headers={"x-rate-limit-remaining": "10"},
        )
        c = make_client()
        c.get("/foo")
        assert any(s > 0 for s in sleeps), "expected a sleep when budget is low"


class TestNextLinkParser:
    def test_extracts_next_url(self):
        link = '<https://x/api/v1/foo?page=2>; rel="next", <...>; rel="last"'

        class FakeResp:
            headers = {"Link": link}

        assert CanvasClient._next_link(FakeResp()) == "https://x/api/v1/foo?page=2"

    def test_returns_none_when_no_next(self):
        class FakeResp:
            headers = {"Link": '<x>; rel="last"'}

        assert CanvasClient._next_link(FakeResp()) is None

    def test_handles_empty_header(self):
        class FakeResp:
            headers = {}

        assert CanvasClient._next_link(FakeResp()) is None
