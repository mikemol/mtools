# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`mikemol-otlp log`: stdin lines become OTLP log records sent to a URL (W1418).

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
from collections.abc import Mapping, Sequence
from typing import TextIO, cast

from mikemol.otlp import endpoints, logs, metrics, sender

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


def main(argv: Sequence[str] | None = None, stdin: TextIO | None = None) -> int:
    """Send stdin's lines as OTLP log records.

    Returns:
        0 when every line was sent, 1 when a send failed, 2 on a usage refusal.

    """
    opts: dict[str, object] = vars(_parser().parse_args(sys.argv[1:] if argv is None else argv))
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
