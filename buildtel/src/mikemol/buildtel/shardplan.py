# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1573: propose a shard count for each test grid that ran over half its limit.

    python -m mikemol.buildtel.targettimes <commit-log> > rows.jsonl
    python -m mikemol.buildtel.shardplan rows.jsonl <repo-root>

The second call is a dry run: it prints a diff of the shards lines and writes nothing.

⚑ THE RULE IS THE OPERATOR'S (2026-10-18, 695f3e0a line 80168): "If something takes longer than
50% of a wall timeout, it should be sharded before its next run. We spend a lot on
waiting-for-failure." A target whose latest run, a TIMED_OUT one included, took more than
`FRACTION` of its limit gets the shard count that puts the average shard under that fraction,
never fewer than one more than it has.

⚑ THE LIMIT IS THE SIZE DEFAULT, NEVER AN EXPLICIT TIMEOUT (github-8f, 2026-10-18; the operator's
2026-10-10 ruling that a raised limit is the wall-clock fix and finer shards are the cure). A grid
that declares `timeout` is planned against its size's default anyway and reported, because
pathsforward's `timeout = "long"` is why its 416 s shard passed while debtplan's 300.1 s timed out.

⚑ A GRID IS `//dist:name_K` FOR EVERY K, READ FROM A `mutants_sharded(name = "name", shards = N)`
BLOCK OF `dist/BUILD.bazel`. A target that is not a numbered shard of such a block cannot be
resharded here and is named as a finding, so a slow plain test is not lost.

