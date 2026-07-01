"""The Exception->500 handler runs outside CORSMiddleware, so it must attach CORS headers
itself; otherwise a real server error reaches the browser as a misleading CORS error."""

import types

from starlette.requests import Request

from src.core import exception_handlers


def _request(origin: str | None) -> Request:
    headers = [(b"origin", origin.encode())] if origin else []
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/x",
        "headers": headers,
        "query_string": b"",
    }
    return Request(scope)


def _patch_cors(monkeypatch, origins: list[str]) -> None:
    # BACKEND_CORS_ORIGINS is a computed property with no setter, so swap the module's whole
    # config reference for a namespace exposing just what the handler reads.
    monkeypatch.setattr(
        exception_handlers,
        "config",
        types.SimpleNamespace(BACKEND_CORS_ORIGINS=origins, DEBUG=False),
    )


def test_500_carries_cors_headers_for_an_allowed_origin(monkeypatch):
    _patch_cors(monkeypatch, ["https://app.example"])
    resp = exception_handlers.global_exception_handler(
        _request("https://app.example"), RuntimeError("boom")
    )
    assert resp.status_code == 500
    assert resp.headers["access-control-allow-origin"] == "https://app.example"
    assert resp.headers["access-control-allow-credentials"] == "true"


def test_500_mirrors_wildcard_cors(monkeypatch):
    _patch_cors(monkeypatch, ["*"])
    resp = exception_handlers.global_exception_handler(
        _request("https://any.example"), RuntimeError("boom")
    )
    assert resp.headers["access-control-allow-origin"] == "*"


def test_500_without_origin_has_no_cors_header(monkeypatch):
    _patch_cors(monkeypatch, ["https://app.example"])
    resp = exception_handlers.global_exception_handler(
        _request(None), RuntimeError("boom")
    )
    assert "access-control-allow-origin" not in resp.headers


def test_500_disallowed_origin_gets_no_cors_header(monkeypatch):
    _patch_cors(monkeypatch, ["https://app.example"])
    resp = exception_handlers.global_exception_handler(
        _request("https://evil.example"), RuntimeError("boom")
    )
    assert "access-control-allow-origin" not in resp.headers
