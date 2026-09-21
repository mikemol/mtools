# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The `mdstruct` command — one mode per structural question.

    mdstruct spans FILE.md                  # every section, with its line bounds
    mdstruct budget FILE.md                 # every section's SIZE: lines, bytes, headings below
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
    mdstruct verify FILE.md                 # does EVERY source heading reach the section list
    mdstruct narrowest FILE.md              # the narrowest width this document satisfies

  the WRITE modes — heading before file, matching `grep`, and a DRY RUN unless `--apply`:

    mdstruct replace-section HEADING FILE.md --body-file B.md [--exact] [--apply]
    mdstruct append-section HEADING FILE.md --body-file B.md [--exact] [--apply]
                  # `--body-file -` reads stdin. A body is a FILE, never an argument:
                  # a multi-line body on the command line is the `>>` this tool replaces.

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

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

from mikemol.mdstruct import (
    budget,
    grep,
    labels,
    lint,
    roundtrip,
    sections,
    spans,
    tables,
    verify,
)

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

# ⚑⚑⚑ EVERY MODE TAKING AN OPERAND BEFORE ITS PATH, which was ONE mode and is now three. The write
# modes take a HEADING there, on an operator ruling (2026-09-12): needle before file, matching
# `grep` and the real tool it is named for, so the tool has ONE rule for every two-positional mode
# rather than a reader-versus-writer split.
# ⚑⚑ A SET RATHER THAN A SECOND CONSTANT. The arity special case in `main` tested `== _PATTERN_MODE`
# and would have silently taken the one-positional branch for a write — putting the FILE in the
# heading slot, which is the silent-wrong-target class this tool's whole refusal layer exists to
# prevent, arriving through the dispatcher instead of through the finder.
_OPERAND_FIRST = frozenset({_PATTERN_MODE, "replace-section", "append-section"})

# How many cells of a row to render before truncating, so one wide row cannot flood a terminal.
_CELL_WIDTH = 40

# ⚑⚑⚑ WHICH MODIFIERS EACH MODE OWNS — the declaration an unknown-flag refusal is derived from.
# A modifier is owned by ONE mode rather than being globally true: `--width` means nothing to
# `spans`, and accepting it there would answer a question nobody asked while reporting success.
# ⚑⚑ THE SHAPE IS SUBSTRATE'S `climode.opts` FIELD, adopted as a CONCEPT rather than imported. That
# module declares contracts for a gate substrate runs; mtools has no such gate yet, so importing
# the dataclass would buy a declaration with no enforcement. The enforcement is what matters here,
# so the declaration is local and the refusal below is the thing that reads it.
_MODE_OPTS: dict[str, frozenset[str]] = {
    "grep": frozenset({"-i", "-E"}),
    "rows": frozenset({"--where", "--starts", "--col", "--table"}),
    "classify": frozenset({"--col", "--table"}),
    "lint": frozenset({"--width"}),
    "replace-section": frozenset({"--body-file", "--exact", "--apply", "--dry-run"}),
    "append-section": frozenset({"--body-file", "--exact", "--apply", "--dry-run"}),
}

# ⚑ EVERY MODE ACCEPTS THESE, so a reader need not learn a per-mode exception for the universal
# two. Kept separate from `_MODE_OPTS` so the per-mode sets stay a statement about that mode.
_GLOBAL_OPTS = frozenset({"-h", "--help"})

# ⚑⚑⚑ ARITY, WHICH `_MODE_OPTS` NEVER DECLARED. The hand-rolled parser reads it from the CALL
# SITE: `_flag(argv, "--width")` makes `--width` value-taking, `"--exact" in argv` makes `--exact`
# a switch. That works and it is invisible — a flag's arity lives wherever its mode happens to
# read it. `argparse` needs it stated, so it is stated here ONCE, and `tests/test_cli_flags.py`
# derives the same table from the call sites by walking this module's AST and refuses
# any disagreement: a flag read by `_flag` that is listed here as a switch, a flag read by `in`
# that is listed as value-taking, or a flag declared in `_MODE_OPTS` and absent here. A restated
# population is the defect this repository measures most; this one is gated in both directions.
# ⚑ True = takes a value (`--name value` or `--name=value`); False = presence is the value.
_OPT_ARITY: dict[str, bool] = {
    "-i": False,
    "-E": False,
    "--where": True,
    "--starts": True,
    "--col": True,
    "--table": True,
    "--width": True,
    "--body-file": True,
    "--exact": False,
    "--apply": False,
    "--dry-run": False,
    "-h": False,
    "--help": False,
}