⚑ ONLY COMPLETE ROWS COUNT (W1572): a row from an invocation `bb_targets` called incomplete is not
a maximum of anything, and the count of those left out is printed.
"""

import json
import math
import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

EXIT_USAGE = 2
EXIT_STALE = 3
APPLY_FLAG = "--apply"
FRACTION = 0.5
LIMITS = {"small": 60, "medium": 300, "large": 900}
DEFAULT_SIZE = "medium"
_ARGC = 2
_MS = 1000
_LABEL = re.compile(r"^//(?P<dist>[^:]+):(?P<name>.+)_(?P<k>[0-9]+)$")
_BLOCK = re.compile(r"mutants_sharded\((?P<body>.*?)\n\)", re.DOTALL)
_NAME = re.compile(r'\bname\s*=\s*"(?P<v>[^"]+)"')
_SHARDS = re.compile(r"\bshards\s*=\s*(?P<v>[0-9]+)")
_SIZE = re.compile(r'\bsize\s*=\s*"(?P<v>[^"]+)"')
_TIMEOUT = re.compile(r'\btimeout\s*=\s*"(?P<v>[^"]+)"')
ReadBuild = Callable[[str], str | None]
Row = dict[str, object]


@dataclass(frozen=True)
class Block:
    """What a `mutants_sharded` block declares: its shards, size and any explicit timeout."""

    shards: int
    size: str
    timeout: str


@dataclass(frozen=True)
class Proposal:
    """One grid that ran over the fraction of its limit, and the count that fixes it."""

    dist: str
    name: str
    old: int
    new: int
    limit_s: int
    slowest_s: float
    timeout: str

    def line(self) -> str:
        """Spell the dry-run diff line.

        Returns:
            the proposal as one line, with the explicit timeout named when there is one.

        """
        share = round(100 * self.slowest_s / self.limit_s)
        said = f"{self.dist}/BUILD.bazel {self.name}: shards {self.old} -> {self.new}"
        said += f" (slowest {self.slowest_s:.1f} s of a {self.limit_s} s default, {share}%)"
        return f"{said}; REMOVE timeout = {self.timeout!r}" if self.timeout else said


def _value(pattern: re.Pattern[str], body: str) -> str:
    found = pattern.search(body)
    return found.group("v") if found else ""


def block_of(build: str, name: str) -> Block | None:
    """Read the `mutants_sharded` block named `name` out of a BUILD file's text.

    Returns:
        its shards, size (the default when absent) and timeout ("" when absent), or None when no
        block of that name declares a shard count.

    """
    for found in _BLOCK.finditer(build):
        body = found.group("body")
        shards = _value(_SHARDS, body)
        if shards and _value(_NAME, body) == name:
            return Block(int(shards), _value(_SIZE, body) or DEFAULT_SIZE, _value(_TIMEOUT, body))
    return None


def _shard_times(rows: Sequence[Row]) -> tuple[dict[tuple[str, str], list[int]], list[str]]:
    # Complete rows grouped by (dist, grid name); a slow row that is no numbered shard is a finding.
    grids: dict[tuple[str, str], list[int]] = {}
    plain: list[str] = []
    for row in rows:
        millis = row.get("millis")
        if row.get("complete") is not True or not isinstance(millis, int):
            continue
        label = str(row.get("label", ""))
        parts = _LABEL.match(label)
        if parts is not None:
            grids.setdefault((parts.group("dist"), parts.group("name")), []).append(millis)
        elif millis > FRACTION * LIMITS[DEFAULT_SIZE] * _MS:
            plain.append(f"{label}: {millis / _MS:.1f} s is not a numbered shard; not resharded")
    return grids, plain


shard_times = _shard_times


def block_spans(build: str) -> list[re.Match[str]]:
    """Find every `mutants_sharded(...)` block of a BUILD file's text.

    Returns:
        the matches, whose `body` group is the text between the parentheses.

    """
    return list(_BLOCK.finditer(build))


def name_of(body: str) -> str:
    """Read the `name` attribute out of a block's body.

    Returns:
        the name, or "" when the body names none.

    """
    return _value(_NAME, body)


def _proposal(dist: str, name: str, times: Sequence[int], block: Block) -> Proposal | None:
    # A proposal when the slowest shard is over the fraction of its size default, else None.
    limit = LIMITS.get(block.size, LIMITS[DEFAULT_SIZE])
    slowest = max(times) / _MS
    if slowest <= FRACTION * limit:
        return None
    wanted = math.ceil(sum(times) / _MS / (FRACTION * limit))
    new = max(wanted, block.shards + 1)
    return Proposal(dist, name, block.shards, new, limit, slowest, block.timeout)


def plan(rows: Sequence[Row], read_build: ReadBuild) -> tuple[list[Proposal], list[str]]:
    """Plan every grid whose slowest shard took over the fraction of its size default.

    Returns:
        the proposals, slowest grid first, and a finding line for each over-fraction target that
        cannot be resharded here.

    """
    grids, findings = _shard_times(rows)
    out: list[Proposal] = []
    for (dist, name), times in grids.items():
        build = read_build(dist)
        block = None if build is None else block_of(build, name)
        if block is None:
            findings.append(f"//{dist}:{name}: no mutants_sharded block with shards; not resharded")
            continue
        proposed = _proposal(dist, name, times, block)
        if proposed is not None:
            out.append(proposed)
    out.sort(key=lambda p: -p.slowest_s)
    return out, findings


class StaleDiffError(ValueError):
    """The BUILD file no longer matches the plan: a grid is gone or its count has moved."""


def rewrite(build: str, proposal: Proposal) -> str:
    """Set one grid's `shards` line to the proposed count, changing nothing else.

    ⚑ THE DIFF MUST STILL MATCH THE FILE (W1574): the plan was drawn from a reading of the BUILD
    file, so a grid that is gone, or whose count is no longer the one the plan started from, is
    refused and the caller writes nothing.

    Returns:
        the BUILD text with only that grid's `shards = N` replaced.

    Raises:
        StaleDiffError: when no block of that name exists or its count differs from the plan's.

    """
    for found in _BLOCK.finditer(build):
        body = found.group("body")
        if _value(_NAME, body) != proposal.name:
            continue
        if _value(_SHARDS, body) != str(proposal.old):
            msg = f"{proposal.dist}: {proposal.name} no longer has shards = {proposal.old}"
            raise StaleDiffError(msg)
        changed = _SHARDS.sub(f"shards = {proposal.new}", body, count=1)
        return build[: found.start("body")] + changed + build[found.end("body") :]
    msg = f"{proposal.dist}: no mutants_sharded block named {proposal.name}"
    raise StaleDiffError(msg)


def apply(root: Path, proposals: Sequence[Proposal]) -> list[str]:
    """Write every proposal into its dist's BUILD.bazel, all or none, one temp file and a replace.

    Returns:
        one line per rewritten grid: the dist, the grid and the old and new counts.

    Raises:
        StaleDiffError: before anything is written, when any proposal no longer matches its file.

    """
    texts: dict[Path, str] = {}
    for proposal in proposals:
        build = root / proposal.dist / "BUILD.bazel"
        if build.is_symlink() or not build.is_file():
            msg = f"{proposal.dist}: BUILD.bazel is missing or a link"
            raise StaleDiffError(msg)
        texts[build] = rewrite(texts.get(build) or build.read_text(encoding="utf-8"), proposal)
    for build, text in texts.items():
        staging = build.with_name(f"{build.name}.shardplan.tmp")
        staging.write_text(text, encoding="utf-8")
        staging.replace(build)
    return [f"{p.dist} {p.name}: shards {p.old} -> {p.new}" for p in proposals]


def _read_rows(path: Path) -> list[Row]:
    rows: list[Row] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row: object = json.loads(raw)
        if isinstance(row, dict):
            rows.append({str(k): v for k, v in row.items()})
    return rows


read_rows = _read_rows


def main(argv: Sequence[str] | None = None) -> int:
    """Print the plan for a rows file; with `--apply` write it into the BUILD files.

    ⚑ A DRY RUN UNLESS ASKED (W1574): `--apply` rewrites only each grid's `shards` line, all or
    none, and refuses with exit 3 when a BUILD file no longer matches the plan it was drawn from.

    Returns:
        0, 2 for a usage error or a rows file that is a link or unreadable, 3 for a stale plan.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    applying = args[_ARGC:] == [APPLY_FLAG]
    if len(args) != _ARGC + int(applying):
        sys.stderr.write("shardplan <rows.jsonl> <repo-root> [--apply]\n")
        return EXIT_USAGE
    path, root = Path(args[0]), Path(args[1])
    if path.is_symlink():
        sys.stderr.write(f"shardplan: {path} is a symlink; refused\n")
        return EXIT_USAGE
    try:
        rows = _read_rows(path)
    except (OSError, ValueError) as err:
        sys.stderr.write(f"shardplan: {path}: {err}\n")
        return EXIT_USAGE

    def read_build(dist: str) -> str | None:
        build = root / dist / "BUILD.bazel"
        return None if build.is_symlink() or not build.is_file() else build.read_text("utf-8")

    proposals, findings = plan(rows, read_build)
    for proposal in proposals:
        sys.stdout.write(proposal.line() + "\n")
    for finding in findings:
        sys.stdout.write(f"FINDING {finding}\n")
    left_out = sum(1 for row in rows if row.get("complete") is not True)
    sys.stdout.write(f"{len(proposals)} grid(s) over {FRACTION:.0%}; {left_out} row(s) left out\n")
    if not applying:
        return 0
    try:
        for said in apply(root, proposals):
            sys.stdout.write(f"APPLIED {said}\n")
    except StaleDiffError as err:
        sys.stderr.write(f"shardplan: nothing written: {err}\n")
        return EXIT_STALE
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
