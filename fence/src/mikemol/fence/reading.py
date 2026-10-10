# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The reading source of a run-time guard: one PromQL instant query against a NAMED endpoint (W919).

A guard (`guard.py`, W918) judges a series of samples; this produces one. The ask is a datastore
latency guard that samples a metrics store while a heavy gate runs (luthen-observability:W710).

⚑⚑ NO ADDRESS IS IN MTOOLS. A guard row names an endpoint (`vmsingle-http`); the host's own JSON
file (`MIKEMOL_ENDPOINTS`, `{"name": "http://host:port"}`) says where it is. The limits live in the
policy row and the address in the host's file, so neither a cluster's layout nor a port is published
here, and a different host answers the same name differently.

⚑⚑ EVERY FAILURE IS A BLIND SAMPLE (`None`), NEVER AN EXCEPTION AND NEVER A NUMBER. An unset or
unreadable endpoints file, an unknown name, a scheme that is not http(s), a refused connection, a
timeout, a body that is not JSON, a query that did not succeed, an empty result and a NaN are all
"could not read". The trip rule treats a blind sample as neither over nor under, so a guard that
cannot see does not kill a healthy build and does not pretend to have seen one.

⚑ ONLY http AND https ARE SPOKEN: a host-supplied file is still data, and `file://` or `ftp://`
through a general URL opener would read local files as a "reading". The request is made with
`http.client` directly, which can speak nothing else.

CONSUMED BY: the guard watcher (W920).
"""

from __future__ import annotations

import json
import math
import urllib.parse
from collections.abc import Callable
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

    from mikemol.fence.guard import Sample

ENV = "MIKEMOL_ENDPOINTS"
QUERY_PATH = "/api/v1/query"
TIMEOUT_S = 10.0
_SCHEMES = ("http", "https")
_PAIR = 2

Fetch = Callable[[str, float], object]
"""GET a URL within a timeout: the parsed JSON body, or None when anything went wrong."""


def endpoint_url(name: str, environ: Mapping[str, str]) -> str | None:
    """Resolve an endpoint name through the host's file.

    Returns:
        the base URL, or None when the file is unset or unreadable, holds no such name, or names
        a scheme other than http(s).

    """
    path = environ.get(ENV)
    if not path:
        return None
    try:
        doc: object = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict):
        return None
    url = cast("dict[object, object]", doc).get(name)
    if not isinstance(url, str):
        return None
    try:
        scheme = urllib.parse.urlsplit(url).scheme
    except ValueError:
        return None
    return url if scheme in _SCHEMES else None


def query_url(base: str, query: str) -> str:
    """Build the instant-query URL for a PromQL expression.

    Returns:
        `<base>/api/v1/query?query=<url-encoded expression>`.

    """
    return f"{base.rstrip('/')}{QUERY_PATH}?{urllib.parse.urlencode({'query': query})}"


def value_of(doc: object) -> float | None:
    """Read the first sample of a PromQL instant-query answer.

    Returns:
        the number, or None when the query did not succeed, returned no series, or the value is
        not a number (NaN is "no data" to Prometheus).

    """
    top = cast("dict[object, object]", doc) if isinstance(doc, dict) else {}
    data = top.get("data")
    if top.get("status") != "success" or not isinstance(data, dict):
        return None
    result = cast("dict[object, object]", data).get("result")
    if not isinstance(result, list) or not result:
        return None
    first = cast("list[object]", result)[0]
    value = cast("dict[object, object]", first).get("value") if isinstance(first, dict) else None
    if not isinstance(value, list) or len(cast("list[object]", value)) != _PAIR:
        return None
    try:
        number = float(str(cast("list[object]", value)[1]))
    except ValueError:
        return None
    return None if math.isnan(number) else number


def fetch(url: str, timeout: float) -> object:
    """GET a URL and parse its JSON body.

    Returns:
        the parsed body, or None on any transport or parse failure. A non-200 answer is parsed
        too: Prometheus answers a bad query with a 400 and a JSON error, which `value_of` reads as
        no value.

    """
    parts = urllib.parse.urlsplit(url)
    connection: HTTPConnection = (
        HTTPSConnection(parts.hostname or "", parts.port, timeout=timeout)
        if parts.scheme == "https"
        else HTTPConnection(parts.hostname or "", parts.port, timeout=timeout)
    )
    try:
        connection.request("GET", f"{parts.path}?{parts.query}")
        body = connection.getresponse().read().decode("utf-8")
        parsed: object = json.loads(body)
    except (OSError, ValueError, HTTPException):
        return None
    finally:
        connection.close()
    return parsed


def reader(
    name: str, query: str, environ: Mapping[str, str], fetcher: Fetch = fetch
) -> Callable[[], Sample]:
    """Build the zero-argument reading a watcher calls once per interval.

    ⚑ THE ENDPOINT IS RESOLVED ON EVERY READ, not once: the host's file may be written after the
    guard starts, and an unresolvable name is a blind sample like any other, not a crash.

    Returns:
        a function giving the current value, or None when it cannot be read.

    """

    def read() -> Sample:
        base = endpoint_url(name, environ)
        if base is None:
            return None
        return value_of(fetcher(query_url(base, query), TIMEOUT_S))

    return read
