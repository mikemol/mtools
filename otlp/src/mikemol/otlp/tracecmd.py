# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-otlp trace`: push one span to the trace store and read it back (W1438).

⚑⚑ THE DESTINATION IS A NAME, THE PATHS ARE LUTHEN'S. The base URL is the host's
`victoriatraces-http` (resolved through `MIKEMOL_ENDPOINTS`, or `--url` for a base the caller
holds), the span goes to `<base>/insert/opentelemetry/v1/traces` as protobuf, and `--readback`
fetches it from `<base>/select/jaeger/api/traces/<hex trace id>` (luthen-observability:W1189,
verified live by them at 2026-10-17T05:54Z). No address is held here.

⚑ ONE READ, NO POLLING: the store ingests asynchronously, so a span may not be visible at once. The
read is attempted ONCE; if the trace is not there yet the command says so, prints the URL to retry
and exits `EXIT_BUSY` (a precondition unmet, a later attempt may succeed), rather than looping on a
timer. A found trace is a witness only when its own id is in the answer. MEASURED 2026-10-17 against
the live store: the immediate read answered 404 and the same GET about a minute later returned the
span with its attributes, so BUSY on a first read is the normal answer, not a fault; luthen's own
probe polls up to 40 s for the same reason.

Both the network calls are seams (`Post`, `Get`), so the tests replace them.
"""

import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from mikemol.otlp import metrics, sender, spans

ENDPOINT = "victoriatraces-http"
JAEGER_PATH = "/select/jaeger/api/traces/"
EXIT_SENT = 0
EXIT_FAILED = 1
EXIT_BUSY = 3
_NS_PER_MS = 1_000_000
_OK = 200
Get = Callable[[str], tuple[int, str]]


@dataclass(frozen=True, slots=True)
class Request:
    """One `trace` invocation, parsed: where, as whom, what span and whether to read it back."""

    base: str
    service: str
    namespace: str
    version: str
    name: str
    status: str
    duration_ms: int
    labels: Mapping[str, str]
    readback: bool


def run(req: Request, post: sender.Post, get: Get) -> int:
    """Send one span and, when asked, read it back once.

    Returns:
        EXIT_SENT when sent (and found, with `readback`), EXIT_FAILED when a call failed,
        EXIT_BUSY when the span was sent but is not visible yet.

    """
    resource = metrics.resource_here(req.service, req.namespace, req.version)
    now = time.time_ns()
    trace_id, span_id = spans.new_ids()
    timing = spans.Timing(now - req.duration_ms * _NS_PER_MS, now)
    entry = spans.Entry(req.name, trace_id, span_id, timing, labels=req.labels, status=req.status)
    base = req.base.rstrip("/")
    payload = spans.request(resource, entry).SerializeToString()
    try:
        sender.send(base + sender.TRACES_PATH, payload, post)
    except sender.SendError as failed:
        sys.stderr.write(f"mikemol-otlp: {failed}\n")
        return EXIT_FAILED
    wanted = trace_id.hex()
    sys.stdout.write(f"sent span name={req.name} trace_id={wanted}\n")
    if not req.readback:
        return EXIT_SENT
    url = base + JAEGER_PATH + wanted
    try:
        status, body = get(url)
    except sender.SendError as failed:
        sys.stderr.write(f"mikemol-otlp: {failed}\n")
        return EXIT_FAILED
    if status == _OK and wanted in body:
        sys.stdout.write(f"read back trace_id={wanted} from {url}\n")
        return EXIT_SENT
    sys.stderr.write(f"mikemol-otlp: not visible yet (status {status}); retry GET {url}\n")
    return EXIT_BUSY
