# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-gmail`: the real effects behind the tested auth logic (W356).

`mikemol-gmail consent --client CLIENT.json --recipient AGE1YUBIKEY... --out TOKEN.age` is the
operator's one-time act (W290). It opens Google's consent page, catches the redirect on a one-shot
127.0.0.1 listener, exchanges the code, and pipes the refresh token into
`age --encrypt --recipient R --output TOKEN.age`. The token is never printed or stored in clear.

⚑ THIS MODULE IS ONLY EFFECTS. The flow, its checks and its redaction live in consent.py and are
tested there with fakes. Here each effect is one small function, tested against a local stand-in:
a fake `age`, a local HTTP server, a simulated redirect.

⚑ AN EXISTING --out IS REFUSED BEFORE ANYTHING RUNS. A second consent never overwrites a token
file; the operator removes the old one on purpose.

⚑ THE POST SPEAKS HTTPS, and plain HTTP only to 127.0.0.1 (the tests' local server). It uses
http.client, which is typed, rather than urllib, whose response is untyped.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, override
from urllib.parse import parse_qs, urlencode, urlsplit

from mikemol.gmailstruct.auth import DecryptError, ExchangeError, decrypt, exchange
from mikemol.gmailstruct.consent import ConsentError, consent, read_client
from mikemol.gmailstruct.fetch import FetchError, raw, search, show
from mikemol.gmailstruct.records import Listed, Message, Unreadable

if TYPE_CHECKING:
    from mikemol.gmailstruct.auth import Poster, Runner
    from mikemol.gmailstruct.consent import AwaitCode, Browser, Encrypt
    from mikemol.gmailstruct.fetch import Getter

_TIMEOUT_S = 30
# A YubiKey decrypt waits for a touch, so it gets longer than a network call.
_TOUCH_S = 120
_CLOSE_PAGE = b"Consent received. You can close this tab."
_LOOPBACK = "127.0.0.1"


def open_browser(url: str) -> None:
    """Print the consent URL, so it can be opened by hand, then try the default browser."""
    sys.stderr.write(f"Open this URL to grant read-only Gmail access:\n{url}\n")
    webbrowser.open(url)


def listen(port: int, timeout: float) -> tuple[str, AwaitCode]:
    """Bind a one-shot listener on 127.0.0.1 (port 0 picks a free one), waiting at most `timeout`.

    The wait is bounded so an abandoned consent page ends the run: with no request in time the
    code and state are "", which consent refuses as a state mismatch.

    Returns:
        (the redirect URI, a function that waits for one request and returns its (code, state);
        either is "" when the redirect lacks it).

    """
    seen: dict[str, str] = {}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = parse_qs(urlsplit(self.path).query)
            seen["code"] = query.get("code", [""])[0]
            seen["state"] = query.get("state", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(_CLOSE_PAGE)

        @override
        def log_message(self, fmt: str, *args: object) -> None:
            # The default logs the request line, which carries the code. Nothing is logged.
            del fmt, args

    server = HTTPServer((_LOOPBACK, port), _Handler)
    server.timeout = timeout
    redirect = f"http://{_LOOPBACK}:{server.server_address[1]}"

    def await_code() -> tuple[str, str]:
        with server:
            server.handle_request()
        return seen.get("code", ""), seen.get("state", "")

    return redirect, await_code


def _connect(url: str) -> tuple[http.client.HTTPConnection, str]:
    """Open a connection for `url`: https anywhere, plain http only to 127.0.0.1.

    Returns:
        (the connection, the path and query to request).

    Raises:
        ConsentError: for any other scheme or host; nothing is sent.

    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    target = f"{parts.path or '/'}{'?' + parts.query if parts.query else ''}"
    if parts.scheme == "https":
        return http.client.HTTPSConnection(host, parts.port, timeout=_TIMEOUT_S), target
    if parts.scheme == "http" and host == _LOOPBACK:
        return http.client.HTTPConnection(host, parts.port, timeout=_TIMEOUT_S), target
    msg = f"refusing to connect to a {parts.scheme or 'schemeless'} URL"
    raise ConsentError(msg)


def post_form(url: str, form: dict[str, str]) -> tuple[int, bytes]:
    """POST a form and return (status, body), an error status's included.

    Returns:
        the response status and body.

    """
    conn, target = _connect(url)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        conn.request("POST", target, urlencode(form), headers)
        response = conn.getresponse()
        return response.status, response.read()
    finally:
        conn.close()


def get_bearer(url: str, access: str) -> tuple[int, bytes]:
    """GET with the access token as a Bearer header; return (status, body), errors included.

    Returns:
        the response status and body.

    """
    conn, target = _connect(url)
    try:
        conn.request("GET", target, headers={"Authorization": f"Bearer {access}"})
        response = conn.getresponse()
        return response.status, response.read()
    finally:
        conn.close()


def age_encrypt(recipient: str, out: Path, binary: str = "age") -> Encrypt:
    """Make the `encrypt` effect: the token goes to age on stdin, and out as ciphertext.

    Returns:
        a function taking the token.

    """

    def encrypt(token: str) -> None:
        proc = subprocess.run(
            [binary, "--encrypt", "--recipient", recipient, "--output", str(out)],
            input=token.encode(),
            capture_output=True,
            check=False,
            timeout=_TIMEOUT_S,
        )
        if proc.returncode != 0:
            msg = f"age could not encrypt to {out} (exit {proc.returncode})"
            raise ConsentError(msg)

    return encrypt


def age_runner(binary: str = "age") -> Runner:
    """Make auth.decrypt's runner: run the argv it builds with `binary` in place of `age`.

    ⚑ STDERR IS NOT CAPTURED, ONLY STDOUT (W382). age-plugin-yubikey asks for the PIN and says
    "touch your YubiKey" through age's stderr; captured, the operator saw neither, and the run
    failed as `age could not decrypt ... (exit 1)` naming no cause (measured 2026-10-02, first
    live decrypt). Inherited, the prompts and any error reach the terminal. stdout, which carries
    the token, is still captured and never printed.

    Returns:
        a runner returning (exit status, stdout, b""): stderr went to the terminal. Decryption
        waits for a YubiKey touch, so it is given longer than a network call.

    """

    def run(argv: list[str]) -> tuple[int, bytes, bytes]:
        proc = subprocess.run(
            [binary, *argv[1:]], stdout=subprocess.PIPE, check=False, timeout=_TOUCH_S
        )
        return proc.returncode, proc.stdout, b""

    return run


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mikemol-gmail")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("consent", help="one-time: store the refresh token age-encrypted")
    run.add_argument("--client", required=True, help="Google installed-client JSON")
    run.add_argument("--recipient", required=True, help="age recipient, e.g. age1yubikey1...")
    run.add_argument("--out", required=True, help="the .age file to create")
    run.add_argument("--port", type=int, default=0, help="loopback port (0: any free one)")
    run.add_argument("--timeout", type=float, default=300.0, help="seconds to wait for consent")
    run.add_argument("--age", default="age", help="the age binary")
    for name, what in (("search", "QUERY"), ("show", "ID"), ("raw", "ID")):
        read = sub.add_parser(name, help=f"{name} by {what}")
        read.add_argument("target", metavar=what)
        read.add_argument("--client", required=True, help="Google installed-client JSON")
        read.add_argument("--token", required=True, help="the .age refresh token from consent")
        read.add_argument("--identity", required=True, help="the YubiKey age identity stub")
        read.add_argument("--age", default="age", help="the age binary")
        if name == "search":
            read.add_argument("--max-pages", type=int, default=10, help="pages at most")
        if name == "raw":
            read.add_argument("--out", required=True, help="the .eml file to create (mode 600)")
    return parser


def _write_new(out: Path, data: bytes) -> None:
    """Create `out` owner-only and write `data`; an existing file is refused, never overwritten.

    O_EXCL makes the refusal and the creation one step, so nothing can appear in between.
    """
    descriptor = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


def _consent(opts: dict[str, object], browser: Browser, post: Poster) -> int:
    out = Path(str(opts["out"]))
    if out.exists():
        sys.stderr.write(f"mikemol-gmail: {out} exists; remove it first to re-consent\n")
        return 1
    port = opts["port"]
    wait = opts["timeout"]
    redirect, await_code = listen(port if isinstance(port, int) else 0, float(str(wait)))
    encrypt = age_encrypt(str(opts["recipient"]), out, str(opts["age"]))
    client = Path(str(opts["client"])).read_text(encoding="utf-8")
    consent(client, redirect, (os.urandom, browser, await_code, post, encrypt))
    sys.stderr.write(f"mikemol-gmail: wrote {out}\n")
    return 0


def _row(rec: Listed | Message | Unreadable) -> dict[str, object]:
    """Name every field that goes out, per record kind; nothing is serialized by reflection.

    Returns:
        the record as a JSON object, with its kind.

    """
    if isinstance(rec, Listed):
        return {
            "kind": "Listed",
            "id": rec.id,
            "thread_id": rec.thread_id,
            "page": rec.page,
            "ordinal": rec.ordinal,
        }
    if isinstance(rec, Message):
        return {
            "kind": "Message",
            "id": rec.id,
            "thread_id": rec.thread_id,
            "labels": list(rec.labels),
            "snippet": rec.snippet,
            "internal_date_ms": rec.internal_date_ms,
            "headers": [list(pair) for pair in rec.headers],
        }
    return {"kind": "Unreadable", "id": rec.id, "reason": rec.reason}


def _read(opts: dict[str, object], effects: tuple[Runner, Poster, Getter]) -> int:
    runner, post, get = effects
    refresh = decrypt(Path(str(opts["token"])), Path(str(opts["identity"])), runner)
    client_id, secret = read_client(Path(str(opts["client"])).read_text(encoding="utf-8"))
    access, _expires = exchange(refresh, client_id, secret, post)
    target = str(opts["target"])
    if opts["command"] == "raw":
        out = Path(str(opts["out"]))
        _write_new(out, raw(target, access, get))
        sys.stderr.write(f"mikemol-gmail: wrote {out}\n")
        return 0
    records: list[Listed | Message | Unreadable]
    if opts["command"] == "show":
        records = [show(target, access, get)]
    else:
        pages_at_most = opts["max_pages"]
        cap = pages_at_most if isinstance(pages_at_most, int) else 1
        records = list(search(target, access, get, cap))
    for rec in records:
        sys.stdout.write(json.dumps(_row(rec)) + "\n")
    return 0


def main(
    argv: list[str] | None = None,
    *,
    browser: Browser = open_browser,
    post: Poster = post_form,
    get: Getter = get_bearer,
    runner: Runner | None = None,
) -> int:
    """Run `mikemol-gmail consent`, `search` or `show`.

    Returns:
        0 on success, 1 on a refused or failed run. argparse exits 2 on a usage error.

    """
    opts: dict[str, object] = vars(_parser().parse_args(sys.argv[1:] if argv is None else argv))
    try:
        if opts["command"] == "consent":
            return _consent(opts, browser, post)
        return _read(opts, (runner or age_runner(str(opts["age"])), post, get))
    except (ConsentError, DecryptError, ExchangeError, FetchError, OSError) as err:
        sys.stderr.write(f"mikemol-gmail: {err}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
