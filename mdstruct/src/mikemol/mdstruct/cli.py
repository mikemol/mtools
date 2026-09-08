# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The `mdstruct` command — one mode per structural question.

    mdstruct spans FILE.md                  # every section, with its line bounds
    mdstruct grep PATTERN FILE.md [-i] [-E] # where text is, AS A SPAN
    mdstruct tables FILE.md                 # every table: position, size, header
    mdstruct rows FILE.md [--where TEXT]    # the cells, optionally filtered
                  [--table N]               # ...scoped to one table
                  [--col N --starts TEXT]   # ...or anchored to one column's PREFIX
    mdstruct classify FILE.md [--col N]     # rows grouped by the doc's OWN declared states
                  [--table N]               # ...scoped to one table
    mdstruct labels FILE.md                 # every worklist label the document mentions
    mdstruct roundtrip FILE.md              # what ONE normalization pass changes
    mdstruct fixpoint FILE.md               # does normalization CONVERGE, and in how many
    mdstruct lint FILE.md [--width N]       # the shape rules, measured on this document
    mdstruct narrowest FILE.md              # the narrowest width this document satisfies

⚑⚑ THE CONSOLE SCRIPT IS THE ADOPTION PATH THAT REPLACES A SYMLINK. Peers previously adopted this
tool by symlinking one file out of another repo's working tree — which broke silently the moment
the tool derived its own root with a call that does not resolve symlinks, so the root became the
CONSUMER's repo. An installed entry point cannot have that defect: a package knows where it
lives, and there is no path to get wrong.

⚑ EVERY MODE PRINTS ITS DENOMINATOR. A bare list cannot distinguish *no matches* from *nothing
read*, and an empty result with no count reads as a tool that failed rather than a document that
does not contain the thing.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from mikemol.mdstruct import grep, labels, lint, roundtrip, spans, tables, verify

# ⚑ THE SIGNATURE EVERY MODE PRESENTS, even where it uses one of the three arguments. Dispatching
# on arity instead would put the branching back, one layer down and less visible.
#
# ⚑ `Callable` IS A RUNTIME IMPORT, NOT A TYPE-CHECKING ONE: a type ALIAS is evaluated when the
# module loads, so parking it behind `TYPE_CHECKING` raises `NameError` at import.
_Mode = Callable[[str, Path, list[str]], int]

# `<mode> <file>` at minimum; `grep` takes a pattern before the file.
_MIN_ARGS = 2

# ⚑ THE ONE MODE TAKING A PATTERN BEFORE ITS PATH, named so the argument-shape special case in
# `main` cites this rather than spelling the string a second time.
_PATTERN_MODE = "grep"

# How many cells of a row to render before truncating, so one wide row cannot flood a terminal.
_CELL_WIDTH = 40


def _flag(argv: list[str], name: str) -> str | None:
    """Return a `--name value` or `--name=value` argument, or None.

    ⚑ BOTH SPELLINGS BIND, because a reader arriving from another tool types the spaced form and
    accepting one only would let the other ride through and be silently discarded.

    Returns:
        a `--name value` or `--name=value` argument, or None.

    """
    for i, arg in enumerate(argv):
        if arg == name and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith(name + "="):
            return arg.split("=", 1)[1]
    return None


def _spans(path: Path) -> int:
    """Print every section span, indented by level."""
    found = spans.spans(path)
    if not found:
        sys.stdout.write(f"mdstruct: {path} declares no headers\n")
        return 0
    for span in found:
        indent = "  " * span.level
        sys.stdout.write(f"  L{span.start:>4}-{span.end - 1:<4} "
                         f"{indent}{'#' * span.level} {span.text}\n")
    sys.stdout.write(f"  {len(found)} section(s) in {path}\n")
    return 0


