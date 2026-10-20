# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-otlp query-metrics PROMQL`: read VictoriaMetrics with an instant or range query (W1727).

A session that can send a metric could not read one back, so a deploy witness (nemik:W702) went
through luthen by hand. This resolves the query endpoint the way the write side does, by the name
`vmsingle-http` in the host's endpoints file, runs `/api/v1/query` (or `/api/v1/query_range` with
`--start`, `--end` and `--step`) and prints each result series as one JSON line.

⚑ UNREACHABLE IS NEVER EMPTY: a store that did not answer, an endpoint name the host's file does not
hold and a reply that is not a Prometheus answer are exit 3 with the reason, because an empty
result a witness reads as "the metric is absent" would be a false negative about the deploy. A
store that ANSWERED with no series is an answer: exit 0 and no lines.

⚑ A QUERY THE STORE REJECTS IS NOT AN OUTAGE: a Prometheus error body (`"status": "error"`) is exit
4 naming the error type and message, so a typo in the PromQL reads differently from a dead store.

Exit codes: 0 answered (zero or more series printed); 2 usage; 3 store unreachable or unknown; 4
the store rejected the query.
"""

import json
from collections.abc import Callable, Mapping
from typing import cast
from urllib.parse import urlencode

from mikemol.otlp import endpoints, sender

ENDPOINT = "vmsingle-http"
INSTANT_PATH = "/api/v1/query"
RANGE_PATH = "/api/v1/query_range"
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_UNREACHABLE = 3
EXIT_REJECTED = 4
HTTP_OK = 200
Get = Callable[[str], tuple[int, str]]


def query_url(base: str, query: str, window: tuple[str, str, str] | None = None) -> str:
    """Build the instant or range query URL.

    Returns:
        the URL; a range query carries `window` as (start, end, step).

    """
    if window is None:
        return f"{base.rstrip('/')}{INSTANT_PATH}?{urlencode({'query': query})}"
    start, end, step = window
    args = urlencode({"query": query, "start": start, "end": end, "step": step})
    return f"{base.rstrip('/')}{RANGE_PATH}?{args}"


def _body(text: str) -> dict[str, object] | None:
    # The reply as a JSON object, or None when it is not one.
    try:
        parsed = cast("object", json.loads(text))
    except ValueError:
        return None
    return cast("dict[str, object]", parsed) if isinstance(parsed, dict) else None


def series_of(body: dict[str, object]) -> list[object] | None:
    """Pull the result series out of a Prometheus success body.

    Returns:
        the series, or None when the body is not a success with a result list.

    """
    data = body.get("data")
    if body.get("status") != "success" or not isinstance(data, dict):
        return None
    result = cast("dict[str, object]", data).get("result")
    return cast("list[object]", result) if isinstance(result, list) else None


def run(
    base: str, query: str, window: tuple[str, str, str] | None = None, get: Get = sender.get
) -> tuple[int, list[str], str]:
    """Run one query against the store at `base`.

    Returns:
        the exit code, the JSON lines to print (one per series) and the sentence for stderr (empty
        on success).

    """
    try:
        status, text = get(query_url(base, query, window))
    except sender.SendError as unreachable:
        return EXIT_UNREACHABLE, [], f"the store did not answer: {unreachable}"
    body = _body(text)
    if body is not None and body.get("status") == "error":
        what = f"{body.get('errorType', 'error')}: {body.get('error', '')}"
        return EXIT_REJECTED, [], f"the store rejected the query: {what}"
    found = series_of(body) if body is not None else None
    if status != HTTP_OK or found is None:
        return EXIT_UNREACHABLE, [], f"the store's reply was not a query answer (HTTP {status})"
    return EXIT_OK, [json.dumps(series, sort_keys=True) for series in found], ""


def base_for(url: str, environ: Mapping[str, str]) -> str | None:
    """Pick the store's base URL: the one given, else the host's file's `vmsingle-http`.

    Returns:
        the base URL, or None when neither names one.

    """
    return url or endpoints.base_url(ENDPOINT, environ)