def _locate_mode(argv: list[str]) -> int | None:
    """Return the index in `argv[1:]` of the mode word, or None when there is none.

    ⚑⚑⚑ THE MODE IS FOUND BEFORE ANY PARSER RUNS, because the parser is PER-MODE: which flags
    exist depends on which word comes first. The retired `_split_args` found it as the first
    operand; this finds it the same way — the first token that is not option-shaped — so
    `mdstruct -i grep …` still dispatches `grep`, exactly as before the argparse switch.

    Returns:
        the index into `argv[1:]`, or None.

    """
    return next((i for i, tok in enumerate(argv[1:]) if not tok.startswith("-")), None)


def _mode_operands(argv: list[str]) -> list[str]:
    """Return the operands `main` parsed for this invocation, without the mode word.

    ⚑ FOR A MODE THAT TAKES A PATH POPULATION (`verify`), which needs every operand and not just
    the first two `main` hands it. It re-runs the SAME parse `main` ran, from the same tables, so
    there is one split and not two spellings of one. A refused parse cannot reach here — `main`
    has already refused it — so an empty list means "no operands", never "parse failed".

    Returns:
        every operand after the mode, in order, with values of value-taking flags consumed.

    """
    at = _locate_mode(argv)
    if at is None:
        return []
    rest = argv[1:]
    operands, refusal = _parse_mode_args(rest[at], rest[:at] + rest[at + 1:])
    return [] if refusal is not None else operands


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


def argparse_parser(mode: str) -> argparse.ArgumentParser:
    """Build the `argparse` parser for one mode from `_MODE_OPTS`, `_GLOBAL_OPTS` and `_OPT_ARITY`.

    ⚑⚑⚑ OPERATOR RULING 2026-09-20 (W9): migrate to argparse, PARITY FIRST. This parser was built
    beside the hand-rolled `_split_args`/`_unknown_opts` with no caller, and the parity arm in
    `tests/test_cli_flags.py` handed both the same argv on fourteen shapes and refused any
    disagreement about what is
    accepted, what is refused, and which token lands in the file slot. Writing that arm found a
    live defect in the OLD parser (a value flag's value leaked into the operands). `main()` then
    switched here and the old two were deleted; the parity arm remains, now holding `main()`
    against this parser directly. Public because it is what `main()` uses and the arm reaches it as
    a caller would.

    ⚑ MODES STAY POSITIONAL WORDS (`mdstruct spans FILE`), not subparsers: the operator ruled on
    the surface, and `add_subparsers` would change the usage text and the unknown-mode refusal.
    The mode is located by `main()` before this parser sees the rest.

    ⚑ `allow_abbrev=False`, because the old parser refused `--wid` and argparse would otherwise
    accept it as `--width` — an acceptance the parity arm would (correctly) call a divergence.

    Args:
        mode: the dispatched mode name; decides which of `_MODE_OPTS` applies.

    Returns:
        a parser accepting this mode's declared options with their declared arity, refusing
        everything else, and collecting operands (after an optional `--`) as `operands`.

    """
    # ⚑ `exit_on_error=False` so a parse failure is an exception `main()` renders in this tool's
    # own voice, never a `SystemExit` from inside a library call.
    parser = argparse.ArgumentParser(
        prog=f"mdstruct {mode}", add_help=False, allow_abbrev=False, exit_on_error=False,
    )
    for opt in sorted(_MODE_OPTS.get(mode, frozenset()) | _GLOBAL_OPTS):
        if _OPT_ARITY[opt]:
            parser.add_argument(opt, dest=opt.lstrip("-").replace("-", "_"))
        else:
            parser.add_argument(opt, dest=opt.lstrip("-").replace("-", "_"), action="store_true")
    parser.add_argument("operands", nargs="*")
    return parser


def _spans(path: Path) -> int:
    """Print every section span, indented by level.

    Returns:
        Always 0. ⚑ THE OUTPUT IS THE ANSWER, NOT THE STATUS: an empty result is a fact
        about the document, so a caller branching on this code learns whether the reader
        RAN, never what it found. The report on stdout is what carries the finding.

    """
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