def _grep(pattern: str, path: Path, argv: list[str]) -> int:
    """Print the structural span of every match."""
    is_regex = "-E" in argv
    hits = grep.search(path, pattern, regex=is_regex, ignore_case="-i" in argv)
    if not hits:
        # ⚑⚑ A READER'S NEGATIVE MUST CARRY ITS DENOMINATOR AND ITS SCOPE (rosettapkg,
        # 2026-09-06). `-E` detection alone is half a repair: it catches the mode misfire and
        # leaves the next silent zero silent. A sibling reader in this ecosystem prints
        # "no line carries X in 2183 file(s) of dpkg 1.23.7ubuntu1 — UNAVAILABLE at this version,
        # NOT a claim that it does not exist upstream", and a wrapper can act on that where it
        # cannot act on a bare "no match". This is census-kit §5's positive-control rule applied
        # to the INSTRUMENT rather than to the surveyor — which is strictly stronger, because it
        # holds when the surveyor forgets.
        mode = "REGEX" if is_regex else "LITERAL"
        n_lines = len(path.read_text(encoding="utf-8").split("\n"))
        sys.stdout.write(f"mdstruct: no line in {path} matches {pattern!r}\n")
        sys.stdout.write(f"    searched {n_lines} line(s) in {mode.upper()} mode. This is a fact\n"
                         f"    about THIS FILE at THIS PATH — not a claim about any other file.\n")
        # ⚑⚑ A ZERO THAT CANNOT SAY WHY IS THE WORST RESULT A READER CAN RETURN, and this one had
        # no natural discoverer: the struct-tools hook routes every `.md` query here, so the
        # routing that makes this tool authoritative also removes the reader who would disagree.
        # Measured (linux-sources, 2026-09-06): `grep '7\.0\.0-'` reported no match on a file
        # containing `7.0.0-29.29` twice, because LITERAL mode escapes the backslash again.
        tell = "" if is_regex else grep.regex_tell(pattern)
        if tell:
            sys.stdout.write(
                f"  ⚑ THE PATTERN CONTAINS {tell!r} AND THIS WAS A **LITERAL** SEARCH, so that\n"
                f"    was matched as text rather than as a regex. This zero may be an artefact\n"
                f"    of the mode rather than a fact about the file.\n"
                f"  re-run with -E for a regex, or drop the escapes for a literal search:\n"
                f"      mdstruct grep -E {pattern!r} {path}\n")
        return 1
    for hit in hits:
        sys.stdout.write(f"  {hit.container}\n")
        sys.stdout.write(f"    L{hit.start}-{hit.end}  :  L{hit.line_no}  {hit.line}\n")
    sys.stdout.write(f"  {len(hits)} match(es) in {path}\n")
    # ⚑ THE LIMIT IS PRINTED WITH THE RESULT, not left in a docstring. A reader who expected a
    # table coordinate must see why they got a section one at the moment they read the output.
    sys.stdout.write("    containers are SECTIONS. pandoc carries no source positions for\n"
                     "    tables, so a match inside one reports its enclosing section.\n")
    return 0


def _tables(path: Path) -> int:
    """Print every table's position, size and header."""
    found = tables.tables(path)
    if not found:
        sys.stdout.write(f"mdstruct: {path} holds no tables\n")
        return 0
    for table in found:
        sys.stdout.write(f"  table {table.position}  {table.rows} row(s) x "
                         f"{table.cols} col(s)  {' | '.join(table.header)}\n")
    sys.stdout.write(f"  {len(found)} table(s) in {path}\n")
    return 0


def _rows(path: Path, argv: list[str]) -> int:
    """Print table rows, filtered by a row-wide substring or a column-anchored prefix.

    ⚑⚑ `--starts` ANSWERS A DIFFERENT QUESTION FROM `--where` AND THE DIFFERENCE IS
    LOAD-BEARING: `--where` asks whether any cell MENTIONS a term, `--starts` asks whether one
    column DECLARES it. A document that explains its own predicate mentions the term while
    declaring nothing — measured on a peer's revision log, where a row announcing a repair to a
    freeze mechanism matched a poll for the freeze itself.
    """
    where = _flag(argv, "--where")
    starts = _flag(argv, "--starts")
    col_raw = _flag(argv, "--col")
    # ⚑ AN UNPARSEABLE --col REFUSES RATHER THAN DEFAULTING TO 0. Silently reading column 0 for
    # `--col two` would answer a question nobody asked and report it as a clean result.
    if col_raw is not None and not col_raw.isdigit():
        sys.stderr.write(f"mdstruct: --col wants a column number, got {col_raw!r}\n")
        return 2
    if col_raw is not None and starts is None:
        sys.stderr.write("mdstruct: --col names a column; --starts says what it must begin with\n")
        return 2
    col = int(col_raw) if col_raw is not None else None
    # ⚑⚑⚑ `--table` WAS ACCEPTED AND IGNORED HERE, AND A PEER MEASURED IT. `rows FILE --table 99`
    # on a five-table document returned all 33 rows — byte-identical to a valid index, and to no
    # index at all. `classify` parses this flag; `rows` never looked for it, so the flag works in
    # whichever mode a reader happens to try second.
    # ⚑⚑ THE COST LANDED IN A COMMIT MESSAGE: *"measured with `rows --table 6`"* named an
    # operation that did not occur. The conclusion held because the wanted table was visible in
    # the unfiltered output; the REPRODUCTION STEP did not reproduce, which is how a defect report
    # becomes un-checkable one revision later.
    pos_raw = _flag(argv, "--table")
    if pos_raw is not None and not pos_raw.isdigit():
        sys.stderr.write(f"mdstruct: --table wants a table number, got {pos_raw!r}\n")
        return 2
    position = int(pos_raw) if pos_raw is not None else None
    # ⚑ AN OUT-OF-RANGE INDEX REFUSES RATHER THAN RETURNING EMPTY. An empty result is
    # indistinguishable from a table that genuinely holds no rows — absence versus unavailable, in
    # the flag a reader reaches for when narrowing.
    if position is not None:
        count = len(tables.tables(path))
        if position >= count:
            sys.stderr.write(
                f"mdstruct: --table {position} but {path} holds {count} table(s), "
                f"numbered 0-{count - 1}\n" if count else
                f"mdstruct: --table {position} but {path} holds no tables\n")
            return 2
    found = tables.table_rows(path, where=where, col=col, starts=starts, position=position)
    if not found:
        asked = starts if starts is not None else where
        how = f"column {col or 0} beginning with" if starts is not None else "matching"
        sys.stdout.write(f"mdstruct: no row in {path} with {how} {asked!r}\n")
        return 1
    for row in found:
        cells = " | ".join(cell[:_CELL_WIDTH] for cell in row.cells)
        sys.stdout.write(f"  table {row.table}  {cells}\n")
    sys.stdout.write(f"  {len(found)} row(s) in {path}\n")
    return 0


