# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-otlp query-traces`: search the trace store for spans by service, name and time (W1799).

`trace --readback` fetches ONE span by its id, so a session that wanted the history of a span it
did not just send (every train round's `failed` field, W1719) had no way to ask. This resolves the
store the way `trace` does, by the name `victoriatraces-http` in the host's endpoints file, runs the
Jaeger search `<base>/select/jaeger/api/traces?service=S&operation=N&start=..&end=..&limit=..` (the
same API `--readback` reads by id) and prints each span found as one JSON line: its trace and span
id, name, start and duration in microseconds, and its attributes as a flat object.

⚑ UNREACHABLE IS NEVER EMPTY, as `query-metrics`: a store that did not answer, an endpoint the
host's file does not hold and a reply that is not a Jaeger answer are exit 3 with the reason,
because an empty result a reader takes as "that step never failed" would be a false negative. A
store that ANSWERED with no trace is an answer: exit 0 and no lines.

⚑ A SEARCH THE STORE REJECTS IS NOT AN OUTAGE: a Jaeger error body (`"errors": [...]`) is exit 4
naming the first error, so a malformed parameter reads differently from a dead store.

The network call is a seam (`Get`), so the tests replace it.
"""

import json
from collections.abc import Callable, Mapping
from typing import cast
from urllib.parse import urlencode

from mikemol.otlp import endpoints, query_metrics, sender

ENDPOINT = "victoriatraces-http"
SEARCH_PATH = "/select/jaeger/api/traces"
EXIT_OK = query_metrics.EXIT_OK
EXIT_UNREACHABLE = query_metrics.EXIT_UNREACHABLE
EXIT_REJECTED = query_metrics.EXIT_REJECTED
HTTP_OK = 200
Get = Callable[[str], tuple[int, str]]


def search_url(base: str, service: str, name: str, window: tuple[int, int], limit: int) -> str:
    """Build the search URL; `window` is (start, end) in epoch microseconds.

    Returns:
        the URL; an empty `name` leaves the operation out so every span of the service matches.

    """
    args = {"service": service, "start": window[0], "end": window[1], "limit": limit}
    if name:
        args["operation"] = name
    return f"{base.rstrip('/')}{SEARCH_PATH}?{urlencode(args)}"


def _body(text: str) -> dict[str, object] | None:
    # The reply as a JSON object, or None when it is not one.
    try:
        parsed = cast("object", json.loads(text))
    except ValueError:
        return None
    return cast("dict[str, object]", parsed) if isinstance(parsed, dict) else None


def _tags(span: Mapping[str, object]) -> dict[str, str]:
    # A span's Jaeger tags as a flat key to string mapping; malformed entries are skipped.
    raw = span.get("tags")
    entries = cast("list[object]", raw) if isinstance(raw, list) else []
    out: dict[str, str] = {}
    for entry in entries:
        if isinstance(entry, dict):
            tag = cast("dict[str, object]", entry)
            out[str(tag.get("key", ""))] = str(tag.get("value", ""))
    return out


def spans_of(body: dict[str, object]) -> list[dict[str, object]] | None:
    """Flatten a Jaeger search answer into one record per span.

    Returns:
        the records, or None when the body is not a search answer (no `data` list).

    """
    data = body.get("data")
    if not isinstance(data, list):
        return None
    out: list[dict[str, object]] = []
    for trace in cast("list[object]", data):
        spans = cast("dict[str, object]", trace).get("spans") if isinstance(trace, dict) else None
        for span in cast("list[object]", spans) if isinstance(spans, list) else []:
            if not isinstance(span, dict):
                continue
            found = cast("dict[str, object]", span)
            out.append(
                {
                    "trace_id": found.get("traceID", ""),
                    "span_id": found.get("spanID", ""),
                    "name": found.get("operationName", ""),
                    "start_us": found.get("startTime", 0),
                    "duration_us": found.get("duration", 0),
                    "fields": _tags(found),
                }
            )
    return out


def _error_of(body: dict[str, object]) -> str:
    # The first error a Jaeger body names, empty when it names none.
    errors = body.get("errors")
    if not isinstance(errors, list) or not errors:
        return ""
    first = cast("list[object]", errors)[0]
    if isinstance(first, dict):
        return str(cast("dict[str, object]", first).get("msg", first))
    return str(first)


def run(
    base: str,
    query: tuple[str, str, int],
    window: tuple[int, int],
    get: Get = sender.get,
) -> tuple[int, list[str], str]:
    """Run one search against the store at `base`.

    `query` is (service, span name, limit). The name may be empty.

    Returns:
        the exit code, the JSON lines to print (one per span) and the sentence for stderr (empty on
        success).

    """
    service, name, limit = query
    try:
        status, text = get(search_url(base, service, name, window, limit))
    except sender.SendError as unreachable:
        return EXIT_UNREACHABLE, [], f"the store did not answer: {unreachable}"
    body = _body(text)
    refusal = _error_of(body) if body is not None else ""
    if refusal:
        return EXIT_REJECTED, [], f"the store rejected the search: {refusal}"
    found = spans_of(body) if body is not None else None
    if status != HTTP_OK or found is None:
        return EXIT_UNREACHABLE, [], f"the store's reply was not a search answer (HTTP {status})"
    return EXIT_OK, [json.dumps(span, sort_keys=True) for span in found], ""


def base_for(url: str, environ: Mapping[str, str]) -> str | None:
    """Pick the store's base URL: the one given, else the host's file's `victoriatraces-http`.

    Returns:
        the base URL, or None when neither names one.

    """
    return url or endpoints.base_url(ENDPOINT, environ)