def _budget(path: Path) -> int:
    """Print every section's size over the same population `spans` prints.

    ⚑ ONE ROW PER SECTION, THEN THE DENOMINATOR: total sections AND total bytes, because a reader
    deciding what fits in a context needs the whole as well as the parts, and a column of sizes
    with no total is a list the reader must sum by hand.

    Returns:
        Always 0 — the report is the answer, as for `spans`.

    """
    found = budget.budget(path)
    if not found:
        sys.stdout.write(f"mdstruct: {path} declares no headers\n")
        return 0
    for row in found:
        indent = "  " * row.span.level
        sys.stdout.write(
            f"  L{row.span.start:>4}-{row.span.end - 1:<4} {row.lines:>5} lines "
            f"{row.size:>7} bytes  {row.below:>3} below  depth {row.depth}  "
            f"{indent}{'#' * row.span.level} {row.span.text}\n",
        )
    # ⚑ THE WHOLE IS THE FILE, NOT A SUM OF ROWS: nested sections overlap their parents, so
    # summing the column double-counts, and a sum over one level misses any preamble before
    # the first heading. The file's own byte count is the denominator a reader loads against.
    total = len(path.read_bytes())
    sys.stdout.write(f"  {len(found)} section(s), {total} bytes in {path}\n")
    return 0


def _grep(pattern: str, path: Path, argv: list[str]) -> int:
    """Print the structural span of every match.

    Returns:
        0 when the pattern matches and 1 when it does not — ⚑ THE ONE READER IN THIS FILE WHOSE
        EMPTY RESULT IS A NONZERO CODE, so `grep`'s exit convention carries over and a caller can
        branch on it the way they would on the real thing.
        ⚑⚑ I WROTE *ALWAYS 0* HERE FIRST, FROM THE `return 0` AT THE END OF THE FUNCTION, without
        reading the early return in the no-match branch. A docstring asserting what the code
        beside it destroys is this repository's recurring defect, arriving in the very paydown
        that exists to make return values legible.
        ⚑ AND THE ZERO IS STILL NOT THE WHOLE ANSWER: the no-match branch prints its DENOMINATOR
        and its MODE, because a bare *no match* cannot distinguish a document that lacks the term
        from a LITERAL search that escaped a regex the caller meant.

    """
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
    """Print every table's position, size and header.

    Returns:
        Always 0. ⚑ THE OUTPUT IS THE ANSWER, NOT THE STATUS: an empty result is a fact
        about the document, so a caller branching on this code learns whether the reader
        RAN, never what it found. The report on stdout is what carries the finding.

    """
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

    Returns:
        0 when rows match, 1 when the query is well-formed and matches nothing, 2 when the QUERY
        ITSELF is malformed — a non-numeric `--col` or `--table`, a `--col` with no `--starts`, an
        index past the last table.
        ⚑⚑⚑ THREE VALUES, AND SEPARATING 1 FROM 2 IS THE WHOLE POINT: *this document has no such
        row* and *I could not understand what you asked* are different facts, and collapsing them
        lets a typo'd flag report as a clean empty result. The body argues it at each site — an
        out-of-range `--table` refuses rather than returning empty, because an empty result is
        indistinguishable from a table that genuinely holds no rows.
        ⚑ I FIRST WROTE *ALWAYS 0* HERE, and an AST probe over this file's `return` statements
        caught it along with the same error in `_grep`. Reading a function's last line is not
        reading its contract.

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
    """Print every worklist label the document mentions, with its lines.

    Returns:
        Always 0. ⚑ THE OUTPUT IS THE ANSWER, NOT THE STATUS: an empty result is a fact
        about the document, so a caller branching on this code learns whether the reader
        RAN, never what it found. The report on stdout is what carries the finding.

    """
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

    Returns:
        Always 0, and the paragraph above is why: drift is EXPECTED here, so a nonzero code would
        report the normal case as a failure. ⚑ The drift's size and sample are on stdout because
        that is the only place a caller can read what actually changed.

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

    Returns:
        0 when normalization converges and 1 when it does not — a real verdict, unlike the
        readers in this file. ⚑ AND THE CODE IS STILL THE SMALLER HALF OF THE ANSWER: it says
        THAT convergence failed, while the printed deltas say whether the sequence was
        approaching, plateaued or diverging, which is what decides the repair.

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
    """Print the shape findings for the document body.

    Returns:
        0 when the document satisfies the check and 1 when it does not. ⚑ UNLIKE THE
        READERS IN THIS FILE, THE STATUS IS THE VERDICT HERE — a caller may branch on it,
        and the printed detail explains a failure rather than constituting it.

    """
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

    Returns:
        0 when some width in range admits the document, 1 when none does. ⚑ THE FAILING CASE IS
        NOT *THE DOCUMENT IS TOO WIDE* BUT *NO ADMISSIBLE ANSWER EXISTS* — a line exceeds the
        ceiling, so there is no number to tell the rule, which is a different fact from a
        document that merely needs a generous one.

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
    """Adapt the span listing to the uniform mode signature.

    Returns:
        The verb's exit code, forwarded unchanged. ⚑ AN ADAPTER NORMALISES THE SIGNATURE,
        NEVER THE VERDICT: the dispatch table needs one callable shape, and a mode that
        rewrote a code on the way through would make the table a place where verdicts are
        decided rather than routed.

    """
    return _spans(path)


