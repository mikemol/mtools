# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-otlp metric`: push one gauge or up-down sample to the metrics store (W1445).

⚑⚑ THE DESTINATION IS A NAME, THE PATH IS LUTHEN'S. The base URL is the host's `vmsingle-http`
(resolved through `MIKEMOL_ENDPOINTS`, or `--url` for a base the caller holds) and the sample goes
to `<base>/opentelemetry/v1/metrics` as protobuf (luthen-observability:W1128). No address is held.

⚑ A GAUGE IS THE DEFAULT, BECAUSE THE CALLER KNOWS A VALUE, NOT A TOTAL. An up-down counter is a
CUMULATIVE sum (see `metrics`): a process that only knows "one more" cannot say what the total now
is, and sending a delta as if it were the total reads as a reset. `--kind updown` exists for a
caller that does hold the running total; the in-flight commit depth (W1446) sends absolute gauges.

The network call is a seam (`Post`), so the tests replace it.
"""

import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass

from mikemol.otlp import metrics, sender

ENDPOINT = "vmsingle-http"
KINDS = ("gauge", "updown")
EXIT_SENT = 0
EXIT_FAILED = 1


@dataclass(frozen=True, slots=True)
class Request:
    """One `metric` invocation, parsed: where, as whom, which sample and of what kind."""

    base: str
    service: str
    namespace: str
    version: str
    name: str
    value: float
    kind: str
    labels: Mapping[str, str]


def run(req: Request, post: sender.Post) -> int:
    """Send one metric sample.

    Returns:
        EXIT_SENT when the store accepted it, EXIT_FAILED when the send failed.

    """
    resource = metrics.resource_here(req.service, req.namespace, req.version)
    value = int(req.value) if req.value == int(req.value) else req.value
    sample = metrics.Sample(req.name, value, time.time_ns(), req.labels)
    build = metrics.updown_counter if req.kind == "updown" else metrics.gauge
    payload = build(resource, sample).SerializeToString()
    try:
        sender.send(req.base.rstrip("/") + sender.METRICS_PATH, payload, post)
    except sender.SendError as failed:
        sys.stderr.write(f"mikemol-otlp: {failed}\n")
        return EXIT_FAILED
    sys.stdout.write(f"sent {req.kind} {req.name}={value}\n")
    return EXIT_SENT
