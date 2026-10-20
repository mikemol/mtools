# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-gate-trend [--recent N] [--limit M]`: each gate phase's median, spread, slope (W1718).

Reads the commit spans (service `mikemol-commit`) from the host's trace store through its Jaeger
API and prints one line per phase: `phase n median spread slope`, seconds, over the phase's last N
gates. The pure arithmetic is `gatetrend`; this is the read and the print.

⚑ NO ADDRESS IS IN MTOOLS: the trace store's base URL comes from the host's endpoints file
(`MIKEMOL_ENDPOINTS`, else `~/.config/mikemol/endpoints.json`, name `victoriatraces-http`), as every
other reader of it does. A host with no such entry is exit 3 saying so, never a guess, and a store
that answers nothing is exit 3 too.

⚑ A READ, NEVER A WRITE: it asks the store for spans and prints; the series a panel reads are
W1722's to publish.
"""

import http.client
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from mikemol.hooks.gatetrend import Sample, phase_of, stats_by_phase

ENV = "MIKEMOL_ENDPOINTS"
HOME_FILE = ".config/mikemol/endpoints.json"
NAME = "victoriatraces-http"
SERVICE = "mikemol-commit"
DEFAULT_RECENT = 10
DEFAULT_LIMIT = 200
TIMEOUT_S = 60
EXIT_USAGE = 2
EXIT_NO_STORE = 3
HTTP_OK = 200
US = 1_000_000
USAGE = "usage: mikemol-gate-trend [--recent N] [--limit M]\n"
Fetch = Callable[[str], object]


def traces_url(environ: Mapping[str, str]) -> str | None:
    """Resolve the trace store's base URL through the host's endpoints file.

    Returns:
        the base URL, or None when no file names it.

    """
    named = environ.get(ENV)
    home = environ.get("HOME")
    path = named or (str(Path(home) / HOME_FILE) if home else "")
    try:
        doc = cast("object", json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None
    url = cast("dict[str, object]", doc).get(NAME) if isinstance(doc, dict) else None
    return url if isinstance(url, str) else None


def _records(value: object) -> list[dict[str, object]]:
    # The dict entries of a JSON list, or none when the value is not a list.
    if not isinstance(value, list):
        return []
    items = cast("list[object]", value)
    return [cast("dict[str, object]", v) for v in items if isinstance(v, dict)]


def samples_of(doc: object) -> list[Sample]:
    """Read the gate-phase samples out of a Jaeger traces document.

    Returns:
        one sample per span named after a gating phase; every other span is left out.

    """
    body = cast("dict[str, object]", doc) if isinstance(doc, dict) else {}
    out: list[Sample] = []
    for trace in _records(body.get("data")):
        for span in _records(trace.get("spans")):
            phase = phase_of(str(span.get("operationName", "")))
            start, took = span.get("startTime"), span.get("duration")
            if phase is not None and isinstance(start, int) and isinstance(took, int):
                out.append(Sample(phase, start, took / US))
    return out


def fetch_json(url: str) -> object:
    """Read one JSON document from the trace store.

    Returns:
        the parsed body.

    Raises:
        OSError: the store did not answer 200.

    """
    parts = urlsplit(url)
    conn = http.client.HTTPConnection(parts.hostname or "", parts.port, timeout=TIMEOUT_S)
    try:
        conn.request("GET", f"{parts.path}?{parts.query}")
        reply = conn.getresponse()
        data = reply.read()
        if reply.status != HTTP_OK:
            msg = f"HTTP {reply.status}"
            raise OSError(msg)
    finally:
        conn.close()
    return cast("object", json.loads(data))


def _options(args: Sequence[str]) -> dict[str, int] | None:
    # The two numeric options with their defaults, or None for an option it does not know.
    found = {"--recent": DEFAULT_RECENT, "--limit": DEFAULT_LIMIT}
    pending = list(args)
    while pending:
        flag = pending.pop(0)
        if flag not in found or not pending or not pending[0].isdigit():
            return None
        found[flag] = int(pending.pop(0))
    return found


def main(
    argv: Sequence[str] | None = None,
    fetch: Fetch = fetch_json,
    environ: Mapping[str, str] | None = None,
) -> int:
    """Print each gate phase's recent median, spread and slope.

    Returns:
        0; EXIT_USAGE for an option it does not know; EXIT_NO_STORE with no trace store to read.

    """
    options = _options(sys.argv[1:] if argv is None else argv)
    if options is None:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    base = traces_url(dict(os.environ) if environ is None else environ)
    if base is None:
        sys.stderr.write(f"mikemol-gate-trend: no {NAME} in the host's endpoints file\n")
        return EXIT_NO_STORE
    query = f"service={SERVICE}&limit={options['--limit']}&lookback=7d"
    try:
        doc = fetch(f"{base}/select/jaeger/api/traces?{query}")
    except (OSError, ValueError) as err:
        sys.stderr.write(f"mikemol-gate-trend: the trace store did not answer: {err}\n")
        return EXIT_NO_STORE
    for phase, stats in stats_by_phase(samples_of(doc), options["--recent"]).items():
        sys.stdout.write(
            f"{phase} n={stats.n} median={stats.median:.1f}s "
            f"spread={stats.spread:.1f}s slope={stats.slope:+.2f}s/gate\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
