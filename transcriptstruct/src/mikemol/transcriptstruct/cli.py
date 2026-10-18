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

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO, cast

from mikemol.transcriptstruct.blocks import Block
from mikemol.transcriptstruct.harvest import harvest
from mikemol.transcriptstruct.memaudit import audit
from mikemol.transcriptstruct.query import (
    Hit,
    Result,
    Stats,
    Window,
    extract,
    grep_blocks,
    grep_prose,
    prose,
    raw,
    stats,
)
from mikemol.transcriptstruct.records import read_path
from mikemol.transcriptstruct.rulingq import rulings
from mikemol.transcriptstruct.rulings import harvest_tree
from mikemol.transcriptstruct.warrant import verify

_REFUSED = 1
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
    mode.add_argument(
        "--verify",
        metavar="UUID",
        help="W1385: read the record a warrant cites; exit 1 and say why when it does not hold",
    )
    mode.add_argument(
        "--audit-memory",
        action="store_true",
        help="W1541: the positional is a memory directory; print one row per finding (GRANT, "
        "WARRANTED, UNWARRANTED, POSSIBLY-SUPERSEDED) against its project's transcripts, read-only",
    )
    mode.add_argument(
        "--harvest",
        action="store_true",
        help="W1386: one PROV-O entity per operator utterance, with its needle, as JSON lines",
    )
    mode.add_argument(
        "--harvest-tree",
        metavar="LEDGER",
        help="W1401/W1402: the positional is a projects directory; append every new operator "
        "utterance under it to LEDGER (append-only, incremental by uuid)",
    )
    mode.add_argument(
        "--rulings",
        metavar="REGEX",
        help="W1387: the positional is a rulings LEDGER; print the operator's utterances matching "
        "REGEX (case-insensitive), newest first, with their citations",
    )
    parser.add_argument("--limit", type=int, help="--rulings: at most this many, the newest")
    parser.add_argument("--claim", help="--verify: the speaker claimed (`operator` needs human)")
    parser.add_argument("--line", type=int, help="--verify: the line the warrant cites")
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
        its line, kind, whole text, span, and the record's uuid and timestamp (W1521), so a ruling
        found by `--human` can be warranted from the same row.

    """
    return {
        "line": hit.line,
        "kind": hit.kind,
        "text": hit.text,
        "span": list(hit.span),
        "uuid": hit.uuid,
        "at": hit.at,
    }


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


def _harvest(path: Path, scheduled: Sequence[str], out: TextIO) -> None:
    """Write each operator utterance of one transcript as a JSON-LD line, then the counts."""
    found = harvest(read_path(path), path, scheduled)
    out.writelines(_line(entity) for entity in found.entities)
    out.write(
        f"# {len(found.entities)} entity(ies), {found.uncitable} human utterance(s) uncitable\n"
    )


def _rulings(ledger: Path, topic: str, limit: int | None, out: TextIO) -> None:
    """Write the rulings matching `topic`, newest first, one JSON line each, then the count."""
    matches = rulings(ledger, topic, limit)
    out.writelines(
        _line(
            {
                "iri": r.iri,
                "said_at": r.said_at,
                "line": r.line,
                "session": r.session,
                "needle": r.needle,
            }
        )
        for r in matches
    )
    out.write(f"# {len(matches)} ruling(s) match\n")


def _verify(opts: dict[str, object], uuid: str, out: TextIO) -> int:
    """Read the record a warrant cites and print the verdict as one JSON line.

    Returns:
        0 when the citation holds, 1 when it does not.

    """
    verdict = verify(
        read_path(Path(str(opts["transcript"]))),
        uuid,
        claim=_text(opts, "claim"),
        line=_number(opts, "line"),
        scheduled=_texts(opts, "scheduled") or (),
    )
    out.write(
        _line(
            {
                "ok": verdict.ok,
                "reason": verdict.reason,
                "line": verdict.line,
                "timestamp": verdict.timestamp,
                "kind": verdict.kind,
            }
        )
    )
    return 0 if verdict.ok else _REFUSED


def _special(
    opts: dict[str, object], path: Path, scheduled: Sequence[str], out: TextIO
) -> int | None:
    """Run the modes that are not a query over one transcript's records, when one is asked for.

    Returns:
        that mode's exit code, or None when none of them was asked for.

    """
    cited = _text(opts, "verify")
    if cited is not None:
        return _verify(opts, cited, out)
    topic = _text(opts, "rulings")
    if topic is not None:
        _rulings(path, topic, _number(opts, "limit"), out)
        return 0
    ledger = _text(opts, "harvest_tree")
    if ledger is not None:
        done = harvest_tree(path, Path(ledger), scheduled)
        out.write(
            f"# read {done.read} file(s), spared {done.spared}, added {done.added} line(s), "
            f"{done.uncitable} human utterance(s) uncitable\n"
        )
        return 0
    if opts.get("harvest") is True:
        _harvest(path, scheduled, out)
        return 0
    if opts.get("audit_memory") is True:
        out.writelines(f"{row.text()}\n" for row in audit(path))
        return 0
    return None


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
    special = _special(opts, path, scheduled, sink)
    if special is not None:
        return special
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
