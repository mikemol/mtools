# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""mikemol-gmail's real effects, each run against a local stand-in, and consent end to end."""

from __future__ import annotations

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING, override
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from mikemol.gmailstruct import cli
from mikemol.gmailstruct.consent import ConsentError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

# ⚑ SYNTHETIC: planted values, so a test can look for them where they must not be.
_REFRESH = "1//planted-refresh-token-0f2a"
_SECRET = "planted-client-secret-77c1"
_CODE = "4/planted-auth-code-5d3e"
_OK = 200
_BAD_REQUEST = 400
# ⚑ EVERY WAIT HERE IS BOUNDED, UNDER ANY ONE MUTATION. Helper threads are daemons joined with a
# limit, so a mutant that makes the listener or a request block fails its test instead of hanging
# the mutation grid (measured W356: //gmailstruct:mutants hit its 300 s limit before this).
_JOIN_S = 5.0


def _dumps(value: object) -> str:
    return json.dumps(value)


def _spawn(target: Callable[[], object]) -> threading.Thread:
    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return thread


def _fake_age(tmp_path: Path, status: int = 0) -> str:
    """Write an `age` stand-in that copies stdin to its --output argument and exits `status`.

    Returns:
        the stand-in's path. Its argv is `--encrypt --recipient R --output OUT`, so OUT is $5.

    """
    script = tmp_path / "age"
    script.write_text(f'#!/bin/sh\ncat > "$5"\nexit {status}\n', encoding="utf-8")
    script.chmod(0o755)
    return str(script)


def _get(url: str) -> bytes:
    parts = urlsplit(url)
    conn = http.client.HTTPConnection(parts.hostname or "", parts.port, timeout=_JOIN_S)
    try:
        conn.request("GET", f"{parts.path or '/'}?{parts.query}")
        return conn.getresponse().read()
    finally:
        conn.close()


def test_age_encrypt_pipes_the_token_to_age(tmp_path: Path) -> None:
    """The token reaches age on stdin with the recipient and output it was given."""
    out = tmp_path / "token.age"
    cli.age_encrypt("age1recipient", out, _fake_age(tmp_path))(_REFRESH)
    assert out.read_text(encoding="utf-8") == _REFRESH


def test_failed_age_is_an_error_carrying_no_token(tmp_path: Path) -> None:
    """When age fails, the error names the output and the exit status, never the token."""
    out = tmp_path / "token.age"
    with pytest.raises(ConsentError, match="exit 3") as caught:
        cli.age_encrypt("age1recipient", out, _fake_age(tmp_path, 3))(_REFRESH)
    assert _REFRESH not in str(caught.value)


def test_listener_returns_the_redirects_code_and_state(capsys: pytest.CaptureFixture[str]) -> None:
    """The redirect yields its code and state, the browser gets the close page, nothing is logged.

    The page is checked too: a request that fails after the code is read (a log call that raises,
    say) still hands back the code, and only the browser's side shows the response never came.
    """
    redirect, await_code = cli.listen(0, _JOIN_S)
    url = f"{redirect}/?{urlencode({'code': _CODE, 'state': 's1'})}"
    pages: list[bytes] = []
    getter = _spawn(lambda: pages.append(_get(url)))
    assert await_code() == (_CODE, "s1")
    getter.join(_JOIN_S)
    assert pages == [b"Consent received. You can close this tab."]
    assert _CODE not in capsys.readouterr().err


def test_open_browser_prints_the_url_and_opens_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The URL is printed, so it can be opened by hand, and handed to the default browser."""
    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", opened.append)
    cli.open_browser("https://accounts.example.invalid/auth?x=1")
    assert opened == ["https://accounts.example.invalid/auth?x=1"]
    assert "https://accounts.example.invalid/auth?x=1" in capsys.readouterr().err


def test_abandoned_consent_ends_the_wait_instead_of_hanging() -> None:
    """With no redirect in time the wait returns empty code and state, which consent refuses."""
    _redirect, await_code = cli.listen(0, 0.2)
    seen: list[tuple[str, str]] = []
    _spawn(lambda: seen.append(await_code())).join(_JOIN_S)
    assert seen == [("", "")]


class _Token(BaseHTTPRequestHandler):
    """A local token endpoint: echoes the form back in a 400, so the test can read it."""

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = _dumps({"form": self.rfile.read(length).decode()}).encode()
        self.send_response(_BAD_REQUEST)
        self.end_headers()
        self.wfile.write(body)

    @override
    def log_message(self, fmt: str, *args: object) -> None:
        del fmt, args


def test_post_form_returns_status_and_body_of_an_error() -> None:
    """A 400 comes back as (400, body) rather than raising, so consent can name the status."""
    server = HTTPServer(("127.0.0.1", 0), _Token)
    serving = _spawn(server.handle_request)
    status, body = cli.post_form(f"http://127.0.0.1:{server.server_address[1]}/token", {"a": "1"})
    serving.join(_JOIN_S)
    server.server_close()
    assert (status, body) == (_BAD_REQUEST, b'{"form": "a=1"}')


@pytest.mark.parametrize("url", ["http://example.invalid/token", "ftp://127.0.0.1/token", "token"])
def test_post_form_refuses_anything_but_https_or_loopback_http(url: str) -> None:
    """Plain HTTP is allowed only to 127.0.0.1; other schemes and hosts are refused unsent."""
    with pytest.raises(ConsentError, match="refusing"):
        cli.post_form(url, {})


def _client(tmp_path: Path) -> Path:
    path = tmp_path / "client.json"
    data = {"installed": {"client_id": "id.apps.googleusercontent.com", "client_secret": _SECRET}}
    path.write_text(_dumps(data), encoding="utf-8")
    return path


def _follow(url: str) -> None:
    """Stand in for a browser: consent at once, requesting the redirect with the page's state."""
    query = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
    target = f"{query['redirect_uri']}/?{urlencode({'code': _CODE, 'state': query['state']})}"
    _spawn(lambda: _get(target))


def _issue(url: str, form: dict[str, str]) -> tuple[int, bytes]:
    del url, form
    return _OK, _dumps({"refresh_token": _REFRESH}).encode()


def test_consent_command_writes_the_token_only_through_age(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """End to end: the token is handed to age for --out, and never printed."""
    out = tmp_path / "token.age"
    argv = ["consent", "--client", str(_client(tmp_path)), "--recipient", "age1r"]
    argv += ["--out", str(out), "--age", _fake_age(tmp_path), "--timeout", "5"]
    assert cli.main(argv, browser=_follow, post=_issue) == 0
    assert out.read_text(encoding="utf-8") == _REFRESH
    printed = capsys.readouterr()
    assert _REFRESH not in printed.out + printed.err
    assert "wrote" in printed.err


def test_existing_out_is_refused_before_anything_runs(tmp_path: Path) -> None:
    """A token file already present is never overwritten; no browser opens."""
    out = tmp_path / "token.age"
    out.write_text("old", encoding="utf-8")
    opened: list[str] = []
    argv = ["consent", "--client", str(_client(tmp_path)), "--recipient", "r", "--out", str(out)]
    argv += ["--timeout", "2"]
    assert cli.main(argv, browser=opened.append, post=_issue) == 1
    assert opened == []
    assert out.read_text(encoding="utf-8") == "old"
