# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The post-apply witness: the root's declared check runs after an apply and is kept (W1853).

Ported from luthen's `checks/opa_plan.py` (lines 659-714, W259), behind `PlanConfig` and `Tools`.

⚑ A WITNESS THAT CANNOT RUN IS A FAILURE, NEVER A PASS: an undeclared root, an unreadable
declaration, a missing tool and a runner that cannot bound CPU each give `cannot-run`. A root whose
declaration says in words that it has no witness yet gives `none-declared`, and the words are kept.
Absence is not health.

⚑ BOUNDED BY CPU TIME, NEVER THE CLOCK (operator ruling 2026-09-24): the apply has already
happened, so a witness that spins must not hold the process after it. The bound is the entry's own
`cpu_seconds` or `WITNESS_CPU_SECONDS`, run through `Tools.run_bounded`.

⚑ THE RESULT IS KEPT BESIDE THE VERDICT IT BELONGS TO (same state directory, same hash) as
`<digest>.witness.json`.

⚑ THE TIME IS THE CALLER'S: `now` is passed in as an RFC 3339 string, so this module reads no
clock. `python` in a declaration is resolved by the consumer's `Tools.find` like any other tool
name; luthen maps it to its own interpreter there, as its code did.
"""

import json
from pathlib import Path

from mikemol.waldo.planconfig import PlanConfig
from mikemol.waldo.planjson import Json, as_list, as_object, parse_object
from mikemol.waldo.plantools import Tools
from mikemol.waldo.planverdict import verdict_path

WITNESS_CPU_SECONDS = 120
TAIL_LINES = 20
RECORD_MODE = 0o644


def declared_witness(config: PlanConfig, root_name: str) -> Json | str:
    """Read the root's witness declaration.

    Returns:
        the entry for the root, or the reason it cannot be read or is absent.

    """
    path = config.witness_data()
    try:
        doc = parse_object(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return f"witness declaration unreadable: {exc}"
    roots = as_object(None if doc is None else doc.get("roots"))
    if not roots:
        return "witness declaration unreadable: no roots table"
    if root_name not in roots:
        return f"root {root_name!r} has no entry in {path.name} (absence is not health)"
    return as_object(roots[root_name])


def tail_lines(text: str, keep: int = TAIL_LINES) -> list[str]:
    """Take the last lines of a tool's output.

    Returns:
        the last `keep` lines.

    """
    return text.strip().splitlines()[-keep:]


def run_witness(tools: Tools, config: PlanConfig, root_name: str, now: str) -> Json:
    """Run the root's declared post-apply witness.

    Returns:
        the result: status `pass` (exit 0), `fail` (non-zero), `cannot-run` (undeclared, unreadable,
        tool not found, no bounded runner) or `none-declared`, with the evidence of a run.

    """
    result: Json = {"root": root_name, "as_of": now}
    entry = declared_witness(config, root_name)
    if isinstance(entry, str):
        return {**result, "status": "cannot-run", "why": entry}
    if "none" in entry:
        return {**result, "status": "none-declared", "why": str(entry["none"])}
    name = str(entry.get("tool", ""))
    args = [str(a) for a in as_list(entry.get("args", []))]
    tool = tools.find(name)
    if tool is None:
        return {**result, "status": "cannot-run", "why": f"witness tool {name!r} not found"}
    cpu = entry.get("cpu_seconds", WITNESS_CPU_SECONDS)
    seconds = cpu if isinstance(cpu, int) and not isinstance(cpu, bool) else WITNESS_CPU_SECONDS
    try:
        proc = tools.run_bounded(tool, *args, cwd=config.root, cpu_seconds=seconds)
    except OSError as exc:
        return {**result, "status": "cannot-run", "why": f"no CPU-bounded runner: {exc}"}
    return {
        **result,
        "status": "pass" if proc.returncode == 0 else "fail",
        "argv": [name, *args],
        "exit": proc.returncode,
        "stdout_tail": tail_lines(proc.stdout or ""),
        "stderr_tail": tail_lines(proc.stderr or ""),
    }


def store_witness(config: PlanConfig, root_name: str, digest: str, result: Json) -> Path:
    """Write the witness result beside the verdict it belongs to (same state dir, same hash).

    Returns:
        the record's path.

    """
    record = verdict_path(config.state_dir(root_name), digest).with_name(f"{digest}.witness.json")
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(result, indent=1), encoding="utf-8")
    record.chmod(RECORD_MODE)
    return record
