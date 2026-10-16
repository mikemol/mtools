# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Post spooled records to a VictoriaLogs JSON-lines ingest; the endpoint is found by NAME (W1167).

⚑ NO ADDRESS IS WRITTEN HERE, OR IN ANY CARD. Substrate's emitter carried one, it went stale, and
every event evaporated with no symptom (hooks/refusal_log.py, same lesson). The base URL comes from
a RESOLVER COMMAND the host configures, asked for a service NAME (for example luthen's
`endpoints_query`); there is no default. A name that resolves to nothing is a refusal the caller
can read, and the lines stay in the spool.

⚑ NO WALL-CLOCK TIMEOUT (operator, standing). The post waits for the endpoint as long as the
endpoint takes; what protects the caller is that this runs in a detached drainer behind the spool
(`vlogspool`), never in the caller's own process. A stalled endpoint backs up into the spool.

⚑ A REFUSAL IS A FACT, NOT AN EXCEPTION: `post` returns a `Posted` saying whether the endpoint took
the batch, the status, and the reason, for connection failures too (status 0). Only a 2xx is taken.
VictoriaLogs answers 2xx and ingests nothing for a record with an integer time, which no response
can reveal; `vlogrecord` is what keeps the time a string.

The ingest query names the fields the endpoint needs: `_msg_field`, `_time_field` and the stream
fields the caller declared, so the streams are the caller's choice and not a guess here.

CONSUMED BY: the `mikemol-vlog` command (W1169).
"""

import http.client
import subprocess
import urllib.parse
from collections.abc import Callable, Sequence
from dataclasses import dataclass

INGEST_PATH = "/insert/jsonline"
CONTENT_TYPE = "application/stream+json"
Opener = Callable[[str, bytes, dict[str, str]], tuple[int, str]]
"""Send a body to a URL with headers: the HTTP status (0 when none) and a short reason."""
Resolver = Callable[[Sequence[str]], tuple[int, str]]
"""Run a resolver command: its exit status and its standard output."""


@dataclass(frozen=True)
class Posted:
    """What posting a batch did: whether the endpoint took it, its status, and why not."""

    ok: bool
    status: int
    reason: str = ""


def ingest_url(base: str, stream_fields: Sequence[str]) -> str:
    """Build the JSON-lines ingest URL for `base` with the fields the endpoint must be told.

    Returns:
        `<base>/insert/jsonline?...` naming `_msg_field`, `_time_field` and `_stream_fields`.

    """
    query = {
        "_msg_field": "_msg",
        "_time_field": "_time",
        "_stream_fields": ",".join(stream_fields),
    }
    return f"{base.rstrip('/')}{INGEST_PATH}?{urllib.parse.urlencode(query, safe=',')}"


def _exchange(
    conn: http.client.HTTPConnection, target: str, data: bytes, headers: dict[str, str]
) -> tuple[int, str]:
    """Send one POST on `conn` and read the whole answer.

    Returns:
        the status and reason; (0, why) when the connection failed.

    """
    try:
        conn.request("POST", target, body=data, headers=headers)
        answer = conn.getresponse()
        answer.read()
    except Exception as exc:
        if not isinstance(exc, (http.client.HTTPException, OSError)):
            raise
        return 0, f"{type(exc).__name__}: {exc}"
    finally:
        conn.close()
    return answer.status, answer.reason


def http_opener(url: str, data: bytes, headers: dict[str, str]) -> tuple[int, str]:
    """POST `data` to `url` with no timeout, over http or https only.

    Returns:
        the status and a short reason; (0, why) when no HTTP answer came (refused, unreachable, a
        scheme that is not http or https).

    """
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname
    if host is None or parts.scheme not in {"http", "https"}:
        return 0, "scheme is not http or https, or the URL has no host"
    target = f"{parts.path or '/'}{'?' + parts.query if parts.query else ''}"
    if parts.scheme == "https":
        return _exchange(http.client.HTTPSConnection(host, parts.port), target, data, headers)
    return _exchange(http.client.HTTPConnection(host, parts.port), target, data, headers)


def post(url: str, lines: Sequence[str], opener: Opener = http_opener) -> Posted:
    """Send one batch of JSON lines.

    Returns:
        whether the endpoint took it (a 2xx), with the status and the reason when it did not.

    """
    body = "".join(f"{line}\n" for line in lines).encode("utf-8")
    status, reason = opener(url, body, {"Content-Type": CONTENT_TYPE})
    taken = status in range(200, 300)
    return Posted(taken, status, "" if taken else reason or f"HTTP {status}")


def run_resolver(argv: Sequence[str]) -> tuple[int, str]:
    """Run a resolver command with no timeout (it is the host's own tool).

    Returns:
        its exit status and standard output; (127, why) when it cannot start.

    """
    try:
        done = subprocess.run(list(argv), capture_output=True, text=True, check=False)
    except OSError as exc:
        return 127, f"{type(exc).__name__}: {exc}"
    return done.returncode, done.stdout


def resolve(name: str, template: Sequence[str], run: Resolver = run_resolver) -> str | None:
    """Ask the host's resolver for the base URL of the service called `name`.

    ⚑ `{name}` IN THE TEMPLATE IS REPLACED, AND THE TEMPLATE IS ARGV, NOT A SHELL STRING, so a name
    cannot inject a command. No template, a failing resolver or an empty answer is None.

    Returns:
        the first non-empty line the resolver printed, or None.

    """
    if not template:
        return None
    status, out = run([part.replace("{name}", name) for part in template])
    first = next((line.strip() for line in out.splitlines() if line.strip()), "")
    return first if status == 0 and first else None
