# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse a stack that touches a mutants grid already past half of its CPU budget (W1602).

⚑ THE RULE IS THE OPERATOR'S (2026-10-18, 695f3e0a line 80168): "If something takes longer than 50%
of a wall timeout, it should be sharded before its next run. We spend a lot on waiting-for-failure."
And its unit (2026-10-20, line 87670): the fraction is measured in whatever unit the failure
threshold is measured in. A mutants grid is bounded by CPU seconds (`cpu_budget` in its dist's
BUILD file since W1778), so the figure compared is a shard's CPU, from the series
`mikemol.gate.target.cpu.seconds` that every gate sends (W1785).

⚑ THE LATEST READING, NOT THE LARGEST (`last_over_time`): a reshard changes what the next run
reads, and a window maximum would go on refusing for days after the fix landed.

⚑ A READING OLDER THAN THE DIST'S LAST BUILD CHANGE IS ABOUT A GRID THAT IS GONE. Resharding lands
a BUILD change, and no gate has run since, so the latest reading is still the old grid's; without
this every stack touching the dist would be refused until a gate ran, which a refused stack cannot
make happen. The reading's time (`tlast_over_time`, seconds) is compared with the commit time of
the dist's BUILD file, and an older reading is not judged.

⚑ NO READING IS NOT A REFUSAL. With no store, no `mikemol-otlp`, or an unreadable answer, nothing is
refused and nothing is said: this gate stops a known-slow grid, it does not guess at an unknown one.

⚑ THE ANSWER NAMES A UNIT, NEVER A COUNT (W2804; operator 2026-11-20, host L198296, L198664 and
L201494, relayed by github-82): "shard" means decompose along the cone, and the unit is a module or
one cell. A flat count by linear rescale was one more raise of the same flat sharding: each wrong
prescription cost a refused round, and the guard asked for 34 to 53 in audiostruct where the
over-half shard held six cells in four modules. The runner logs each cell's CPU and the gate sends
it as `mikemol.gate.cell.cpu.seconds`, so the finding lists the shard's modules with their summed
CPU and its heaviest cell, names a cell alone past half the budget INDIVISIBLE (its source
splits), and says so, never a guess, when the store holds no cell of the shard.

⚑ A RAISE OF `shards` IS REFUSED, STACKS THAT CARRY THE BUILD FILE INCLUDED: the carried file
excuses the READING (a number about the grid as committed), never a higher count. The frozen
BUILD's value is compared with HEAD's, so there is no baseline file to keep, and a lower or deleted
value is admitted.

CONSUMED BY: `commit_kata.submit_problem`, at submit, beside the import and build-file refusals.
"""

import json
import re
from collections.abc import Callable, Collection, Mapping
from pathlib import Path
from typing import cast

from mikemol.hooks import stacksnap
from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.presubmit import dists_of
from mikemol.hooks.runproc import run_process
from mikemol.hooks.stackfreeze import SNAP_ENV
from mikemol.hooks.stackrun import items_of

FRACTION = 0.5
SERIES = "mikemol.gate.target.cpu.seconds"
CELL_SERIES = "mikemol.gate.cell.cpu.seconds"
_LABEL = re.compile(r"^//(?P<dist>[^:]+):mutants_[0-9]+$")
_BUDGET = re.compile(r"\bcpu_budget\s*=\s*(?P<v>[0-9]+)")
_SHARDS = re.compile(r"\bshards\s*=\s*(?P<v>[0-9]+)")

type Reading = tuple[float, float]
"""A shard's latest CPU seconds and the time of that sample, in epoch seconds."""

type Cells = Mapping[str, Mapping[str, float]]
"""A grid's cells' CPU seconds, by shard label and then by the stable cell id."""

ReadBuild = Callable[[str], str | None]
ChangedAt = Callable[[str], float | None]
Run = Callable[[list[str], Path], tuple[int, str]]


def query(repo: str, function: str = "last_over_time") -> str:
    """Build the PromQL for one reading of every mutants shard of a repo.

    Returns:
        the query text: the latest value by default, `tlast_over_time` for the sample's time.

    """
    return f'{function}({SERIES}{{kind="mutants",repo="{repo}"}}[3d])'