def _labels(path: Path) -> int:
    """Print every worklist label the document mentions, with its lines."""
    seen: dict[str, list[int]] = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for label in labels.labels_in(line):
            seen.setdefault(label, []).append(lineno)
    if not seen:
        sys.stdout.write(f"mdstruct: {path} mentions no labels\n")
        return 0
    for label in sorted(seen):
        lines = ", ".join(str(n) for n in seen[label][:8])
        sys.stdout.write(f"  {label:<16} L{lines}\n")
    sys.stdout.write(f"  {len(seen)} label(s) in {path}\n")
    return 0


def _roundtrip(path: Path) -> int:
    """Print what one normalization pass changes.

    ⚑ NOT A PASS/FAIL. Pandoc normalizes by design, so identity is the unusual case; the SIZE
    and SHAPE of the drift is what a caller needs, which is why the sample prints with the count.
    """
    drift = roundtrip.roundtrip(path)
    if drift.identical:
        sys.stdout.write(f"  {path}: round-trips IDENTICALLY\n")
        return 0
    sys.stdout.write(f"  {path}: normalization changes {drift.changed} line(s). First "
                     f"{len(drift.sample)}:\n")
    for line in drift.sample:
        sys.stdout.write(f"    {line[:150]}\n")
    return 0


def _fixpoint(path: Path) -> int:
    """Print whether normalization converges, and the per-round deltas.

    ⚑ THE DELTAS ARE PRINTED, NOT JUST THE VERDICT. A decreasing sequence is approach, a
    repeated value is a plateau, a growing one is divergence — and a bare boolean discards the
    only thing that distinguishes them. Two wrong stopping rules were adopted by reading a
    verdict without its sequence.
    """
    result = roundtrip.fixpoint(path)
    deltas = ", ".join(str(n) for n in result.deltas)
    if result.converged:
        sys.stdout.write(f"  {path}: CONVERGES in {len(result.deltas)} round(s)\n")
        sys.stdout.write(f"    deltas: [{deltas}]\n")
        return 0
    sys.stdout.write(f"  {path}: does NOT converge in {len(result.deltas)} round(s)\n")
    sys.stdout.write(f"    deltas: [{deltas}]\n")
    for line in result.sample:
        sys.stdout.write(f"    {line[:150]}\n")
    return 1


def _lint(path: Path, argv: list[str]) -> int:
    """Print the shape findings for the document body."""
    width = _flag(argv, "--width")
    rows = lint.shape(path, int(width) if width and width.isdigit() else lint.DEFAULT_WIDTH)
    if not rows:
        sys.stdout.write(f"  {path}: no shape findings\n")
        return 0
    for row in rows:
        sys.stdout.write(f"  L{row.line:<5} {row.rule}  {row.detail}\n")
    sys.stdout.write(f"  {len(rows)} finding(s) in {path}\n")
    return 1


def _narrowest(path: Path) -> int:
    """Print the narrowest width this document already satisfies.

    ⚑ THE NUMBER TO TELL A WIDTH RULE, so the rule agrees with the writer rather than being
    disabled by it.
    """
    got = lint.narrowest_width(path)
    if got is None:
        sys.stdout.write(f"  {path}: no admissible width in range — a line exceeds the "
                         f"ceiling\n")
        return 1
    sys.stdout.write(f"  {path}: narrowest admissible width is {got}\n")
    return 0


