# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 6: `mikemol-transcriptstruct` — the queries, from a shell, refusing what it does not know.

- ⚑ AN UNKNOWN FLAG IS REFUSED (exit 2). substrate's `_arg` ignored any flag it did not look
  for, so a mistyped `--timestamps` ran the default query and its answer read as the answer to
  the question asked. argparse refuses it, and names it;
- the bare invocation is the CHEAP read, `--stats`: a population summary, never a dump;
- output is JSON lines, one per hit, whole — the text is never cut — and every query ends with
  a `#` line carrying its denominators, so "n of m" is on the page, not in the reader's head.

The console name follows the mtools convention (`mikemol-paths-forward`, `mikemol-membudget`),
not the study's bare `transcriptstruct`. Options are read through `vars()` into a
`dict[str, object]` and narrowed per key, as pathsforward's cli does, because argparse's
Namespace is untyped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.transcriptstruct.query import (
    Window,
    extract,
    grep_blocks,
    grep_prose,
    prose,
    raw,
    stats,
)
from mikemol.transcriptstruct.records import read_path

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import TextIO

    from mikemol.transcriptstruct.blocks import Block
    from mikemol.transcriptstruct.query import Hit, Result, Stats

_DEFAULT_SPEAKERS = ("human", "peer", "assistant")


def _raw(path: Path, types: Sequence[str], window: Window) -> Result:
    """Read whole records of the named envelope types.

    Returns:
        the hits and their denominators.

    """
    return raw(read_path(path), types, window=window)


def _parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        the parser; its modes are mutually exclusive and `--stats` is the default.

    """
    parser = argparse.ArgumentParser(
        prog="mikemol-transcriptstruct",
        description="Query a Claude Code transcript (JSONL) by record, block and speaker.",
    )
    parser.add_argument("transcript")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--stats", action="store_true", help="population counts (the default)")
    mode.add_argument("--grep", metavar="REGEX", help="search decoded block text")
    mode.add_argument("--human", metavar="REGEX", help="search what the operator said")
    mode.add_argument("--prose", action="store_true", help="list utterances, whole, in order")
    mode.add_argument("--extract", metavar="LINE", type=int, nargs="+", help="lines' blocks")
    mode.add_argument("--raw", metavar="TYPE", nargs="+", help="whole records of these types")
    parser.add_argument("--kinds", nargs="+", help="--grep: only these block kinds")
    parser.add_argument("--speakers", nargs="+", help="--prose: only these speaker kinds")
    parser.add_argument(
        "--scheduled",
        action="append",
        metavar="PREFIX",
        help="a prompt prefix the scheduler emits (repeatable)",
    )
    parser.add_argument("--since", type=int, help="first line to search (1-based, inclusive)")
    parser.add_argument("--until", type=int, help="last line to search (inclusive)")
    return parser


def _text(opts: dict[str, object], key: str) -> str | None:
    """Read a string option.

    Returns:
        the value, or None when unset.

    """
    value = opts.get(key)
    return None if value is None else str(value)


def _texts(opts: dict[str, object], key: str) -> tuple[str, ...] | None:
    """Read a list option as strings.

    Returns:
        the values, or None when unset.

    """
    value = opts.get(key)
    return None if value is None else tuple(str(v) for v in cast("list[object]", value))


def _number(opts: dict[str, object], key: str) -> int | None:
    """Read an integer option.

    Returns:
        the value, or None when unset.

    """
    value = opts.get(key)
    return value if isinstance(value, int) else None


def _line(value: dict[str, object]) -> str:
    """Serialise one output object as a JSON line, non-ASCII kept as written.

    Returns:
        the line, newline-terminated.

    """
    return json.dumps(value, ensure_ascii=False) + "\n"


def _hit(hit: Hit) -> dict[str, object]:
    """Spell a hit as a JSON object.

    Returns:
        its line, kind, whole text and span.

    """
    return {"line": hit.line, "kind": hit.kind, "text": hit.text, "span": list(hit.span)}


def _block(block: Block) -> dict[str, object]:
    """Spell a block as a JSON object.

    Returns:
        its kind, whole text, path and decoded flag.

    """
    return {
        "kind": block.kind,
        "text": block.text,
        "path": list(block.path),
        "decoded": block.decoded,
    }


def _stats(counts: Stats) -> dict[str, object]:
    """Spell stats as a JSON object.

    Returns:
        every population count.

    """
    return {
        "total": counts.total,
        "malformed": counts.malformed,
        "unknown": counts.unknown,
        "unknown_types": counts.unknown_types,
        "speakers": counts.speakers,
        "block_kinds": counts.block_kinds,
        "undecoded_blocks": counts.undecoded_blocks,
        "undecoded_strings": counts.undecoded_strings,
    }


def _emit(result: Result, out: TextIO) -> None:
    """Write a result's hits as JSON lines, then its denominators."""
    out.writelines(_line(_hit(hit)) for hit in result.hits)
    out.write(
        f"# {len(result.hits)} hit(s) in {result.searched} searched of {result.total} "
        f"record(s), {result.malformed} malformed\n"
    )


def _extract(path: Path, lines: Sequence[str], out: TextIO) -> None:
    """Write each requested line's blocks, or null for a line with no record."""
    found = extract(read_path(path), [int(line) for line in lines])
    for line, got in sorted(found.items()):
        body = None if got is None else [_block(block) for block in got]
        out.write(_line({"line": line, "blocks": body}))


def main(argv: Sequence[str] | None = None, out: TextIO | None = None) -> int:
    """Run one query over one transcript.

    Returns:
        0 on success. argparse exits 2 on an unknown flag or a bad value.

    """
    opts: dict[str, object] = vars(_parser().parse_args(sys.argv[1:] if argv is None else argv))
    sink = out or sys.stdout
    path = Path(str(opts["transcript"]))
    window = Window(_number(opts, "since"), _number(opts, "until"))
    scheduled = _texts(opts, "scheduled") or ()
    grep, human, lines = _text(opts, "grep"), _text(opts, "human"), _texts(opts, "extract")
    types = _texts(opts, "raw")
    if types is not None:
        _emit(_raw(path, types, window), sink)
    elif grep is not None:
        kinds = _texts(opts, "kinds")
        _emit(grep_blocks(read_path(path), grep, block_kinds=kinds, window=window), sink)
    elif human is not None:
        found = grep_prose(
            read_path(path), human, speakers={"human"}, scheduled=scheduled, window=window
        )
        _emit(found, sink)
    elif opts.get("prose") is True:
        speakers = _texts(opts, "speakers") or _DEFAULT_SPEAKERS
        _emit(prose(read_path(path), speakers=speakers, scheduled=scheduled, window=window), sink)
    elif lines is not None:
        _extract(path, lines, sink)
    else:
        sink.write(_line(_stats(stats(read_path(path), scheduled=scheduled))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