def cell_query(repo: str) -> str:
    """Build the PromQL for the latest reading of every cell of a repo's mutants grids.

    Returns:
        the query text over `mikemol.gate.cell.cpu.seconds`.

    """
    return f'last_over_time({CELL_SERIES}{{kind="mutants",repo="{repo}"}}[3d])'


def samples(text: str) -> dict[str, float]:
    """Read `mikemol-otlp query-metrics` lines into target -> value.

    Returns:
        the values; a line that is not a sample of a labelled target is skipped.

    """
    found: dict[str, float] = {}
    for line in text.splitlines():
        try:
            row = cast("dict[str, object]", json.loads(line))
            metric = cast("dict[str, object]", row["metric"])
            value = cast("list[object]", row["value"])
            found[str(metric["target"])] = float(str(value[1]))
        except (ValueError, KeyError, IndexError, TypeError):
            continue
    return found


def cell_samples(text: str) -> dict[str, dict[str, float]]:
    """Read `mikemol-otlp query-metrics` lines into shard label -> cell id -> CPU seconds.

    Returns:
        the values; a line that is not a sample of a labelled shard and cell is skipped.

    """
    found: dict[str, dict[str, float]] = {}
    for line in text.splitlines():
        try:
            row = cast("dict[str, object]", json.loads(line))
            metric = cast("dict[str, object]", row["metric"])
            value = cast("list[object]", row["value"])
            found.setdefault(str(metric["target"]), {})[str(metric["cell"])] = float(str(value[1]))
        except (ValueError, KeyError, IndexError, TypeError):
            continue
    return found


def readings(cpu_text: str, time_text: str) -> dict[str, Reading]:
    """Join the CPU samples and the sample times by target.

    Returns:
        target -> (CPU seconds, epoch seconds); a target with no time is left out, since a reading
        of unknown age cannot be told from one about a grid that is gone.

    """
    times = samples(time_text)
    return {t: (cpu, times[t]) for t, cpu in samples(cpu_text).items() if t in times}


def _number(pattern: re.Pattern[str], build: str) -> int | None:
    found = pattern.search(build)
    return int(found.group("v")) if found else None


_NAME = re.compile(r'\bname\s*=\s*"(?P<v>[^"]+)"')
_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|#[^\n]*|[()]')


def _calls(build: str) -> list[str]:
    # The text between the parentheses of each top-level call of a BUILD file. A string literal and
    # a comment are matched whole, so a parenthesis or a `shards =` inside one is not read as code.
    bodies: list[str] = []
    depth, start = 0, 0
    for token in _TOKEN.finditer(build):
        mark = token.group()
        if mark == "(":
            start = token.end() if depth == 0 else start
            depth += 1
        elif mark == ")" and depth:
            depth -= 1
            if depth == 0:
                bodies.append(build[start : token.start()])
    return bodies


def _uncommented(match: re.Match[str]) -> str:
    # A comment token reads as nothing and every other token as itself, so prose like `shards = 53`
    # in a comment is never taken for a value.
    text = match.group()
    return "" if text.startswith("#") else text


_SHARDS_ANY = re.compile(r"\bshards\s*=\s*(?P<v>[^,\n)]+)")
_CONSTANT = re.compile(r"^(?P<k>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<v>[0-9]+)\s*$", re.MULTILINE)


def _value_of(text: str, constants: Mapping[str, int]) -> int | None:
    # An int literal, or a bare name bound to one at the file's top level; anything else is None.
    word = text.strip()
    return int(word) if word.isdecimal() else constants.get(word)


def parsed_targets(build: str) -> dict[str, int | None]:
    """Read every sharded target of a BUILD file: its `name` and its `shards` value.

    ⚑ A VALUE THAT IS NEITHER AN INT LITERAL NOR A TOP-LEVEL `NAME = <int>` IS None, NOT ABSENT: the
    target is listed so the ratchet can refuse it as unjudgeable instead of losing it.

    Returns:
        name -> shards (None when unreadable) for each top-level call that has a name and a shards.

    """
    clean = _TOKEN.sub(_uncommented, build)
    constants = {found.group("k"): int(found.group("v")) for found in _CONSTANT.finditer(clean)}
    found_targets: dict[str, int | None] = {}
    for body in _calls(clean):
        name, shards = _NAME.search(body), _SHARDS_ANY.search(body)
        if name and shards:
            found_targets[name.group("v")] = _value_of(shards.group("v"), constants)
    return found_targets