# ⚑⚑ THESE ADAPTERS ARE NAMED FUNCTIONS, NOT LAMBDAS, AND THE REASON IS A TYPE. A lambda's
# parameters carry no annotations, so each table entry would infer `Callable[[Any, Any, Any],
# int]` — a typed-LOOKING table checked against nothing. A named function takes the annotation,
# and the strict bar then verifies each adapter really is a `_Mode`.
def _spans_mode(_pattern: str, path: Path, _argv: list[str]) -> int:
    """Adapt the span listing to the uniform mode signature."""
    return _spans(path)


def _tables_mode(_pattern: str, path: Path, _argv: list[str]) -> int:
    """Adapt the table listing to the uniform mode signature."""
    return _tables(path)


def _rows_mode(_pattern: str, path: Path, argv: list[str]) -> int:
    """Adapt the row listing, which reads a `--where` filter from argv."""
    return _rows(path, argv)


def _labels_mode(_pattern: str, path: Path, _argv: list[str]) -> int:
    """Adapt the label census to the uniform mode signature."""
    return _labels(path)


def _roundtrip_mode(_pattern: str, path: Path, _argv: list[str]) -> int:
    """Adapt the one-pass drift report to the uniform mode signature."""
    return _roundtrip(path)


def _fixpoint_mode(_pattern: str, path: Path, _argv: list[str]) -> int:
    """Adapt the convergence report to the uniform mode signature."""
    return _fixpoint(path)


def _lint_mode(_pattern: str, path: Path, argv: list[str]) -> int:
    """Adapt the shape rules, which read a `--width` from argv."""
    return _lint(path, argv)


def _verify_one(path: Path) -> int:
    """Verify one document. Returns 0 when every heading reaches the section list."""
    missing = verify.missing_headings(path)
    if not missing:
        sys.stdout.write(f"  {path}: every source heading reaches the section list\n")
        return 0
    for item in missing:
        sys.stdout.write(
            f"  L{item.line:>4}  {'#' * item.level} {item.text}  — SWALLOWED, not a section\n")
    sys.stdout.write(
        f"  {len(missing)} heading(s) in {path} are unreachable. A bounded write against the "
        "PRECEDING section would land inside one of them.\n")
    return 1


def _verify_mode(_pattern: str, path: Path, argv: list[str]) -> int:
    """Assert this tool's own contract: every source heading reaches the section list.

    ⚑ A TOOL OWES A SELF-ASSERTING CONTRACT. `lint` and `roundtrip` both report green on a
    document this tool silently corrupts, so neither can stand in for this. Run it on a document
    before trusting a bounded write into that document.

    ⚑⚑⚑ IT TAKES MANY PATHS BECAUSE THE GATE PAID ONE INTERPRETER STARTUP PER FILE. The pre-commit
    hook loops over every committed markdown file and spawns a fresh `python3 -m` for each —
    MEASURED: 68 files, 1,972,369 bytes, 68 startups to check 1.9MB. ⚑ And the domain is *every
    committed markdown file*, not the ones a commit touches, so the work grows every time any party
    files a census leg: 32 files when the loop was written, 68 now. **That is not a slowdown, it is
    a domain that expands with the corpus.**

    ⚑⚑ ONLY THE INTERPRETER IS BATCHED, NOT THE DOMAIN. Narrowing to staged files would trade a
    corpus-wide invariant for a per-commit one — and the defect this mode exists for was found in a
    file NOBODY HAD STAGED, corrupted by another party's write. Same verdict over the same set,
    one startup instead of N.

    ⚑ EVERY PATH IS VERIFIED BEFORE RETURNING: the loop does not stop at the first failure, because
    a gate that reports one finding per run teaches one finding per round — the same
    information-per-refusal argument `preflight.sh` is built on.
    """
    # ⚑ `argv[2:]` STILL CONTAINS THE FIRST PATH, and slicing it naively verified that file TWICE.
    # MEASURED on the single-path arm — `verify README.md` printed the same green line twice — which
    # is why the arm exists: a duplicate PASS is invisible in a green run and would have doubled the
    # gate's first file forever. Positional args after the mode are `args[1:]`; `path` is `args[1]`.
    positional = [a for a in argv[1:] if not a.startswith("-")]
    paths = [path, *(Path(p) for p in positional[2:])]
    worst = 0
    for candidate in paths:
        if not candidate.exists():
            sys.stderr.write(f"mdstruct: no such file: {candidate}\n")
            worst = max(worst, 2)
            continue
        worst = max(worst, _verify_one(candidate))
    return worst