def _budget_mode(_pattern: str, path: Path, _argv: list[str]) -> int:
    """Adapt the section budget to the uniform mode signature.

    Returns:
        The verb's exit code, forwarded unchanged — see `_spans_mode`.

    """
    return _budget(path)


def _tables_mode(_pattern: str, path: Path, _argv: list[str]) -> int:
    """Adapt the table listing to the uniform mode signature.

    Returns:
        The verb's exit code, forwarded unchanged. ⚑ AN ADAPTER NORMALISES THE SIGNATURE,
        NEVER THE VERDICT: the dispatch table needs one callable shape, and a mode that
        rewrote a code on the way through would make the table a place where verdicts are
        decided rather than routed.

    """
    return _tables(path)


def _rows_mode(_pattern: str, path: Path, argv: list[str]) -> int:
    """Adapt the row listing, which reads a `--where` filter from argv.

    Returns:
        The verb's exit code, forwarded unchanged. ⚑ AN ADAPTER NORMALISES THE SIGNATURE,
        NEVER THE VERDICT: the dispatch table needs one callable shape, and a mode that
        rewrote a code on the way through would make the table a place where verdicts are
        decided rather than routed.

    """
    return _rows(path, argv)


def _labels_mode(_pattern: str, path: Path, _argv: list[str]) -> int:
    """Adapt the label census to the uniform mode signature.

    Returns:
        The verb's exit code, forwarded unchanged. ⚑ AN ADAPTER NORMALISES THE SIGNATURE,
        NEVER THE VERDICT: the dispatch table needs one callable shape, and a mode that
        rewrote a code on the way through would make the table a place where verdicts are
        decided rather than routed.

    """
    return _labels(path)


def _roundtrip_mode(_pattern: str, path: Path, _argv: list[str]) -> int:
    """Adapt the one-pass drift report to the uniform mode signature.

    Returns:
        The verb's exit code, forwarded unchanged. ⚑ AN ADAPTER NORMALISES THE SIGNATURE,
        NEVER THE VERDICT: the dispatch table needs one callable shape, and a mode that
        rewrote a code on the way through would make the table a place where verdicts are
        decided rather than routed.

    """
    return _roundtrip(path)


def _fixpoint_mode(_pattern: str, path: Path, _argv: list[str]) -> int:
    """Adapt the convergence report to the uniform mode signature.

    Returns:
        The verb's exit code, forwarded unchanged. ⚑ AN ADAPTER NORMALISES THE SIGNATURE,
        NEVER THE VERDICT: the dispatch table needs one callable shape, and a mode that
        rewrote a code on the way through would make the table a place where verdicts are
        decided rather than routed.

    """
    return _fixpoint(path)


def _lint_mode(_pattern: str, path: Path, argv: list[str]) -> int:
    """Adapt the shape rules, which read a `--width` from argv, over a PATH POPULATION.

    ⚑⚑ MANY PATHS, LIKE `verify` — W8, 2026-09-20. A corpus-wide count (`how many files carry
    MD056?`) was UNMEASURABLE through this mode: `find … -exec mdstruct lint {} +` handed it
    ninety paths and it read the first, and a grep over the result returned 0 with a FAILED
    positive control. A shell loop is refused by this repository's no-chaining hook and is the
    wrong instrument anyway — the tool owes the mode. Each file prints its own findings and its
    own denominator line, exactly as before; the file count is the count of those lines.

    Returns:
        The WORST code over every path: 0 every document satisfies the check, 1 some does not,
        2 some path does not exist. ⚑ AN ADAPTER NORMALISES THE SIGNATURE, NEVER THE VERDICT:
        the per-file code is `_lint`'s own, folded with `max`.

    """
    return _over_paths(path, argv, lambda p: _lint(p, argv))


