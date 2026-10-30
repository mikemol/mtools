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
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO, cast

from mikemol.transcriptstruct import (
    authfail,
    commitexport,
    commitledger,
    commitrows,
    sample,
    turnlayer,
)
from mikemol.transcriptstruct.blocks import Block
from mikemol.transcriptstruct.cacheturns import Turn, turns
from mikemol.transcriptstruct.commitments import Commitment
from mikemol.transcriptstruct.commitments import extract as extract_commitments
from mikemol.transcriptstruct.gitlog import read as read_git_log
from mikemol.transcriptstruct.harvest import harvest
from mikemol.transcriptstruct.intents import diverged as diverged_intents
from mikemol.transcriptstruct.intents import resolve as resolve_intents
from mikemol.transcriptstruct.intentsio import cards_of, trailers_of
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
from mikemol.transcriptstruct.turnstart import turn_start
from mikemol.transcriptstruct.warrant import verify

DIVERGED_INTENTS = diverged_intents
RESOLVE_INTENTS = resolve_intents
CARDS_OF = cards_of
TRAILERS_OF = trailers_of
_REFUSED = 1
_USAGE = 2
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
        "--cache-turns",
        action="store_true",
        help="W1830: one row per assistant API call: cache_read, cache_creation, the gap "
        "to the previous call, the model and what woke it; the cold ones flagged",
    )
    mode.add_argument(
        "--commitments",
        action="store_true",
        help="W1931: one JSON line per statement of known-needed, unpersisted work the "
        "assistant made (line, uuid, session, repo, family, text, names), then the count",
    )
    mode.add_argument(
        "--intents",
        action="store_true",
        help="W2101: the commitments, each resolved by what landed: landed, closed, missed, "
        "unchecked or pending, with --queue (the cards), --git-log (the trailers) and --bound",
    )
    mode.add_argument(
        "--resolve",
        action="store_true",
        help="W1986: the positional is a JSON-lines file of commitment rows another extractor "
        "wrote; resolve them against --queue for --repo into the ledger document",
    )
    mode.add_argument(
        "--auth-failed",
        action="store_true",
        help="W2040: one JSON line for the transcript: session id, project (the directory "
        "name, never a path), failed-authentication turns, the run of them at the tail and the "
        "newest; read from record metadata only, never message content",
    )
    mode.add_argument(
        "--commitments-tree",
        action="store_true",
        help="W2048: the positional is a projects directory; resolve every repository's "
        "commitments against its own queue and write ONE document of the exported keys only "
        "(repo, session, at, names, state, layer, resolved_by: never the sentence, uuid or "
        "line) to --out whole or not at all, or to stdout",
    )
    mode.add_argument(
        "--turn-start",
        action="store_true",
        help="W1903: where the latest turn began (a prompt, a wake, a notification or a peer "
        "message; not a tool result or a Stop block) and how many Stop blocks it has had, as "
        "one JSON line",
    )
    mode.add_argument(
        "--harvest",
        action="store_true",
        help="W1386: one PROV-O entity per operator utterance, with its needle, as JSON lines",
    )
    mode.add_argument(
        "--sample",
        metavar="N",
        type=int,
        help="W1966: draw N random assistant sentences plus every regex hit (a seeded draw); "
        "write them BLIND (id, place, text) to stdout and this side's labels to --key",
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
    parser.add_argument(
        "--since-last",
        metavar="REGEX",
        help="start after the last tool_use block matching REGEX (W2161)",
    )
    parser.add_argument(
        "--nth",
        type=int,
        help="--since-last: count back this many matches (1 is the last, 2 the one before); "
        "the probe's own record matches its regex, so a tick-open hook asks for 2 (W2176)",
    )
    parser.add_argument("--repo", help="--resolve: keep only the rows of this repository")
    parser.add_argument(
        "--turns",
        help="--resolve: the transcript the rows' lines point into; an announce row whose "
        "assistant turn goes on to make a tool call is discharged (layer turn), not debt",
    )
    parser.add_argument(
        "--root", metavar="DIR", help="--commitments-tree: where the repositories live (~/github)"
    )
    parser.add_argument("--seed", type=int, default=0, help="--sample: the draw's seed")
    parser.add_argument("--key", metavar="PATH", help="--sample: where this side's labels go")
    parser.add_argument(
        "--out", metavar="PATH", help="--sample: write the blind rows here, not to stdout"
    )
    parser.add_argument(
        "--queue",
        metavar="PATH",
        help="--commitments: resolve each statement against this paths-forward queue and "
        "write the ledger document (as_of and rows with state, layer, resolved_by)",
    )
    parser.add_argument(
        "--git-log",
        metavar="PATH",
        help="--intents: a file holding git log as %%H%%x1f%%cd%%x1f%%B%%x1e under TZ=UTC",
    )
    parser.add_argument(
        "--git-repo",
        metavar="PATH",
        help="--intents: read the landed trailers from this repository's git log "
        "(--git-log wins when both are given)",
    )
    parser.add_argument(
        "--bound", metavar="STAMP", help="--intents: judge a miss up to this UTC stamp (now)"
    )
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


def _turn(turn: Turn) -> dict[str, object]:
    """Spell a turn as a JSON object.

    Returns:
        its line, time, model, cache read and creation, plain input, gap, waker and whether
        it was cold.

    """
    return {
        "line": turn.line,
        "at": turn.at,
        "model": turn.model,
        "cache_read": turn.cache_read,
        "cache_creation": turn.cache_creation,
        "input_tokens": turn.input_tokens,
        "gap_s": turn.gap_s,
        "woke": turn.woke,
        "cold": turn.cold,
    }


def _cache_turns(path: Path, out: TextIO) -> None:
    """Write each API call of one transcript, then how many there were and how many cold."""
    found = turns(read_path(path))
    out.writelines(_line(_turn(turn)) for turn in found)
    out.write(f"# {len(found)} turn(s), {sum(t.cold for t in found)} cold\n")


def _cards_of(queue: Path) -> list[dict[str, object]]:
    # The waypoint cards of a paths-forward queue file; a card that is not an object is skipped.
    doc: object = json.loads(queue.read_text(encoding="utf-8"))
    listed = cast("dict[str, object]", doc).get("waypoints") if isinstance(doc, dict) else None
    items = cast("list[object]", listed) if isinstance(listed, list) else []
    return [cast("dict[str, object]", item) for item in items if isinstance(item, dict)]


def _resolve(
    rows_file: Path, queue: str | None, repo: str | None, out: TextIO, turns_file: str | None = None
) -> int:
    """Resolve the rows of another extractor against a queue and write the ledger document.

    Returns:
        0 after the document and a tally line (counted layers, then the uncertain count); 2
        without --queue or --repo; 1 when a line of the file is not a well-typed row.

    """
    if queue is None or repo is None:
        sys.stderr.write("mikemol-transcriptstruct: --resolve needs --queue and --repo\n")
        return _USAGE
    incoming, why = commitrows.read(rows_file.read_text(encoding="utf-8").splitlines(), repo)
    if why:
        sys.stderr.write(f"mikemol-transcriptstruct: {why}\n")
        return _REFUSED
    announces = {r.commitment.line for r in incoming if r.kind == commitrows.ANNOUNCE}
    done = (
        turnlayer.discharged(read_path(Path(turns_file)), announces)
        if turns_file is not None
        else set[int]()
    )
    rows = commitrows.resolve(incoming, _cards_of(Path(queue)), done)
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    out.write(_line(commitledger.document(stamp, rows)))
    tally = commitledger.counted(rows)
    said = f"{sum(tally.values())} counted: {tally}, {commitledger.uncertain_count(rows)} uncertain"
    out.write(f"# {said}\n")
    return 0


def _ledger(found: list[Commitment], queue: Path, out: TextIO) -> None:
    """Write the commitments resolved against a queue as one ledger document, then a tally."""
    rows = commitledger.resolve(found, _cards_of(queue))
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    out.write(_line(commitledger.document(stamp, rows)))
    tally = commitledger.counted(rows)
    out.write(f"# {sum(tally.values())} counted: {tally}\n")


def _commitments(
    path: Path, out: TextIO, queue: str | None = None, window: Window | None = None
) -> None:
    """Write each commitment the assistant records of one transcript make, then the count.

    The session is the transcript's file name and the repository the last word of its project
    directory (`-home-mikemol-github-mtools` is `mtools`), a reading and not a declaration.
    `window` keeps only commitments whose line it admits (W1947: --since was ignored).
    """
    repo = path.resolve().parent.name.rsplit("-", 1)[-1]
    found = extract_commitments(read_path(path), path.stem, repo)
    if window is not None:
        found = [row for row in found if window.admits(row.line)]
    if queue is not None:
        _ledger(found, Path(queue), out)
        return
    for row in found:
        body: dict[str, object] = {
            "line": row.line,
            "uuid": row.uuid,
            "at": row.at,
            "session": row.session,
            "repo": row.repo,
            "family": row.family,
            "text": row.text,
            "names": list(row.names),
        }
        out.write(_line(body))
    out.write(f"# {len(found)} commitment(s)\n")


def _sample(path: Path, opts: dict[str, object], out: TextIO) -> None:
    """Write a blind sample of assistant sentences to `out` and the labels to `--key`.

    Raises:
        SystemExit: with the usage code when `--key` is not given, since the labels would
            otherwise have nowhere to go but beside the blind rows.

    """
    keyed = _text(opts, "key")
    if keyed is None:
        sys.stderr.write("mikemol-transcriptstruct: --sample needs --key PATH\n")
        raise SystemExit(_USAGE)
    chosen = sample.draw(
        sample.sentences(read_path(path)), _number(opts, "sample") or 0, _number(opts, "seed") or 0
    )
    blind = "".join(_line(row) for row in sample.blind(chosen))
    blind_to = _text(opts, "out")
    if blind_to is None:
        out.write(blind)
    else:
        Path(blind_to).write_text(blind, encoding="utf-8")
    Path(keyed).write_text("".join(_line(row) for row in sample.key(chosen)), encoding="utf-8")
    where = "" if blind_to is None else f"blind rows in {blind_to}; "
    out.write(f"# {len(chosen)} sentence(s); {where}labels in {keyed}\n")


def _commitments_tree(path: Path, opts: dict[str, object], out: TextIO) -> None:
    """Write the fleet's commitments as one exported document, and say what was not read."""
    root = Path(_text(opts, "root") or Path.home() / "github")
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    document, unread = commitexport.export(path, root, stamp)
    target = _text(opts, "out")
    if target is None:
        out.write(_line(document))
    else:
        commitexport.write_whole(Path(target), document)
    out.write(f"# {commitexport.summary(document, unread)}\n")
    for name in unread:
        sys.stderr.write(f"mikemol-transcriptstruct: unread {name}\n")


def _auth_failed(path: Path, out: TextIO) -> None:
    """Write the failed-authentication summary of one transcript as one JSON line."""
    found = authfail.summarize(read_path(path), path.resolve().parent.name)
    body = {
        "session": found.session,
        "project": found.project,
        "failed": found.failed,
        "tail_run": found.tail_run,
        "newest": found.newest,
    }
    out.write(json.dumps(body) + "\n")


def _turn_start(path: Path, out: TextIO) -> None:
    """Write where the latest turn began and its Stop blocks as one JSON line (null for none)."""
    found = turn_start(read_path(path))
    body: dict[str, object] | None = None
    if found is not None:
        body = {"line": found.line, "at": found.at, "blocks": found.blocks}
    out.write(json.dumps(body) + "\n")


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


def _intents(path: Path, opts: dict[str, object], out: TextIO) -> None:
    """Write what each statement of intent came to, then the count and how many diverged (W2101).

    ⚑ THE SAME ROWS AS `--commitments`, RESOLVED BY WHAT LANDED (`intents.resolve`): `--queue` names
    the queue document (the cards' status and last-worked stamp), `--git-log` a file holding
    `git log` in the `%H%x1f%cd%x1f%B%x1e` shape under `TZ=UTC` (the landed trailers), `--bound` the
    stamp up to which a miss is judged (now, by default). With no queue or no log the cards or the
    trailers are empty, so every row reads UNCHECKED or MISSED by what was given, never by a guess.
    """
    repo = path.resolve().parent.name.rsplit("-", 1)[-1]
    rows = extract_commitments(read_path(path), path.stem, repo)
    queue, log = _text(opts, "queue"), _text(opts, "git_log")
    repo_path = _text(opts, "git_repo")
    cards = CARDS_OF(Path(queue).read_text(encoding="utf-8")) if queue else {}
    repo_log = read_git_log(Path(repo_path)) if repo_path and not log else None
    landed = TRAILERS_OF(Path(log).read_text(encoding="utf-8")) if log else []
    landed = TRAILERS_OF(repo_log) if repo_log else landed
    bound = _text(opts, "bound") or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    resolved = RESOLVE_INTENTS(rows, cards, landed, bound)
    out.writelines(
        _line({"line": r.line, "state": r.state, "cards": list(r.cards), "text": r.text})
        for r in resolved
    )
    out.write(f"# {len(resolved)} intent(s), {len(DIVERGED_INTENTS(resolved))} diverged\n")


def _listing(opts: dict[str, object], path: Path, scheduled: Sequence[str], out: TextIO) -> bool:
    """Run the two modes that list a whole transcript, when one is asked for.

    Returns:
        True when `--cache-turns` or `--harvest` ran.

    """
    if opts.get("cache_turns") is True:
        _cache_turns(path, out)
    elif opts.get("commitments_tree") is True:
        _commitments_tree(path, opts, out)
    elif opts.get("auth_failed") is True:
        _auth_failed(path, out)
    elif opts.get("turn_start") is True:
        _turn_start(path, out)
    elif opts.get("intents") is True:
        _intents(path, opts, out)
    elif opts.get("commitments") is True:
        _commitments(
            path, out, _text(opts, "queue"), Window(_number(opts, "since"), _number(opts, "until"))
        )
    elif opts.get("harvest") is True:
        _harvest(path, scheduled, out)
    elif _number(opts, "sample") is not None:
        _sample(path, opts, out)
    elif opts.get("audit_memory") is True:
        out.writelines(f"{row.text()}\n" for row in audit(path))
    else:
        return False
    return True


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
    if opts.get("resolve") is True:
        return _resolve(path, _text(opts, "queue"), _text(opts, "repo"), out, _text(opts, "turns"))
    return 0 if _listing(opts, path, scheduled, out) else None


def _window_of(opts: dict[str, object], path: Path) -> Window:
    """Build the line window of a query, `--since-last REGEX` moving its start (W2161).

    ⚑ A FIXED LINE CANNOT BOUND A SEARCH TO "SINCE THE LAST TICK CLOSE" (github:R141):
    `--since-last` starts the search on the line after the LAST tool_use block that matches the
    regex, inside any `--since` and `--until` given. When nothing matches, the window is the one
    `--since` and `--until` name, so a transcript with no close yet is searched whole.

    ⚑ THE PROBE'S OWN RECORD MATCHES ITS REGEX (W2176, github-42): the command that carries
    `--since-last 'tick-open'` is itself a tool_use containing 'tick-open', so it is the last
    match and nothing after it is searched. `--nth N` counts back N matches (1 is the last, the
    old behaviour; 2 skips the invoker and starts after the previous tick-open). With fewer than N
    matches the window is the one `--since` and `--until` name.

    Returns:
        the window.

    """
    since, until = _number(opts, "since"), _number(opts, "until")
    pattern = _text(opts, "since_last")
    nth = _number(opts, "nth") or 1
    if pattern is not None:
        marks = grep_blocks(
            read_path(path), pattern, block_kinds=["tool_use"], window=Window(since, until)
        )
        lines = sorted(hit.line for hit in marks.hits)
        if len(lines) >= nth:
            since = lines[-nth] + 1
    return Window(since, until)


def main(argv: Sequence[str] | None = None, out: TextIO | None = None) -> int:
    """Run one query over one transcript.

    Returns:
        0 on success. argparse exits 2 on an unknown flag or a bad value.

    """
    opts: dict[str, object] = vars(_parser().parse_args(sys.argv[1:] if argv is None else argv))
    sink = out or sys.stdout
    path = Path(str(opts["transcript"]))
    window = _window_of(opts, path)
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
