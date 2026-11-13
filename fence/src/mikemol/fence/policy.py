# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The guard policy: declared rows, so a limit is a line in a file and not a literal in code (W921).

    [[guard]]
    name = "kine-latency"
    reading = "promql"
    endpoint = "vmsingle-http"        # a NAME; the address is the host's file (MIKEMOL_ENDPOINTS)
    query = 'histogram_quantile(0.99, sum by (le) (rate(kine_sql_time_seconds_bucket[5m])))'
    above = 4.0                       # seconds
    samples = 6                       # consecutive over-limit samples that trip
    interval_s = 30
    signal = "SIGINT"
    target = "bazel"                  # the descendant process, by name, to interrupt

⚑⚑ EVERY KEY IS REQUIRED AND NAMED WHEN ABSENT, AND A KEY NOBODY KNOWS IS A PROBLEM TOO. A default
limit would be a literal again, and a typo (`sample = 6`) that silently fell back to one would guard
less than its author believed. All problems in a file are reported together, not the first.

⚑ AN ABSENT POLICY IS NO GUARD, NOT AN ERROR: most hosts have none. A policy that exists and is
wrong raises `PolicyError` naming each problem; whoever runs the command decides what a broken
policy means for it (`guard_cli` reports it loudly and runs the command unguarded).

CONSUMED BY: `guard_cli` (the `mikemol-commit` wiring), W921.
"""

import signal
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mikemol.fence.watcher import Row

READINGS = ("promql",)
ACTIONS = ("signal", "freeze")
CAP_ACTIONS = ("resume", "kill")
_KEYS = (
    "name",
    "reading",
    "endpoint",
    "query",
    "above",
    "samples",
    "interval_s",
    "signal",
    "target",
)
# W2356: an absent `action` is the one-shot signal every host file written before it declares, so
# the key stays optional; a `freeze` row must then say every key of its own, with no default.
_FREEZE_KEYS = ("resume_samples", "max_frozen_samples", "on_cap")
_KNOWN = frozenset((*_KEYS, "action", *_FREEZE_KEYS))


class PolicyError(ValueError):
    """A policy file that exists and is wrong; `problems` names each fault."""

    def __init__(self, problems: list[str]) -> None:
        """Hold every problem and make the message from them."""
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Spec:
    """One guard row with the reading it takes."""

    row: Row
    endpoint: str
    query: str


def _number(value: object) -> bool:
    """Say whether a TOML value is an int or a float and not a bool.

    Returns:
        True for a real number.

    """
    return isinstance(value, int | float) and not isinstance(value, bool)


def _count(value: object) -> bool:
    """Say whether a TOML value is an integer of at least 1 and not a bool.

    Returns:
        True for a positive integer.

    """
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _freeze_problems(label: str, raw: dict[object, object]) -> list[str]:
    """Collect the faults in a row's `action` and in the keys that belong to a freeze.

    Returns:
        the faults; a `signal` row may not carry a freeze key, a `freeze` row needs all of them.

    """
    action = raw.get("action", "signal")
    if action not in ACTIONS:
        return [f"{label}: action must be one of {ACTIONS}, not {action!r}"]
    present = [key for key in _FREEZE_KEYS if key in raw]
    if action == "signal":
        return [f"{label}: {key!r} only applies to action = 'freeze'" for key in present]
    found = [
        f"{label}: action 'freeze' needs key {key!r}" for key in _FREEZE_KEYS if key not in raw
    ]
    found += [
        f"{label}: {key!r} must be an integer of at least 1"
        for key in ("resume_samples", "max_frozen_samples")
        if key in raw and not _count(raw[key])
    ]
    if "on_cap" in raw and raw["on_cap"] not in CAP_ACTIONS:
        found.append(f"{label}: on_cap must be one of {CAP_ACTIONS}, not {raw['on_cap']!r}")
    return found


def _problems(index: int, raw: dict[object, object]) -> list[str]:
    """Collect every fault in one `[[guard]]` table.

    Returns:
        the faults, each prefixed with the table's position and name.

    """
    label = f"guard #{index + 1} ({raw.get('name', '?')})"
    found = [f"{label}: missing key {key!r}" for key in _KEYS if key not in raw]
    found += [f"{label}: unknown key {key!r}" for key in raw if key not in _KNOWN]
    found += _freeze_problems(label, raw)
    for key in ("name", "endpoint", "query", "target"):
        if key in raw and not (isinstance(raw[key], str) and raw[key]):
            found.append(f"{label}: {key!r} must be a non-empty string")
    if "reading" in raw and raw["reading"] not in READINGS:
        found.append(f"{label}: reading must be one of {READINGS}, not {raw['reading']!r}")
    if "above" in raw and not _number(raw["above"]):
        found.append(f"{label}: 'above' must be a number")
    for key in ("interval_s",):
        if key in raw and not (_number(raw[key]) and cast("float", raw[key]) > 0):
            found.append(f"{label}: {key!r} must be a positive number")
    samples = raw.get("samples")
    if "samples" in raw and not (
        isinstance(samples, int) and not isinstance(samples, bool) and samples >= 1
    ):
        found.append(f"{label}: 'samples' must be an integer of at least 1")
    if "signal" in raw and raw["signal"] not in signal.Signals.__members__:
        found.append(f"{label}: 'signal' must name a signal such as SIGINT, not {raw['signal']!r}")
    return found


def parse(doc: object) -> list[Spec]:
    """Read the specs out of a parsed policy document.

    Returns:
        one `Spec` per `[[guard]]` table.

    Raises:
        PolicyError: naming every fault, when any table is wrong.

    """
    tables = cast("dict[object, object]", doc).get("guard", []) if isinstance(doc, dict) else []
    if not isinstance(tables, list):
        raise PolicyError(["'guard' must be an array of tables ([[guard]])"])
    problems: list[str] = []
    specs: list[Spec] = []
    for index, table in enumerate(cast("list[object]", tables)):
        if not isinstance(table, dict):
            problems.append(f"guard #{index + 1}: not a table")
            continue
        raw = cast("dict[object, object]", table)
        found = _problems(index, raw)
        problems += found
        if not found:
            row = Row(
                name=str(raw["name"]),
                above=float(cast("float", raw["above"])),
                hold=int(cast("int", raw["samples"])),
                interval_s=float(cast("float", raw["interval_s"])),
                signal=int(signal.Signals[str(raw["signal"])]),
                target=str(raw["target"]),
                action=str(raw.get("action", "signal")),
                resume_hold=int(cast("int", raw.get("resume_samples", 0))),
                max_frozen=int(cast("int", raw.get("max_frozen_samples", 0))),
                on_cap=str(raw.get("on_cap", "")),
            )
            specs.append(Spec(row, str(raw["endpoint"]), str(raw["query"])))
    if problems:
        raise PolicyError(problems)
    return specs


def load(path: Path) -> list[Spec]:
    """Read a policy file.

    Returns:
        the specs; none when the file does not exist.

    Raises:
        PolicyError: when the file exists and is not valid TOML or holds a wrong table.

    """
    if not path.is_file():
        return []
    try:
        doc: object = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as problem:
        if not isinstance(problem, (OSError, tomllib.TOMLDecodeError)):
            raise
        raise PolicyError([f"{path}: {problem}"]) from problem
    return parse(doc)
