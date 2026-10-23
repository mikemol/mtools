# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A reading taken before and after an apply, and whether it advanced and is fresh (W1871).

An exit 0 can be a failed apply's: a no-op apply and a failed one both leave "the rules match" true
before and after (luthen-observability:W1550). A witness entry may therefore declare a `reading`,
`{tool, args, advances?, fresh_since?}`, taken before the apply and again after it.

⚑ `advances` NAMES A POINTER INTO THE READING'S JSON (dotted keys; the empty string means the whole
trimmed stdout) whose value must DIFFER after the apply from before it. Inequality only: a value
such as a Kubernetes resourceVersion is opaque, so "greater than" would be a guess.

⚑ `fresh_since` NAMES A POINTER TO A TIMESTAMP in the after-reading that must be at or after the
apply's start, so a reading the apply did not make cannot pass.

⚑ NOTHING THAT CANNOT BE JUDGED IS A PASS: a reading that cannot be taken, a pointer that is absent
from either reading, a timestamp that does not parse and a reading that declares neither check are
each a failure with the reason.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mikemol.waldo.planjson import Json, as_list, as_object, parse_object
from mikemol.waldo.plantools import Tools

READ = "read"
CANNOT_RUN = "cannot-run"
DEFAULT_CPU_SECONDS = 120


def cpu_of(entry: Json) -> int:
    """Read the CPU bound of a witness or reading entry.

    Returns:
        the entry's own `cpu_seconds` when it is an int and not a bool, else the default.

    """
    cpu = entry.get("cpu_seconds", DEFAULT_CPU_SECONDS)
    return cpu if isinstance(cpu, int) and not isinstance(cpu, bool) else DEFAULT_CPU_SECONDS


def take(tools: Tools, cwd: Path, spec: Json) -> Json:
    """Take one reading, bounded by CPU.

    Returns:
        `{"status": "read", "stdout": text}`, or `{"status": "cannot-run", "why": reason}` when the
        tool is not found, no bounded runner exists or the command exits non-zero.

    """
    name = str(spec.get("tool", ""))
    tool = tools.find(name)
    if tool is None:
        return {"status": CANNOT_RUN, "why": f"reading tool {name!r} not found"}
    args = [str(a) for a in as_list(spec.get("args", []))]
    try:
        proc = tools.run_bounded(tool, *args, cwd=cwd, cpu_seconds=cpu_of(spec))
    except OSError as exc:
        return {"status": CANNOT_RUN, "why": f"no CPU-bounded runner: {exc}"}
    if proc.returncode != 0:
        return {"status": CANNOT_RUN, "why": f"reading {name!r} exited {proc.returncode}"}
    return {"status": READ, "stdout": proc.stdout or ""}


def value(stdout: str, pointer: str) -> str | None:
    """Pick the value a pointer names out of a reading.

    Returns:
        the whole trimmed stdout for the empty pointer; else the string at a dotted path through the
        JSON object (a non-string value as JSON text); None when the path is absent.

    """
    if not pointer:
        return stdout.strip()
    found: object = parse_object(stdout)
    for key in pointer.split("."):
        if not isinstance(found, dict):
            return None
        found = as_object(found).get(key)
    if found is None:
        return None
    return found if isinstance(found, str) else json.dumps(found, sort_keys=True)


def _moment(stamp: str | None) -> datetime | None:
    if stamp is None:
        return None
    try:
        return datetime.fromisoformat(stamp)
    except ValueError:
        return None


def _stuck(spec: Json, before: Json, after: Json) -> str | None:
    pointer = str(spec["advances"])
    was, now = value(str(before["stdout"]), pointer), value(str(after["stdout"]), pointer)
    if was is None or now is None:
        return f"advances pointer {pointer!r} is absent from a reading"
    return f"did not advance: {pointer or 'the reading'} is still {now!r}" if now == was else None


def _stale(spec: Json, after: Json, started: str) -> str | None:
    pointer = str(spec["fresh_since"])
    said = value(str(after["stdout"]), pointer)
    read_at, began = _moment(said), _moment(started)
    if read_at is None or began is None:
        return f"fresh_since pointer {pointer!r} is absent or not a timestamp"
    return f"stale: read at {said}, the apply began {started}" if read_at < began else None


def judge(spec: Json, before: Json | None, after: Json, started: str) -> str | None:
    """Judge whether the reading advanced and is fresh.

    Returns:
        the reason the reading fails the witness, or None when it holds.

    """
    if "advances" not in spec and "fresh_since" not in spec:
        return "the reading declares neither advances nor fresh_since, so it proves nothing"
    if before is None or before.get("status") != READ:
        return "no reading was taken before the apply"
    if after.get("status") != READ:
        return f"the reading after the apply cannot run: {after.get('why')}"
    stuck = _stuck(spec, before, after) if "advances" in spec else None
    return stuck or (_stale(spec, after, started) if "fresh_since" in spec else None)


@dataclass(frozen=True)
class Prior:
    """What was true before the apply: the reading taken then, and the moment the apply began."""

    reading: Json | None = None
    started: str = ""


def verdict(tools: Tools, cwd: Path, spec: Json | None, prior: Prior, result: Json) -> Json:
    """Fold the reading into a witness result.

    A root with no reading keeps its result. A reading that holds adds `reading: advanced`; one that
    does not turns a passing exit into `fail` (or `cannot-run` when it could not be taken) with the
    reason, and never softens a result that had already failed.

    Returns:
        the witness result, with the reading's outcome.

    """
    if spec is None:
        return result
    after = take(tools, cwd, spec)
    why = judge(spec, prior.reading, after, prior.started)
    if why is None:
        return {**result, "reading": "advanced"}
    status = result["status"]
    if status == "pass":
        status = CANNOT_RUN if after.get("status") == CANNOT_RUN else "fail"
    return {**result, "status": status, "why": why, "reading": "failed"}
