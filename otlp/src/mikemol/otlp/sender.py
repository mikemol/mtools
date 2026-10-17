# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Send a serialised OTLP payload to a named endpoint, behind a seam (W1412).

⚑ THE ENDPOINT IS THE CALLER'S, THE PATHS ARE LUTHEN'S. Luthen's receiver (luthen-observability:
W1128, read 2026-10-17) answers metrics at `/opentelemetry/v1/metrics` on vmsingle and logs at
`/insert/opentelemetry/v1/logs` on victorialogs, as PROTOBUF only: its JSON body answers 400. The
host and port are luthen's declared endpoint names, so this module takes a full URL and names only
the two paths and the content type; it holds no address.

⚑ A NON-2xX IS A FAILURE THE CALLER SEES. `send` raises `SendError` naming the status, so a 400 for
a wrong encoding is not swallowed; the `post` seam is a plain function the tests replace, and the
real one is the only code here that touches the network.

⚑ THIS CALL CAN BLOCK, SO A HOOK DOES NOT MAKE IT INLINE. It sets no wall-clock timeout (the tree
bounds work by progress, not by a timer), which means an unresponsive endpoint holds the caller:
the spool-and-drain model of `mikemol-vlog` is how a hook emits, and the drainer calls this.
"""

from collections.abc import Callable
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from urllib.parse import urlsplit

CONTENT_TYPE = "application/x-protobuf"
METRICS_PATH = "/opentelemetry/v1/metrics"
LOGS_PATH = "/insert/opentelemetry/v1/logs"
_SCHEMES: dict[str, type[HTTPConnection]] = {"http": HTTPConnection, "https": HTTPSConnection}
_OK_LOW = 200
_OK_HIGH = 300

Post = Callable[[str, bytes], int]


class SendError(RuntimeError):
    """A payload was not delivered: a bad URL, an unreachable endpoint, or a non-2xx answer."""


def post(url: str, body: bytes) -> int:
    """POST `body` to `url` as protobuf and return the HTTP status.

    Returns:
        the status code, 4xx and 5xx included (a refusal is an answer, not an exception).

    Raises:
        SendError: when the URL is not http(s) or the endpoint cannot be reached.

    """
    parts = urlsplit(url)
    if parts.scheme not in _SCHEMES:
        msg = f"not an http(s) URL: {url!r}"
        raise SendError(msg)
    connection = _SCHEMES[parts.scheme](parts.netloc)
    target = parts.path + (f"?{parts.query}" if parts.query else "")
    try:
        connection.request("POST", target, body=body, headers={"Content-Type": CONTENT_TYPE})
        status = connection.getresponse().status
    except OSError as unreachable:
        msg = f"cannot reach {url}: {unreachable}"
        raise SendError(msg) from unreachable
    except HTTPException as broken:
        msg = f"{url} answered something that is not HTTP: {broken}"
        raise SendError(msg) from broken
    finally:
        connection.close()
    return status


def send(url: str, payload: bytes, poster: Post = post) -> int:
    """Deliver a serialised payload and insist on a 2xx answer.

    Returns:
        the status code of the accepted delivery.

    Raises:
        SendError: when the endpoint answers outside 200 to 299.

    """
    status = poster(url, payload)
    if not _OK_LOW <= status < _OK_HIGH:
        msg = f"{url} answered {status}; OTLP over HTTP wants protobuf and a 2xx"
        raise SendError(msg)
    return status