def _narrowest_mode(_pattern: str, path: Path, _argv: list[str]) -> int:
    """Adapt the narrowest-width report to the uniform mode signature."""
    return _narrowest(path)


def _classify(path: Path, argv: list[str]) -> int:
    """Group a table's rows by the states the document itself declares.

    ⚑⚑⚑ THE VOCABULARY COMES FROM THE DOCUMENT, WHICH IS THE WHOLE POINT. A consumer of this
    corpus had four states written by hand from the two files its author happened to be reading;
    the declared union across the corpus was twice that, and one of the states it missed is
    annotated in its own document as *reading like a zero when nobody was asked*. A published
    vocabulary is the only population that cannot go stale.

    ⚑⚑ EVERY GROUP IS PRINTED WITH ITS COUNT, INCLUDING THE RESIDUE. A classifier that reports
    only what it matched describes its own coverage as complete; the unclassified group is the
    only thing that can reveal a state the document uses and never declared — measured, one census
    does exactly that.

    Returns:
        0 when the document declares a vocabulary, 2 when it does not.

    """
    states = tables.vocabulary(path)
    if not states:
        sys.stderr.write(
            f"mdstruct: {path} declares no `state | means` table — nothing to classify against. "
            "That is a fact about the document, not about this reader.\n")
        return 2
    col_raw = _flag(argv, "--col")
    if col_raw is not None and not col_raw.isdigit():
        sys.stderr.write(f"mdstruct: --col wants a column number, got {col_raw!r}\n")
        return 2
    pos_raw = _flag(argv, "--table")
    if pos_raw is not None and not pos_raw.isdigit():
        sys.stderr.write(f"mdstruct: --table wants a table number, got {pos_raw!r}\n")
        return 2
    groups = tables.classify(
        path,
        states,
        col=int(col_raw) if col_raw is not None else 1,
        position=int(pos_raw) if pos_raw is not None else None,
    )
    sys.stdout.write(f"  {len(states)} declared state(s) in {path}\n")
    total = 0
    for state, rows in groups.items():
        if not rows:
            continue
        total += len(rows)
        sys.stdout.write(f"  {len(rows):>4}  {state or '⚑ UNCLASSIFIED — no declared state'}\n")
    sys.stdout.write(f"  {total} row(s) classified in {path}\n")
    return 0


def _classify_mode(_pattern: str, path: Path, argv: list[str]) -> int:
    """Adapt the classifier to the uniform mode signature.

    Returns:
        the classifier's status.

    """
    return _classify(path, argv)


# ⚑⚑⚑ THE MODE ROSTER IS DATA, NOT A BRANCH CHAIN. As nine `if mode == …` arms `main` sat over
# three complexity bars at once — and, the part that actually cost something, **nothing could
# answer "which modes exist" without walking a function body.** The usage text and the dispatch
# were then two lists free to disagree, with no mechanism able to notice. A dict is enumerable:
# the unknown-mode message below derives its list FROM this table, so the two cannot drift.
_MODES: dict[str, _Mode] = {
    "spans": _spans_mode,
    _PATTERN_MODE: _grep,
    "tables": _tables_mode,
    "rows": _rows_mode,
    "classify": _classify_mode,
    "labels": _labels_mode,
    "roundtrip": _roundtrip_mode,
    "fixpoint": _fixpoint_mode,
    "lint": _lint_mode,
    "verify": _verify_mode,
    "narrowest": _narrowest_mode,
}


def main() -> int:
    """Dispatch one mode."""
    argv = sys.argv
    args = [a for a in argv[1:] if not a.startswith("-")]
    if len(args) < _MIN_ARGS:
        sys.stderr.write(__doc__ or "usage: mdstruct <mode> ...\n")
        return 2

    mode = args[0]
    run = _MODES.get(mode)
    if run is None:
        sys.stderr.write(f"mdstruct: unknown mode {mode!r} — "
                         f"known modes are {', '.join(sorted(_MODES))}\n")
        return 2

    if mode == _PATTERN_MODE:
        if len(args) < _MIN_ARGS + 1:
            sys.stderr.write("usage: mdstruct grep PATTERN FILE.md [-i] [-E]\n")
            return 2
        pattern, path = args[1], Path(args[2])
    else:
        pattern, path = "", Path(args[1])

    if not path.exists():
        sys.stderr.write(f"mdstruct: no such file: {path}\n")
        return 2

    return run(pattern, path, argv)


if __name__ == "__main__":
    sys.exit(main())
