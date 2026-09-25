# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Record a REFUSED tool invocation as one structured VictoriaLogs event.

Substrate's `ratchet_log`, moved (N-a row 5,
`inbox/2026-09-24-substrate-ratchet-log-flags-letter.md`). Renamed because it never ratcheted: it
answers *what are people and agents trying to invoke that these tools do not offer*, and lived in
the gate core only because that is where it was first needed.

⚑⚑ THE DESTINATION IS THE CALLER'S, WITH NO DEFAULT. Substrate's copy carried a written-down
address — `http://127.0.0.1:9428/…`, then `:30928` — and when the first one went stale, every
fault event evaporated with no symptom, because the emitter swallows every failure by design. A
package cannot know where its caller's log store lives, so the caller resolves it by NAME (e.g.
luthen's `endpoints_query victorialogs-http`) and passes it. `None` means it resolved to nothing.

⚑⚑ THE OUTCOME IS REPORTED, NOT SWALLOWED — and still never raised. `log_fallthrough` returns an
`Emission` saying whether the event left and, if not, why: no destination, no `curl`, or `curl`'s
own failure. A caller may print it, count it, or ignore it; what it can no longer do is mistake a
dead store for a quiet one. ⚑ Callers compute their verdict FIRST and emit after, so a logging
failure still cannot turn a refusal into a pass.

⚑ NO MODULE STATE, SO NO `redirected()`. Substrate's override slot existed to let a test point the
emitter somewhere dead; a destination passed per call makes that a plain argument.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from shutil import which
from typing import NamedTuple

# The 2s cap bounds the damage a hung endpoint can do to a commit; the outer timeout is one
# second longer so `curl`'s own deadline fires first and reports rather than being killed.
_CURL_MAX_TIME_S = "2"
_RUN_TIMEOUT_S = 3

UNKNOWN_TOOL = "unknown"
NO_DESTINATION = "no destination: the caller resolved none, and there is no default"
NO_CURL = "no curl on PATH"


def stream_tool(label: object) -> str:
    """Reduce a caller's LABEL to a BOUNDED tool identity fit for a stream field.

    ⚑⚑ `tool` IS A `_stream_fields` MEMBER, SO ITS CARDINALITY IS THE STREAM COUNT. A caller's
    label describes the INVOCATION (`bibstruct --add KEY`), which is unbounded in its operands;
    this keeps its first word's basename. The full label rides as the per-line `label` field.

    ⚑ `str(None)` IS THE TRUTHY STRING "None": the value is tested BEFORE it is stringified, or
    `None` mints a stream literally named `None` (caught by substrate's suite on its first run).

    Returns:
        the bounded identity, or "unknown".

    """
    text = str(label).strip() if label is not None else ""
    if not text:
        return UNKNOWN_TOOL
    return text.split()[0].rsplit("/", 1)[-1] or UNKNOWN_TOOL


class Refusal(NamedTuple):
    """The payload of one refused invocation, beyond its identity.

    ⚑ A RECORD, BECAUSE `known` AND `argv` ARE BOTH SEQUENCES OF STRINGS: as positional
    parameters a caller could transpose them and ingest a well-formed event whose two most
    diagnostic fields read backwards. ⚑ The fields are `object` because junk must not raise;
    `_join` does the narrowing at the one place that touches them.
    """

    known: object = ()
    argv: object = ()
    exit_code: int = 2


class Emission(NamedTuple):
    """Whether one event left for its store, and why not when it did not."""

    emitted: bool
    why: str = ""


def _join(value: object, *, sort: bool = False) -> str:
    """Render an untrusted sequence-ish value as a space-joined string; junk renders as "".

    Returns:
        the joined text.

    """
    if not isinstance(value, (list, tuple, set, frozenset)):
        return ""
    parts = [str(v) for v in value]
    return " ".join(sorted(parts) if sort else parts)


def event_line(tool: object, reason: object, typed: str, refusal: Refusal) -> str:
    """Return the event as one jsonline.

    ⚑ RFC3339 MICROSECONDS, NEVER AN INTEGER: VictoriaLogs answers HTTP 200 to an integer
    timestamp while ingesting ZERO rows (measured by cassian).

    Returns:
        the JSON text.

    """
    event: dict[str, object] = {
        "_time": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "_msg": f"{reason} {typed} on {tool}".replace("  ", " ").strip(),
        "tool": stream_tool(tool),
        "label": str(tool),
        "reason": str(reason),
        "typed": typed,
        "known": _join(refusal.known, sort=True),
        "argv": _join(refusal.argv) or " ".join(sys.argv),
        "exit": refusal.exit_code,
    }
    return json.dumps(event)


def log_fallthrough(
    tool: object,
    reason: object,
    typed: str = "",
    refusal: Refusal | None = None,
    *,
    destination: str | None,
) -> Emission:
    """Send one refused invocation to `destination`. Best-effort; never raises.

    ⚑⚑ `destination` IS REQUIRED AND HAS NO DEFAULT (the module docstring). `None` reports
    NOT emitted and starts nothing: there is no address to fall back to.

    ⚑ NO SPOOL: a replayed refusal is a fabricated attempt at the wrong time; a dropped one is an
    unmeasured attempt, which is honest.

    Returns:
        whether the event left, and why not when it did not.

    """
    if destination is None:
        return Emission(emitted=False, why=NO_DESTINATION)
    try:
        line = event_line(tool, reason, typed, refusal if refusal is not None else Refusal())
        curl = which("curl")
        if curl is None:
            return Emission(emitted=False, why=NO_CURL)
        done = subprocess.run(
            [
                curl,
                "-fsS",
                "--max-time",
                _CURL_MAX_TIME_S,
                "--data-binary",
                "@-",
                "-H",
                "Content-Type: application/stream+json",
                destination,
            ],
            input=line,
            text=True,
            capture_output=True,
            timeout=_RUN_TIMEOUT_S,
            check=False,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        return Emission(emitted=False, why=f"{type(exc).__name__}: {exc}")
    if done.returncode != 0:
        return Emission(emitted=False, why=f"curl exit {done.returncode}: {done.stderr.strip()}")
    return Emission(emitted=True)