def targets(build: str) -> dict[str, int]:
    """Read every sharded target of a BUILD file whose `shards` value can be judged.

    ⚑ EVERY `shards =` IS A VALUE, PAIRED BY ITS TARGET (github-82, W2804): a file can hold more
    than one sharded rule, and the first match is only one of them.

    Returns:
        name -> shards for each top-level call with a readable count; an unreadable one is left
        out here and listed by `parsed_targets`.

    """
    return {name: value for name, value in parsed_targets(build).items() if value is not None}


def unit_of(cells: Mapping[str, float] | None, budget: int) -> str:
    """Name the unit a past-half shard must be decomposed along, from its cells' CPU.

    Returns:
        the unit's description, or the named absence when the store holds no cell of the shard.

    """
    if not cells:
        return "no per-cell reading of this shard is in the store, so its unit cannot be named"
    heavy = max(cells, key=cells.__getitem__)
    spent = cells[heavy]
    if spent > FRACTION * budget:
        return f"{heavy} alone used {spent:.0f} CPU s: INDIVISIBLE, its source is what splits"
    by_module: dict[str, float] = {}
    for cell, cpu in cells.items():
        module = cell.split("::", 1)[0]
        by_module[module] = by_module.get(module, 0.0) + cpu
    ranked = sorted(by_module, key=by_module.__getitem__, reverse=True)
    named = ", ".join(f"{module} {by_module[module]:.0f} s" for module in ranked)
    return (
        f"its {len(cells)} cells span {len(ranked)} module(s) ({named}) and the heaviest cell is "
        f"{heavy} at {spent:.0f} s: give each module its own per-site target"
    )


def findings(
    read: Mapping[str, Reading],
    dists: Collection[str],
    builds: tuple[ReadBuild, ChangedAt],
    cells: Cells | None = None,
) -> list[str]:
    """Name each touched dist's worst current shard that is past half of the dist's CPU budget.

    `builds` is the reader of a dist's BUILD text and the epoch second it last changed; `cells`
    holds the per-cell CPU of each shard, when the store has it.

    Returns:
        one line per dist, naming the shard and the unit to decompose and never a shard count;
        empty when nothing is past the line.

    """
    text_of, changed_at = builds
    worst: dict[str, tuple[str, float]] = {}
    for label, (cpu, at) in read.items():
        matched = _LABEL.match(label)
        dist = matched.group("dist") if matched else ""
        changed = changed_at(dist) if dist in dists else None
        current = dist in dists and (changed is None or at > changed)
        if current and cpu > worst.get(dist, ("", 0.0))[1]:
            worst[dist] = (label, cpu)
    lines: list[str] = []
    for dist, (label, cpu) in sorted(worst.items()):
        build = text_of(dist) or ""
        budget, shards = _number(_BUDGET, build), _number(_SHARDS, build)
        if not budget or not shards or cpu <= FRACTION * budget:
            continue
        lines.append(
            f"{label} used {cpu:.0f} CPU s of {budget} ({100 * cpu / budget:.0f}%), past half "
            f"(shards = {shards} in {dist}/BUILD.bazel is not to be raised): "
            f"{unit_of((cells or {}).get(label), budget)}"
        )
    return lines


def raises_in(path: str, old: str | None, new: str | None) -> list[str]:
    """Say which sharded targets of a BUILD file raise their `shards` over the committed file's.

    ⚑ EVERY TARGET IS COMPARED WITH ITS OWN PRIOR VALUE, IN ANY BUILD FILE (github-82, W2804): a
    target new to the file has no prior value and is admitted, UNLESS another target of the old file
    is gone, when a rename carries the SMALLEST removed value (the ratchet's direction is strict, so
    a new target that could be a raise of any removed one is refused).

    ⚑ A VALUE THAT CANNOT BE READ IS REFUSED, NEVER ADMITTED: a `shards` that is neither an int
    literal nor a name bound to one at the file's top level is unjudgeable, and a target that drops
    out of the ratchet by being unreadable would be an escape.

    Returns:
        one refusal line per target whose count rose or cannot be judged, naming it; empty when
        none did.

    """
    before, after = parsed_targets(old or ""), parsed_targets(new or "")
    removed = [value for name, value in before.items() if name not in after and value is not None]
    carried = min(removed, default=None)
    lines: list[str] = []
    for name, now in after.items():
        if now is None:
            lines.append(
                f"{path} shards of {name} is neither an int literal nor a top-level integer "
                "constant, so it cannot be judged and is refused"
            )
            continue
        prior = before.get(name, carried)
        if prior is not None and now > prior:
            how = "" if name in before else " (carries the smallest removed value)"
            lines.append(
                f"{path} raises shards of {name} from {prior} to {now}{how}: a shards value is "
                "never raised, decompose the over-half unit along its cone (per-site targets)"
            )
    return lines