def _write_section(path: Path, needle: str, argv: list[str], *, append: bool) -> int:
    """Replace or append one section's body, printing the diff or applying it.

    ⚑⚑⚑ THE FIRST WRITE MODE THIS TOOL HAS EXPOSED, and the library functions predate it by a
    long way — `replace_section` and `append_to_section` were reachable only as an import, so the
    structural-query hook routed WRITES to a CLI that had none. A gate naming a successor is half
    a gate when the successor has no mode for the job, and that was measured by hitting the
    refusal while trying to file a section about it.

    ⚑⚑ THE BODY ARRIVES AS A FILE, NEVER AS AN ARGUMENT. A multi-line body passed inline is the
    `>>` this toolkit exists to replace: a shell that can hand over arbitrary text is a shell
    doing the structuring. `--body-file -` reads stdin, so a caller can still pipe without the
    body becoming argv.

    ⚑⚑ DRY RUN IS THE DEFAULT AND `--apply` IS THE OPT-IN, which is this repository's
    expensive-reading-must-not-be-default rule applied to a WRITE: the destructive mode is the
    flag you reach for, not the one you get by forgetting. The refusal to combine them is not a
    precedence rule — `--dry-run --apply` has two bad resolutions and guessing between them is how
    a caller loses a document.

    ⚑ `exact=` IS THREADED THROUGH, because the ambiguity refusal and its escape compose at the
    WRITE path specifically: `linux-sources-94` reports substrate's refusal on `"§4"` as the only
    reason a write did not destroy two sections of their protocol file, and a correct refusal a
    caller cannot escape is a dead end. Both halves are one design.

    Args:
        path: the document to rewrite.
        needle: the heading to target — a substring by default, the whole text under `--exact`.
        argv: the full argument vector, for the modifiers this mode owns.
        append: append inside the section rather than replacing its body.

    Returns:
        0 when the rewrite is derived (and applied, under `--apply`), 2 on any refusal. ⚑ A
        REFUSAL IS 2 AND NEVER AN EMPTY DIFF: *I could not find that section* and *that section is
        already what you asked for* are different facts, and collapsing them would let a typo read
        as a no-op.

    """
    body_file = _flag(argv, "--body-file")
    if body_file is None:
        sys.stderr.write(
            f"mdstruct: {'append-section' if append else 'replace-section'} needs --body-file.\n"
            f"    The body is a FILE, not an argument: a multi-line body on the command line is\n"
            f"    the shell append this tool exists to replace. Use `--body-file -` for stdin.\n")
        return 2
    if "--apply" in argv and "--dry-run" in argv:
        sys.stderr.write(
            "mdstruct: state exactly one of --apply / --dry-run.\n"
            "    Both together is an incoherent instruction with two bad resolutions — a\n"
            "    write the caller believed was a preview, or the reverse.\n")
        return 2

    # ⚑⚑⚑ THE TARGET AND THE BODY MUST NOT BE THE SAME FILE, and the shape that produces it is a
    # DROPPED HEADING rather than a typo. Measured: `replace-section FILE.md --body-file B.md` with
    # the heading omitted leaves two valid positionals, so the FILE becomes the heading and `B.md`
    # becomes the document — and the tool was one matching heading away from rewriting the body
    # file instead of the target. The arity check cannot see this, because the shape is legal.
    # ⚑⚑ THE FINDER REFUSED IT HERE ONLY BY ACCIDENT of the body file having no headings. A refusal
    # that depends on the contents of the wrong file is not a guard; this one is about IDENTITY, so
    # it holds whatever either file contains.
    if body_file != "-" and Path(body_file).resolve() == path.resolve():
        sys.stderr.write(
            f"mdstruct: the target and the body file are the same document ({path}).\n"
            f"    This is what a DROPPED HEADING looks like: with the heading omitted the file\n"
            f"    slides into the heading slot and --body-file's argument becomes the target.\n"
            f"    Re-run as: mdstruct {'append-section' if append else 'replace-section'} "
            f"HEADING FILE.md --body-file BODY.md\n")
        return 2

    # ⚑⚑ `sys.stdin.read()` IS `Any`, and the cast is where that is stated — the same narrow-at-the
    # -boundary discipline the sibling `fence` applies to argparse's `Namespace`.
    # ⚑ AND I CHASED IT THROUGH THREE WRONG DIAGNOSES, worth recording because each looked
    # plausible. First I blamed the two writers' differing signatures and split a ternary into an
    # if/else; then an annotation on the binding, which types the NAME and leaves the EXPRESSION
    # `Any`; then `str(...)`, which returns `str` while the argument stays `Any`. mypy named the
    # same line every time and reported `str | Any` — a UNION, so the `str` half was never the
    # problem. The checker was precise and I read past it twice.
    if body_file == "-":
        body = cast("str", sys.stdin.read())
    else:
        body = Path(body_file).read_text(encoding="utf-8")
    exact = "--exact" in argv
    try:
        if append:
            new_text, span = sections.append_to_section(path, needle, body, exact=exact)
        else:
            new_text, span = sections.replace_section(path, needle, body, exact=exact)
    except LookupError as e:
        # ⚑ THE FINDER'S OWN MESSAGE IS THE REFUSAL, verbatim. It already names both candidates on
        # an ambiguous needle and tells the caller to pass `--exact`; restating it here would be a
        # second spelling of one fact, which is the drift this tool has measured in itself twice.
        sys.stderr.write(f"mdstruct: {e}\n")
        return 2

    if "--apply" in argv:
        path.write_text(new_text, encoding="utf-8")
        sys.stdout.write(f"  {path}: wrote {'into' if append else 'over'} "
                         f"{'#' * span.level} {span.text} (L{span.start}-{span.end - 1})\n")
        return 0
    sys.stdout.write(f"  {path}: would write {'into' if append else 'over'} "
                     f"{'#' * span.level} {span.text} (L{span.start}-{span.end - 1})\n")
    sys.stdout.write("  ── the rewritten document follows; re-run with --apply to write it ──\n")
    sys.stdout.write(new_text if new_text.endswith("\n") else new_text + "\n")
    return 0


