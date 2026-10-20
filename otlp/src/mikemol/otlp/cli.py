# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`mikemol-otlp log|trace`: stdin lines become OTLP log records; `trace` sends one span (W1418).

`trace --service S --namespace N --name NAME [--url BASE] [--status OK|ERROR] [--readback]` pushes
one span to `victoriatraces-http` (by name through the endpoints file, or `--url` for a base) and,
with `--readback`, GETs it once from the Jaeger path; see `tracecmd` (W1438). The text below
describes `log`.

⚑⚑ FOR A USER-LEVEL PRODUCER THAT MUST NOT IMPORT THE WHEEL (the paths-forward writer, W1248). It
reads one record per non-empty stdin line, builds each with `logs.request` under the resource
`resource_here` names (so `host.name` is the machine's own), and sends it with `sender.send`. The
writer stays dependency-free by running this as a child that may be absent; this module is where
the protobuf wheel is imported, and it is imported only when a record is sent.

    mikemol-otlp log --url URL --service NAME --namespace REPO [--field KEY=VALUE]... \
        [--severity INFO|WARN|ERROR] [--version V] < lines

⚑ THE URL IS THE CALLER'S, resolved by name through luthen's `checks.endpoints_query`; no address is
held here, and `--url` may instead be the environment variable `MIKEMOL_OTLP_LOGS_URL`. A per-run
nonce is attached to every record as the attribute `otlp_log_nonce` and printed, so the caller (or
luthen) can read the records back with `checks.vlogs_query`; this CLI does not query the store.

Exit codes: 0 every line sent; 1 a send failed (the reason on stderr, records after it unsent); 2 a
usage refusal.
"""

import argparse
import os
import secrets
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from typing import TextIO, cast

from mikemol.otlp import (
    endpoints,
    logs,
    metriccmd,
    metrics,
    query_metrics,
    sender,
    staleness,
    tracecmd,
)

URL_ENV = "MIKEMOL_OTLP_LOGS_URL"
ENDPOINT = "victorialogs-http"
NONCE_FIELD = "otlp_log_nonce"
EXIT_SENT = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
_LEVELS = ("ERROR", "INFO", "WARN")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mikemol-otlp")
    verbs = parser.add_subparsers(dest="verb", required=True)
    log = verbs.add_parser("log", help="send each stdin line as an OTLP log record")
    log.add_argument("--url", help=f"the logs endpoint URL (default: ${URL_ENV})")
    log.add_argument("--service", required=True, help="service.name")
    log.add_argument("--namespace", required=True, help="service.namespace, the owning repo")
    log.add_argument("--version", default="", help="service.version, the commit it runs")
    log.add_argument("--severity", default="INFO", choices=_LEVELS)
    log.add_argument("--field", action="append", metavar="KEY=VALUE")
    trace = verbs.add_parser("trace", help="send one span and optionally read it back")
    trace.add_argument("--url", help=f"the traces base URL (default: ${endpoints.ENV} name)")
    trace.add_argument("--service", required=True, help="service.name")
    trace.add_argument("--namespace", required=True, help="service.namespace, the owning repo")
    trace.add_argument("--version", default="", help="service.version, the commit it runs")
    trace.add_argument("--name", required=True, help="the span's name")
    trace.add_argument("--status", default="UNSET", choices=("ERROR", "OK", "UNSET"))
    trace.add_argument("--duration-ms", dest="duration_ms", type=int, default=1)
    trace.add_argument("--field", action="append", metavar="KEY=VALUE")
    trace.add_argument("--readback", action="store_true", help="GET the trace once afterwards")
    trace.add_argument("--start-ns", dest="start_ns", type=int, default=0, help="start, epoch ns")
    trace.add_argument("--end-ns", dest="end_ns", type=int, default=0, help="end, epoch ns")
    trace.add_argument("--trace-id", dest="trace_id", default="", help="32 hex digits")
    trace.add_argument("--span-id", dest="span_id", default="", help="16 hex digits")
    trace.add_argument("--parent-id", dest="parent_id", default="", help="16 hex digits")
    metric = verbs.add_parser("metric", help="send one gauge or up-down sample")
    metric.add_argument("--url", help=f"the metrics base URL (default: ${endpoints.ENV} name)")
    metric.add_argument("--service", required=True, help="service.name")
    metric.add_argument("--namespace", required=True, help="service.namespace, the owning repo")
    metric.add_argument("--version", default="", help="service.version, the commit it runs")
    metric.add_argument("--name", required=True, help="the metric's name")
    metric.add_argument("--value", required=True, type=float, help="the sample's value")
    metric.add_argument("--kind", default="gauge", choices=metriccmd.KINDS)
    metric.add_argument("--field", action="append", metavar="KEY=VALUE")
    batch = verbs.add_parser("metrics", help="send stdin JSON lines as gauge samples, one request")
    batch.add_argument("--url", help=f"the metrics base URL (default: ${endpoints.ENV} name)")
    batch.add_argument("--service", required=True, help="service.name")
    batch.add_argument("--namespace", required=True, help="service.namespace, the owning repo")
    batch.add_argument("--version", default="", help="service.version, the commit it runs")
    query = verbs.add_parser("query-metrics", help="run a PromQL query, print JSON lines")
    query.add_argument("promql", help="the PromQL expression")
    query.add_argument("--url", help=f"the metrics base URL (default: ${endpoints.ENV} name)")
    query.add_argument("--start", help="a range query: its start (RFC 3339 or epoch)")
    query.add_argument("--end", help="a range query: its end")
    query.add_argument("--step", help="a range query: its step, such as 30s")
    return parser


def _text(opts: dict[str, object], key: str) -> str:
    # A string option, empty when unset.
    value = opts.get(key)
    return "" if value is None else str(value)


def _fields(opts: dict[str, object]) -> dict[str, str] | None:
    # The KEY=VALUE pairs as a mapping; None when one has no `=` or no key.
    given = opts.get("field")
    pairs: list[str] = cast("list[str]", given) if given else []
    out: dict[str, str] = {}
    for pair in pairs:
        key, found, value = pair.partition("=")
        if not found or not key:
            return None
        out[key] = value
    return out


def _destination(given: str, environ: Mapping[str, str]) -> str:
    """Pick the logs URL: `--url`, else the environment's full URL, else the named endpoint.

    ⚑ THE NAME IS RESOLVED LAST (luthen, 2026-10-17): an address in an environment is an address
    literal in their tree, so the host's endpoints file is the route they want, with the older
    full-URL variable still winning when set so nothing built before it breaks.

    Returns:
        the URL, or empty when none of the three yields one.

    """
    if given:
        return given
    full = environ.get(URL_ENV, "")
    if full:
        return full
    return endpoints.url_for(ENDPOINT, sender.LOGS_PATH, environ) or ""


def _trace(opts: dict[str, object], environ: Mapping[str, str]) -> int:
    # The `trace` verb: parse into a request and run it; a missing base or a bad field is usage.
    base = _text(opts, "url") or endpoints.base_url(tracecmd.ENDPOINT, environ) or ""
    fields = _fields(opts)
    if not base or fields is None:
        sys.stderr.write(
            f"mikemol-otlp: need --url or ${endpoints.ENV} naming {tracecmd.ENDPOINT}; "
            "and --field KEY=VALUE pairs\n"
        )
        return EXIT_USAGE
    request = tracecmd.Request(
        base=base,
        service=_text(opts, "service"),
        namespace=_text(opts, "namespace"),
        version=_text(opts, "version"),
        name=_text(opts, "name"),
        status=_text(opts, "status"),
        duration_ms=int(_text(opts, "duration_ms")),
        labels=fields,
        readback=bool(opts.get("readback")),
        start_ns=int(_text(opts, "start_ns")),
        end_ns=int(_text(opts, "end_ns")),
        trace_id=_text(opts, "trace_id"),
        span_id=_text(opts, "span_id"),
        parent_id=_text(opts, "parent_id"),
    )
    return tracecmd.run(request, sender.post, sender.get)


def _metric(opts: dict[str, object], environ: Mapping[str, str]) -> int:
    # The `metric` verb: parse into a request and run it; a missing base or a bad field is usage.
    base = _text(opts, "url") or endpoints.base_url(metriccmd.ENDPOINT, environ) or ""
    fields = _fields(opts)
    if not base or fields is None:
        sys.stderr.write(
            f"mikemol-otlp: need --url or ${endpoints.ENV} naming {metriccmd.ENDPOINT}; "
            "and --field KEY=VALUE pairs\n"
        )
        return EXIT_USAGE
    request = metriccmd.Request(
        base=base,
        service=_text(opts, "service"),
        namespace=_text(opts, "namespace"),
        version=_text(opts, "version"),
        name=_text(opts, "name"),
        value=float(_text(opts, "value")),
        kind=_text(opts, "kind"),
        labels=fields,
    )
    return metriccmd.run(request, sender.post)


def _metrics(opts: dict[str, object], environ: Mapping[str, str]) -> int:
    # The `metrics` verb: stdin JSON lines as gauge samples in one request (W1784).
    base = _text(opts, "url") or endpoints.base_url(metriccmd.ENDPOINT, environ) or ""
    if not base:
        sys.stderr.write(
            f"mikemol-otlp: need --url or ${endpoints.ENV} naming {metriccmd.ENDPOINT}\n"
        )
        return EXIT_USAGE
    request = metriccmd.BatchRequest(
        base=base,
        service=_text(opts, "service"),
        namespace=_text(opts, "namespace"),
        version=_text(opts, "version"),
        lines=cast("TextIO", sys.stdin).read().splitlines(),
    )
    return metriccmd.run_batch(request, sender.post)


def _query_metrics(opts: dict[str, object], environ: Mapping[str, str]) -> int:
    # The `query-metrics` verb: an instant query, or a range one when all three bounds are given.
    base = query_metrics.base_for(_text(opts, "url"), environ)
    given = (_text(opts, "start"), _text(opts, "end"), _text(opts, "step"))
    if base is None or any(given) != all(given):
        sys.stderr.write(
            f"mikemol-otlp: need --url or ${endpoints.ENV} naming {query_metrics.ENDPOINT}; "
            "and --start, --end and --step together or none\n"
        )
        return EXIT_USAGE if base is not None else query_metrics.EXIT_UNREACHABLE
    window = given if all(given) else None
    code, lines, said = query_metrics.run(base, _text(opts, "promql"), window)
    if said:
        sys.stderr.write(f"mikemol-otlp: {said}\n")
    sys.stdout.writelines(f"{line}\n" for line in lines)
    return code


_VERBS: dict[str, Callable[[dict[str, object], Mapping[str, str]], int]] = {
    "trace": _trace,
    "metric": _metric,
    "metrics": _metrics,
    "query-metrics": _query_metrics,
}


def main(argv: Sequence[str] | None = None, stdin: TextIO | None = None) -> int:
    """Send stdin's lines as OTLP log records, one span with `trace`, or one sample with `metric`.

    Returns:
        0 when everything was sent, 1 when a send failed, 2 on a usage refusal, 3 when a span was
        sent but not yet readable.

    """
    opts: dict[str, object] = vars(_parser().parse_args(sys.argv[1:] if argv is None else argv))
    warning = staleness.notice()
    if warning:
        sys.stderr.write(f"{warning}\n")
    handler = _VERBS.get(_text(opts, "verb"))
    if handler is not None:
        return handler(opts, os.environ)
    url = _destination(_text(opts, "url"), os.environ)
    fields = _fields(opts)
    if not url or fields is None:
        sys.stderr.write(
            f"mikemol-otlp: need --url, ${URL_ENV}, or ${endpoints.ENV} naming {ENDPOINT}; "
            "and --field KEY=VALUE pairs\n"
        )
        return EXIT_USAGE
    nonce = secrets.token_hex(8)
    service = _text(opts, "service")
    resource = metrics.resource_here(service, _text(opts, "namespace"), _text(opts, "version"))
    source = cast("TextIO", sys.stdin) if stdin is None else stdin
    labels = {**fields, NONCE_FIELD: nonce}
    sent = 0
    for line in source.read().splitlines():
        if not line.strip():
            continue
        entry = logs.Entry(line, time.time_ns(), _text(opts, "severity"), labels)
        try:
            sender.send(url, logs.request(resource, entry).SerializeToString())
        except sender.SendError as failed:
            sys.stderr.write(f"mikemol-otlp: {failed}; {sent} sent before it\n")
            return EXIT_FAILED
        sent += 1
    sys.stdout.write(f"sent {sent} record(s) service.name={service} nonce={nonce}\n")
    return EXIT_SENT


if __name__ == "__main__":
    raise SystemExit(main())
