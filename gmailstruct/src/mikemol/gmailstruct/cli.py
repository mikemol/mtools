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
import os
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, override
from urllib.parse import parse_qs, urlencode, urlsplit

from mikemol.gmailstruct.consent import ConsentError, consent

if TYPE_CHECKING:
    from mikemol.gmailstruct.auth import Poster
    from mikemol.gmailstruct.consent import AwaitCode, Browser, Encrypt

_TIMEOUT_S = 30
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


def post_form(url: str, form: dict[str, str]) -> tuple[int, bytes]:
    """POST a form and return (status, body), an error status's included.

    Returns:
        the response status and body.

    Raises:
        ConsentError: for any scheme but https, or http to anywhere but 127.0.0.1.

    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    conn: http.client.HTTPConnection
    if parts.scheme == "https":
        conn = http.client.HTTPSConnection(host, parts.port, timeout=_TIMEOUT_S)
    elif parts.scheme == "http" and host == _LOOPBACK:
        conn = http.client.HTTPConnection(host, parts.port, timeout=_TIMEOUT_S)
    else:
        msg = f"refusing to POST to a {parts.scheme or 'schemeless'} URL"
        raise ConsentError(msg)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        conn.request("POST", parts.path or "/", urlencode(form), headers)
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
    return parser


def main(
    argv: list[str] | None = None,
    *,
    browser: Browser = open_browser,
    post: Poster = post_form,
) -> int:
    """Run `mikemol-gmail`. Only `consent` exists so far (W357 adds search and show).

    Returns:
        0 on success, 1 on a refused or failed run. argparse exits 2 on a usage error.

    """
    opts: dict[str, object] = vars(_parser().parse_args(sys.argv[1:] if argv is None else argv))
    out = Path(str(opts["out"]))
    if out.exists():
        sys.stderr.write(f"mikemol-gmail: {out} exists; remove it first to re-consent\n")
        return 1
    port = opts["port"]
    wait = opts["timeout"]
    redirect, await_code = listen(port if isinstance(port, int) else 0, float(str(wait)))
    encrypt = age_encrypt(str(opts["recipient"]), out, str(opts["age"]))
    try:
        client = Path(str(opts["client"])).read_text(encoding="utf-8")
        consent(client, redirect, (os.urandom, browser, await_code, post, encrypt))
    except (ConsentError, OSError) as err:
        sys.stderr.write(f"mikemol-gmail: {err}\n")
        return 1
    sys.stderr.write(f"mikemol-gmail: wrote {out}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