def _verify_one(path: Path) -> int:
    """Verify one document against this tool's own contract.

    ⚑ THE FACT WAS ALREADY HERE, IN THE WRONG FORM. This summary read *Returns 0 when every
    heading reaches the section list* — true, complete, and invisible to a reader (human or rule)
    looking for a Returns section. The content did not change; only where it lives did.

    Returns:
        0 when every source heading reaches the section list, 1 when any is SWALLOWED. ⚑ A
        swallowed heading is the defect this whole tool exists to catch: its parent silently
        absorbs the lines, so a bounded write against the preceding section lands inside a
        section nobody can see. The unreachable headings are printed because the count alone
        does not say WHERE a write would go wrong.

    """
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

    Returns:
        The WORST code over every path: 0 all verified, 1 some heading is swallowed, 2 some path
        does not exist. ⚑⚑ THREE VALUES, NOT TWO, AND THE THIRD IS THE ONE THAT MATTERS: *a file
        I could not read* is not *a file that failed*, and collapsing them would let a typo'd
        path report as a clean document. The same distinction this repository draws between
        ABSENT and EMPTY everywhere else.
        ⚑ `max` RATHER THAN FIRST-FAILURE, which is what makes the loop above worth running to
        the end — a caller learns the severest finding across the whole corpus in one run.

    """
    return _over_paths(path, argv, _verify_one)


def _over_paths(path: Path, argv: list[str], one: Callable[[Path], int]) -> int:
    """Run `one` over every path operand and return the WORST code.

    ⚑⚑⚑ THE OPERANDS COME FROM THE SAME PARSE `main` RAN, through `_mode_operands`, which returns
    them WITHOUT the mode word — so the whole list IS the path population, and `path` (already
    `operands[0]`) is not added a second time. Two earlier cuts of this loop, inside `verify`,
    were each off by one: one indexed `[2:]` over a list that still carried the mode and read
    the first file TWICE (measured: `verify README.md` printed the same green line twice); the
    next added `[1:]` and silently SKIPPED ONE PATH. Both were indexing over a list whose first
    element meant something different from the rest; a list of only paths has no such element.

    ⚑⚑ SHARED BY `verify` AND `lint` (W8, 2026-09-20) so a mode that takes a population has one
    loop, not one per mode: a second spelling of *iterate, refuse a missing file, keep the worst*
    would be a second thing to drift — and `lint` reading one file where the corpus has ninety
    was exactly the reader failure a positive control caught on tick 13.

    ⚑ EVERY PATH IS VISITED BEFORE RETURNING: the loop does not stop at the first failure,
    because a gate that reports one finding per run teaches one finding per round.

    Args:
        path: the first operand, already opened by `main`; the fallback when the parse yields
            no operands (it cannot, once `main` has run, but the loop must not be empty).
        argv: the full argument vector, re-parsed for the population.
        one: the per-file verb; its code is folded with `max`.

    Returns:
        The WORST code over every path: the verb's own codes, or 2 for a path that does not
        exist. ⚑⚑ *A file I could not read* is not *a file that failed*, and collapsing them
        would let a typo'd path report as a clean document — the ABSENT/EMPTY distinction this
        repository draws everywhere else. `max` rather than first-failure is what makes visiting
        every path worth doing: a caller learns the severest finding across the corpus in one run.

    """
    paths = [Path(p) for p in _mode_operands(argv)]
    if not paths:
        paths = [path]
    worst = 0
    for candidate in paths:
        if not candidate.exists():
            sys.stderr.write(f"mdstruct: no such file: {candidate}\n")
            worst = max(worst, 2)
            continue
        worst = max(worst, one(candidate))
    return worst


def _narrowest_mode(_pattern: str, path: Path, _argv: list[str]) -> int:
    """Adapt the narrowest-width report to the uniform mode signature.

    Returns:
        The verb's exit code, forwarded unchanged. ⚑ AN ADAPTER NORMALISES THE SIGNATURE,
        NEVER THE VERDICT: the dispatch table needs one callable shape, and a mode that
        rewrote a code on the way through would make the table a place where verdicts are
        decided rather than routed.

    """
    return _narrowest(path)


def _replace_section_mode(needle: str, path: Path, argv: list[str]) -> int:
    """Adapt the section rewrite to the uniform mode signature.

    Returns:
        The verb's exit code, forwarded unchanged.

    """
    return _write_section(path, needle, argv, append=False)


def _append_section_mode(needle: str, path: Path, argv: list[str]) -> int:
    """Adapt the bounded append to the uniform mode signature.

    Returns:
        The verb's exit code, forwarded unchanged.

    """
    return _write_section(path, needle, argv, append=True)


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
    # ⚑⚑⚑ THE SPAN IS DISCLOSED, AND WITHOUT IT THIS READER INVENTS GAPS. Unscoped, `classify`
    # walks EVERY table and pools them into one total — measured on a census carrying four tables
    # of entirely different kinds (a surveyor roster, a revision log, a status table, and the state
    # vocabulary itself): 56 rows classified and 48 UNCLASSIFIED. Scoped to the one table that
    # carries statuses: 8 rows, 0 unclassified. Same document, same question, and the unscoped
    # reading manufactures a 48-row documentation gap that does not exist, because a revision-log
    # row was never meant to carry a state.
    # ⚑⚑ THE RESIDUE GROUP WAS ALREADY PRINTED AND THAT IS NOT THE SAME THING. Reporting *48
    # unclassified* without saying WHAT WAS READ describes a defect in the document; saying it was
    # read across four tables describes a defect in the QUESTION. This tool's own rule is that
    # every mode prints its denominator, and a count of rows is only half of one — the other half
    # is which tables they came from.
    scope = (f"table {pos_raw}" if pos_raw is not None
             else f"ALL {len(tables.tables(path))} table(s) — pass --table N to scope")
    sys.stdout.write(f"  {len(states)} declared state(s) in {path}, read across {scope}\n")
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
    "budget": _budget_mode,
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
    "replace-section": _replace_section_mode,
    "append-section": _append_section_mode,
}


def _parse_mode_args(mode: str, rest: list[str]) -> tuple[list[str], str | None]:
    """Parse one mode's arguments with argparse; return its operands or the refusal to print.

    ⚑⚑⚑ ARGPARSE PARSES THE REST — operator ruling 2026-09-20 (W9), step 2 of the migration.
    `parse_known_args` so an UNDECLARED flag comes back as an extra rather than as argparse's own
    error text, and the refusal stays word-for-word what it was: it names the mode, the tokens as
    the caller typed them, and the declared set. `tests/test_cli_flags.py`'s parity arm holds
    `main()` against `argparse_parser` directly on every shape.

    ⚑ A VALUE FLAG WITH NO VALUE (`--width` last) is the one refusal argparse makes that the old
    parser did not — `_flag` returned None and the mode carried on. That was a silent
    fall-through; naming it is the better behaviour, and it is not a parity shape because the two
    parsers are MEANT to differ there.

    ⚑⚑ THE UNKNOWN-FLAG REFUSAL IS DERIVED FROM `_MODE_OPTS`, so a mode gaining a flag gains its
    acceptance in one place. It fires AFTER the mode is known, because the declared set is
    per-mode — an earlier check could only compare against a global union, which would accept
    `--width` on `spans` and be no refusal at all for the case that matters.

    Args:
        mode: the dispatched mode, already known to exist.
        rest: every argv token except the program name and the mode word.

    Returns:
        `(operands, None)` on success, or `([], text)` where `text` is the complete refusal for
        stderr. One of the two is always empty.

    """
    parser = argparse_parser(mode)
    try:
        ns, unknown = parser.parse_known_args(rest)
    except argparse.ArgumentError as exc:
        return [], f"mdstruct: {mode}: {exc}\n"
    if unknown:
        declared = sorted(_MODE_OPTS.get(mode, frozenset()) | _GLOBAL_OPTS)
        return [], (
            f"mdstruct: {mode} does not take {', '.join(unknown)}\n"
            f"    it takes {', '.join(declared) if declared else 'no modifiers'}.\n"
            f"    A flag this mode does not read would be SILENTLY IGNORED, and a result\n"
            f"    that ignored your flag is indistinguishable from one that honoured it.\n"
            f"    to pass a literal operand beginning with '-', put it after '--'.\n"
        )
    # ⚑ NARROWED AT THE EDGE: `Namespace` attributes are `Any` and this package's mypy refuses
    # an `Any` expression, so the one untyped value argparse hands back is checked here once.
    raw_operands: object = getattr(ns, "operands", None)
    if not isinstance(raw_operands, list):
        return [], "mdstruct: internal: argparse returned no operand list\n"
    return [str(o) for o in raw_operands], None


def main(argv: list[str] | None = None) -> int:
    """Dispatch one mode.

    ⚑⚑⚑ `argv` IS A PARAMETER BECAUSE READING THE GLOBAL MAKES EVERY BRANCH BELOW UNREACHABLE
    FROM A CASE. The usage arm, the unknown-mode arm and the grep-arity arm are all decided from
    `argv`, and a function that reads `sys.argv` can only be exercised by a caller that MUTATES
    the global and remembers to restore it — which this suite did, in `_run_cli`, with a `finally`.
    A case that forgot the restore would poison its neighbours and nothing would catch it.

    ⚑⚑ THE SHAPE CAME FROM A PEER'S FINDING ABOUT A DIFFERENT REPOSITORY. cassian reported
    `_arg_after` reading `sys.argv` in their copies of a shared hook and named the real defect:
    *the captivity is the defect and the raise is its symptom*. mtools recorded it as owed, cassian
    checked their own tree because of that sentence, and mtools carried it as owed a SECOND time
    without looking. Measured when it finally did: the raise-shape is absent from all 36 sources
    here — positive control constructed, so the searcher is known to see it — and the captivity was
    in exactly this one place.

    Args:
        argv: the full argument vector, `argv[0]` being the program name. Defaults to `sys.argv`.

    ⚑ THE DEFAULT IS THE OLD BEHAVIOUR, EXACTLY. `[project.scripts]` names this function and a
    console script calls it with no arguments; changing what an undeclared caller gets would break
    the installed entry point. Pinned by its own arm.

    Returns:
        the process exit code.

    """
    if argv is None:
        argv = sys.argv
    rest = argv[1:]
    mode_at = _locate_mode(argv)
    if mode_at is None:
        sys.stderr.write(__doc__ or "usage: mdstruct <mode> ...\n")
        return 2
    mode = rest[mode_at]
    run = _MODES.get(mode)
    if run is None:
        sys.stderr.write(f"mdstruct: unknown mode {mode!r} — "
                         f"known modes are {', '.join(sorted(_MODES))}\n")
        return 2

    operands, refusal = _parse_mode_args(mode, rest[:mode_at] + rest[mode_at + 1:])
    if refusal is not None:
        sys.stderr.write(refusal)
        return 2
    args = [mode, *operands]
    # ⚑⚑ THE ARITY REFUSAL IS WHAT CATCHES A VANISHED OPERAND, and for a WRITE that is the
    # difference between a usage error and a rewrite of the wrong section. Naming the mode rather
    # than hardcoding `grep` is what extends that protection to the writers. One rule, two
    # messages: a mode short of its file gets the whole usage; an operand-first mode short of
    # its needle gets its own line.
    need = _MIN_ARGS + (1 if mode in _OPERAND_FIRST else 0)
    if len(args) < need:
        if len(args) < _MIN_ARGS:
            sys.stderr.write(__doc__ or "usage: mdstruct <mode> ...\n")
        else:
            sys.stderr.write(
                f"usage: mdstruct {mode} "
                f"{'PATTERN' if mode == _PATTERN_MODE else 'HEADING'} FILE.md ...\n")
        return 2
    if mode in _OPERAND_FIRST:
        pattern, path = args[1], Path(args[2])
    else:
        pattern, path = "", Path(args[1])

    if not path.exists():
        sys.stderr.write(f"mdstruct: no such file: {path}\n")
        return 2

    return run(pattern, path, argv)


if __name__ == "__main__":
    sys.exit(main())
