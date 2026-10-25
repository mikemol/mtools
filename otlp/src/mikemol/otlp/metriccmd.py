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

import json
import sys
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import cast

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
    url: str = ""


@dataclass(frozen=True, slots=True)
class BatchRequest:
    """One `metrics` invocation: where, as whom, and the JSON lines on stdin."""

    base: str
    service: str
    namespace: str
    version: str
    lines: Iterable[str]
    url: str = ""


# ⚑ W1961: a row may describe its metric; each of these is a string or the row is not a sample.
_DESCRIBES = ("description", "unit", "freshness_class", "freshness_companion", "owner")


def _freshness_refusal(klass: str, companion: str) -> bool:
    """Say whether a freshness declaration is unusable to the registry.

    Returns:
        True for a class outside the two, an event_driven metric with no companion, or a
        companion on anything else; False for no declaration or a sound one.

    """
    if not klass:
        return bool(companion)
    if klass not in metrics.CLASSES:
        return True
    return (klass == "event_driven") != bool(companion)


def _described_by(row: dict[str, object]) -> dict[str, str] | None:
    """Read the description fields of a row.

    Returns:
        the fields as strings (empty where absent); None when one is not a string or the
        freshness declaration is unusable to the registry.

    """
    given = {key: row.get(key, "") for key in _DESCRIBES}
    if not all(isinstance(val, str) for val in given.values()):
        return None
    strings = {key: str(val) for key, val in given.items()}
    if _freshness_refusal(strings["freshness_class"], strings["freshness_companion"]):
        return None
    return strings


def _sample_of(line: str, now_ns: int) -> metrics.Sample | None:
    """Read one line as a gauge sample.

    Returns:
        the sample, or None when the line is not an object with a string name and a numeric value.

    """
    try:
        raw: object = json.loads(line)
    except ValueError:
        return None
    if not isinstance(raw, dict):
        return None
    row = cast("dict[str, object]", raw)
    name, value = row.get("name"), row.get("value")
    fields, when = row.get("fields", {}), row.get("time_ns", now_ns)
    numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
    if not isinstance(name, str) or not numeric or not isinstance(fields, dict):
        return None
    if not isinstance(when, int) or not isinstance(value, (int, float)):
        return None
    labels = {str(k): str(v) for k, v in cast("dict[object, object]", fields).items()}
    given = _described_by(row)
    if given is None:
        return None
    return metrics.Sample(
        name,
        float(value),
        when,
        labels,
        unit=str(given["unit"]),
        description=str(given["description"]),
        freshness_class=str(given["freshness_class"]),
        freshness_companion=str(given["freshness_companion"]),
        owner=str(given["owner"]),
    )


def parse_batch(lines: Iterable[str], now_ns: int) -> tuple[list[metrics.Sample], str]:
    """Read one gauge sample per non-empty line: `{"name", "value", "fields", "time_ns"}`.

    ⚑ ALL OR NOTHING: a line that is not an object with a name and a numeric value refuses the
    whole batch and says which line, so a half-sent batch never reads as a whole one. `time_ns` is
    when the number was true; absent, it is `now_ns`.

    Returns:
        the samples and an empty string, or no samples and the reason.

    """
    samples: list[metrics.Sample] = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        sample = _sample_of(line, now_ns)
        if sample is None:
            return [], f"line {number} is not a gauge sample"
        samples.append(sample)
    return samples, ""


def target(base: str, url: str) -> str:
    """Pick where a metrics request is posted.

    Returns:
        a complete URL as given (the OpenTelemetry standard variables, W1960), else the
        base joined to the store's metrics path.

    """
    return url or base.rstrip("/") + sender.METRICS_PATH


def run_batch(req: BatchRequest, post: sender.Post) -> int:
    """Send every sample of a batch in one request.

    Returns:
        EXIT_SENT when the store accepted it, EXIT_FAILED when a line was refused or the send
        failed.

    """
    samples, why = parse_batch(req.lines, time.time_ns())
    if why:
        sys.stderr.write(f"mikemol-otlp: {why}\n")
        return EXIT_FAILED
    if not samples:
        sys.stdout.write("sent 0 gauge samples\n")
        return EXIT_SENT
    resource = metrics.resource_here(req.service, req.namespace, req.version)
    payload = metrics.gauges(resource, samples).SerializeToString()
    try:
        sender.send(target(req.base, req.url), payload, post)
    except sender.SendError as failed:
        sys.stderr.write(f"mikemol-otlp: {failed}\n")
        return EXIT_FAILED
    sys.stdout.write(f"sent {len(samples)} gauge samples\n")
    return EXIT_SENT


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
        sender.send(target(req.base, req.url), payload, post)
    except sender.SendError as failed:
        sys.stderr.write(f"mikemol-otlp: {failed}\n")
        return EXIT_FAILED
    sys.stdout.write(f"sent {req.kind} {req.name}={value}\n")
    return EXIT_SENT