def _text_of(root: Path) -> ReadBuild:
    def build(dist: str) -> str | None:
        try:
            return (root / dist / "BUILD.bazel").read_text(encoding="utf-8")
        except OSError:
            return None

    return build


def _changed_at(root: Path, run: Run) -> ChangedAt:
    def changed(dist: str) -> float | None:
        status, out = run(["git", "log", "-1", "--format=%ct", "--", f"{dist}/BUILD.bazel"], root)
        return float(out.strip()) if status == 0 and out.strip().isdecimal() else None

    return changed


def _frozen_blobs(env: Mapping[str, str]) -> dict[str, str]:
    # The stack's frozen files by path (a later entry's bytes win), read from the snapshot taken at
    # submit and never from the working tree.
    snap = env.get(SNAP_ENV, "")
    loaded = stacksnap.load(Path(snap)) if snap else None
    return {frozen.path: frozen.blob for entry in loaded or [] for frozen in entry if frozen.blob}


def _raises(root: Path, paths: list[str], env: Mapping[str, str], run: Run) -> list[str]:
    blobs = _frozen_blobs(env)
    found: list[str] = []
    for path in paths:
        if path.rpartition("/")[2] != "BUILD.bazel" or path not in blobs:
            continue
        old_status, old = run(["git", "show", f"HEAD:{path}"], root)
        new_status, new = run(["git", "cat-file", "blob", blobs[path]], root)
        found.extend(
            raises_in(path, old if old_status == 0 else None, new if new_status == 0 else None)
        )
    return found


def refusal(
    root: Path, stack_file: Path, env: Mapping[str, str], run: Run = run_process
) -> str | None:
    """Judge a submitted stack against the latest shard readings and its own `shards` values.

    Returns:
        the findings, one per line, or None when nothing is past the line, no `shards` value rose,
        or nothing could be read (no stack file, no store, no `mikemol-otlp`, an unreadable
        answer). A raise is judged from the snapshot and git alone, whatever the store says.

    """
    items = items_of(stack_file)
    if isinstance(items, str):
        return None
    paths = [path for item in items for path in item.paths]
    raises = _raises(root, paths, env, run)
    program = binary(env)
    if program is None or not store_named(env):
        return "\n".join(raises) if raises else None
    cpu_status, cpu = run([program, "query-metrics", query(root.name)], root)
    time_status, when = run([program, "query-metrics", query(root.name, "tlast_over_time")], root)
    if cpu_status != 0 or time_status != 0:
        return "\n".join(raises) if raises else None
    cell_status, cell_text = run([program, "query-metrics", cell_query(root.name)], root)
    held = cell_samples(cell_text) if cell_status == 0 else {}
    # ⚑ A STACK THAT CARRIES THE DIST'S BUILD FILE IS THE REPAIR AND ITS READING IS NOT JUDGED
    # (found by the first real refusal, 2026-10-22): the reading is about the grid as committed,
    # while the shard count is read from the tree this stack changes, so a proposal came out
    # against the wrong count (80 measured, 102 set, 130 demanded). A RAISE IN IT IS REFUSED ABOVE.
    carried = {path.removesuffix("/BUILD.bazel") for path in paths if path.endswith("/BUILD.bazel")}
    dists = [dist for dist in dists_of(paths) if dist not in carried]
    found = findings(readings(cpu, when), dists, (_text_of(root), _changed_at(root, run)), held)
    both = [*raises, *found]
    return "\n".join(both) if both else None
