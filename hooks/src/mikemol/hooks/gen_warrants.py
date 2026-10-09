# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Emit warrants.bib entries for test modules, transcribed from test docstrings.

Usage: mikemol-gen-warrants [--root DIR] [--layout L] <dist> <module> <section>
           >> <dist>/warrants.bib
   or: mikemol-gen-warrants [--root DIR] [--layout L] <dist> <module>=<section> [...] >> ...
   or: mikemol-gen-warrants --write [--prune] [--title KEY=TITLE ...] <dist> <module>=<section> ...

where <root>/<dist>/tests/test_<module>.py is the file and <section> is the RUBRIC KEY verbatim. A
function whose `-k <name>}` check already appears in warrants.bib is skipped, so re-running over a
grown file emits only the new functions. Several pairs in one call emit in the order given, into
one stream: a whole new distribution in one append, with no shell loop and no interleaving.

⚑⚑ `--write` DOES THE WHOLE JOB (W835, operator 2026-10-06: always mechanize). The stream form left
two hand steps: a `>>` redirect, and a rubric row for any new section, typed by hand, whose lost
trailing TAB broke the commit gate twice in one day. `--write` appends the entries to
`<dist>/warrants.bib` and a row for each new section to the dist's rubric, in whichever of
`rubric.jsonl` or `rubric.tsv` it has (the format is moving), taking each new section's heading from
`--title KEY=TITLE`. It never rewrites or reorders an existing row. A new section with no title is
exit 2 BEFORE anything is written, so a half-update never exists.

⚑ `--prune` REMOVES THE OTHER HALF OF A RENAME: a warrant whose check names a test function that no
longer exists in its test module (or a module that no longer exists) is a claim about nothing, and
renaming or deleting a test leaves one behind. It is dropped before the new entries are appended;
entries whose test still exists are kept byte for byte. Only with `--write`.

⚑⚑ `--prune` IS CHECKED AGAINST AN INDEPENDENT DERIVATION, AND `--dry-run` SHOWS IT (W840, operator
2026-10-06: "set equality, not read the count"). The 41-warrant prune of fence printed a plausible
number and was wrong. `--prune` now REFUSES (exit 2, nothing written) unless the set it would drop
equals the ORPHAN WARRANT set `count_test_functions.py --pairing` reports for the same distribution,
a separate parse, naming every pair in the symmetric difference; an absent or unrunnable checker is
also a refusal. `--dry-run` changes nothing and prints each warrant key it would drop with the
verdict of that comparison (exit 0 when equal, 2 when not); it still takes the usual operands.

⚑⚑ TWO LAYOUTS, BECAUSE THE ROOT IS NOT A DISTRIBUTION (W669). `--layout dist` (the default) is the
layout above: the file under `tests/`, keys `<dist>-<module>-...`, checks run by the distribution's
own `.venv`. `--layout atom` is the repository root's: a test module BESIDE the script it tests
(the runner every distribution's `mutants` target shares), keyed `root-<module>-...` and checked by
the hooks venv's interpreter from the repository root, which is how `check_mutants/warrants.bib`
was written by hand before this existed. In `atom`, `<dist>` names the directory holding the module
and its bib.

⚑ THE ROOT IS THE CWD OR `--root`, NEVER `__file__`. The origin (`.claude/gen_warrants.py`)
derived it from its own location, which is the defect this package exists to end: an installed
module lives in a venv, and a worktree's tests are invisible to a root fixed at the main repo.

⚑ A BRACE IN A DOCSTRING EXITS 2 — the could-not-transcribe code — and writes nothing to stdout,
so a `>>` append never receives a half-stream.

CONSUMED BY: the `mikemol-gen-warrants` console script.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks.payload import as_record, text_of
from mikemol.hooks.warrant_crosscheck import UnverifiableError, difference, independent_orphans

_ARTICLES = ("a", "an", "the")
_LEGACY_ARGC = 2
RUBRIC_NAMES = ("rubric.jsonl", "rubric.tsv")
EXIT_UNTRANSCRIBABLE = 2
# One bib entry, from its `@misc{key,` line to the `}` that closes it on a line of its own, and the
# test a warrant's check names: `-m pytest <file> -k <function>}`.
_ENTRY = re.compile(r"\n?@misc\{[^,\n]+,\n.*?\n\}\n", re.DOTALL)
_CHECKED_TEST = re.compile(r"-m pytest (\S+) -k (\w+)\}")
_KEY = re.compile(r"@misc\{([^,\n]+),")


class BraceError(ValueError):
    """A docstring carries a brace, which would corrupt a BibTeX field."""


class RubricError(ValueError):
    """A new section has no heading, or a heading the rubric format cannot carry."""


@dataclass(frozen=True)
class Layout:
    """Where a test module lives and how its warrants are keyed and checked.

    `tests` is the module's path under its base, with `{module}` filled in; `runner` is the
    interpreter the check command names; `key_prefix` replaces the distribution name in the key, or
    is None to keep it.
    """

    tests: str
    runner: str
    key_prefix: str | None


DIST = Layout("tests/test_{module}.py", ".venv/bin/python3", None)
ATOM = Layout("test_{module}.py", "hooks/.venv/bin/python3", "root")
LAYOUTS = {"dist": DIST, "atom": ATOM}
_LAYOUT_NAMES: tuple[str, ...] = tuple(LAYOUTS)


@dataclass(frozen=True)
class Spec:
    """One module to transcribe: where it is, the rubric section its entries land in, its layout."""

    dist: str
    module: str
    section: str
    layout: Layout = DIST

    @property
    def test_file(self) -> str:
        """Name the module's test file as its check commands spell it."""
        return self.layout.tests.format(module=self.module)

    @property
    def key_prefix(self) -> str:
        """Name the prefix every key of this module starts with."""
        return f"{self.layout.key_prefix or self.dist}-{self.module.replace('_', '-')}-"


@dataclass(frozen=True)
class Options:
    """What one invocation asked for, read from the command line."""

    root: Path
    dist: str
    pairs: list[tuple[str, str]]
    layout: Layout
    titles: dict[str, str]
    write: bool
    prune: bool
    dry_run: bool = False


def _entry(spec: Spec, node: ast.FunctionDef, bib: str) -> str | None:
    """Render one function's entry, or None when the bib already carries it.

    Returns:
        the entry text, or None when already present.

    Raises:
        BraceError: the docstring carries a brace.

    """
    # Keyed on the FILE and the name: two modules may share a test name, and a name-only check
    # skipped the second.
    if f"{spec.test_file} -k {node.name}}}" in bib:
        return None
    doc = ast.get_docstring(node) or ""
    if "{" in doc or "}" in doc:
        msg = f"brace in docstring of {node.name}"
        raise BraceError(msg)
    words = node.name[len("test_") :].split("_")
    prefix = spec.key_prefix
    # An older entry may carry no `check` and keep the leading article in its key.
    if f"{{{prefix}{'-'.join(words)}," in bib:
        return None
    if words[0] in _ARTICLES:
        words = words[1:]
    key = prefix + "-".join(words)
    if f"{{{key}," in bib:
        return None
    first, _, rest = doc.partition("\n")
    title = first.strip().rstrip(".")
    body = " ".join((first + " " + rest).split()).replace("⚑", "").replace("  ", " ")
    claim = textwrap.fill(body, width=88, subsequent_indent=" " * 12)
    check = f"cmd:{spec.layout.runner} -m pytest {spec.test_file} -k {node.name}"
    return (
        f"@misc{{{key},\n"
        f"  section = {{{spec.section}}},\n"
        f"  title  = {{{title}}},\n"
        f"  claim  = {{{claim}}},\n"
        f"  check  = {{{check}}},\n"
        f"}}\n"
    )


def bib_text(path: Path) -> str:
    """Read a warrants.bib, or "" for a distribution that has none yet.

    ⚑ A DISTRIBUTION'S FIRST WARRANTS HAD NO WAY IN (mtools:W873): `--write` read the bib first,
    so a new distribution needed one to exist, and the only ways to make it were a hand edit
    (refused by standing rule 14: the bib is appended from this tool's output, never edited) or a
    shell `touch`, the same hand move under another name. A missing bib is an empty one.

    Returns:
        the file's text, or the empty string when it does not exist.

    """
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def emit(root: Path, dist: str, pairs: list[tuple[str, str]], layout: Layout = DIST) -> list[str]:
    """Return the missing entries for each (module, section) pair, in the order given.

    Returns:
        one entry per test function the bib does not yet carry.

    """
    base = root / dist
    bib = bib_text(base / "warrants.bib")
    out: list[str] = []
    for module, section in pairs:
        spec = Spec(dist, module, section, layout)
        tree = ast.parse((base / spec.test_file).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                entry = _entry(spec, node, bib)
                if entry is not None:
                    out.append(entry)
    return out


def _defined_tests(path: Path) -> set[str] | None:
    """Name the test functions a module defines.

    Returns:
        the names, or None when the module does not exist or does not parse.

    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    # ⚑ THE WHOLE TREE, NOT THE MODULE LEVEL: a class-based suite (fence's `class TestCaps: def
    # test_…`) defines its tests as methods, and reading only the top level judged 41 live warrants
    # stale in fence on the first real run. The pairing check walks the tree for the same reason.
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }


def _stale_pair(
    base: Path, defined: dict[str, set[str] | None], text: str
) -> tuple[str, str] | None:
    """Say whether one bib entry's check names a test that no longer exists.

    ⚑ AN ENTRY WITH NO PARSEABLE CHECK IS KEPT: an older entry may carry none, and what cannot be
    shown stale is not removed. A module that no longer exists makes all its entries stale.

    Returns:
        the (module, test name) its check names when that test is gone, else None.

    """
    checked = _CHECKED_TEST.search(text)
    if checked is None:
        return None
    module, name = checked.group(1), checked.group(2)
    if module not in defined:
        defined[module] = _defined_tests(base / module)
    tests = defined[module]
    return None if tests is not None and name in tests else (module, name)


def prune(base: Path, bib: str) -> tuple[str, int]:
    """Drop the entries whose check names a test that no longer exists.

    Returns:
        the bib text without the stale entries, and how many were dropped.

    """
    defined: dict[str, set[str] | None] = {}
    dropped = 0

    def keep(found: re.Match[str]) -> str:
        nonlocal dropped
        text = found.group(0)
        if _stale_pair(base, defined, text) is None:
            return text
        dropped += 1
        return ""

    return _ENTRY.sub(keep, bib), dropped


def would_drop(base: Path, bib: str) -> list[tuple[str, str, str]]:
    """List what `prune` would drop, by the same rule, without dropping it.

    Returns:
        (warrant key, module, test name) for each stale entry, in bib order.

    """
    defined: dict[str, set[str] | None] = {}
    found: list[tuple[str, str, str]] = []
    for entry in _ENTRY.finditer(bib):
        pair = _stale_pair(base, defined, entry.group(0))
        key = _KEY.search(entry.group(0))
        if pair is not None and key is not None:
            found.append((key.group(1), *pair))
    return found


def rubric_file(base: Path) -> Path | None:
    """Find the distribution's rubric: `rubric.jsonl` when it has one, else `rubric.tsv`.

    Returns:
        the rubric's path, or None for a distribution with no rubric.

    """
    return next((base / name for name in RUBRIC_NAMES if (base / name).is_file()), None)


def rubric_keys(path: Path) -> set[str]:
    """Read the section keys a rubric already declares.

    Returns:
        the keys, from either format; comment and blank lines name nothing.

    """
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if path.suffix == ".jsonl":
            parsed: object = json.loads(line)
            keys.add(text_of(as_record(parsed).get("key")))
        else:
            keys.add(line.split("\t", 1)[0].strip())
    return keys


def rubric_row(path: Path, key: str, title: str) -> str:
    """Render one rubric row in the rubric's own format.

    Returns:
        the row, newline-terminated.

    Raises:
        RubricError: the title holds a tab or a newline (a tsv row cannot carry either).

    """
    if "\t" in title or "\n" in title:
        msg = f"the heading for {key!r} holds a tab or a newline"
        raise RubricError(msg)
    if path.suffix == ".jsonl":
        record: dict[str, str] = {"key": key, "title": title}
        return json.dumps(record, ensure_ascii=False) + "\n"
    return f"{key}\t{title}\n"


def new_rubric_rows(
    base: Path, sections: list[str], titles: dict[str, str]
) -> tuple[Path | None, list[str]]:
    """Build the rows for every section the rubric does not yet declare, in the order given.

    Returns:
        the rubric file (None when the distribution has none, so nothing is added) and the rows.

    Raises:
        RubricError: a new section has no heading.

    """
    path = rubric_file(base)
    if path is None:
        return None, []
    known = rubric_keys(path)
    rows: list[str] = []
    for section in sections:
        if section in known:
            continue
        if section not in titles:
            msg = f"section {section!r} is not in {path.name}: pass --title {section}=<heading>"
            raise RubricError(msg)
        rows.append(rubric_row(path, section, titles[section]))
        known.add(section)
    return path, rows


def append_text(path: Path, text: str) -> None:
    """Append `text` to `path`, first ending an unterminated last line."""
    existing = bib_text(path)
    lead = "" if not existing or existing.endswith("\n") else "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(lead + text)


def _pairs(args: list[str]) -> list[tuple[str, str]]:
    """Read the legacy `<module> <section>` form or the `<module>=<section>` list.

    Returns:
        the (module, section) pairs.

    """
    if len(args) == _LEGACY_ARGC and "=" not in args[0]:
        return [(args[0], args[1])]
    return [(m, s) for m, _, s in (arg.partition("=") for arg in args)]


def _titles(given: list[str]) -> dict[str, str]:
    """Read the repeated `KEY=TITLE` options.

    Returns:
        the heading for each key named.

    """
    return {key: title for key, _, title in (item.partition("=") for item in given)}


def _options(argv: list[str] | None) -> Options:
    """Read the command line.

    Returns:
        the options; argparse exits 2 on a usage error.

    """
    parser = argparse.ArgumentParser(prog="mikemol-gen-warrants", description=__doc__)
    parser.add_argument("--root", default=None, help="repo root (default: the cwd)")
    parser.add_argument("--layout", choices=_LAYOUT_NAMES, default="dist", help="test layout")
    parser.add_argument("--write", action="store_true", help="append to the bib and the rubric")
    parser.add_argument("--prune", action="store_true", help="with --write: drop stale warrants")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the warrants --prune would drop and check them against the pairing check "
        "(changes nothing)",
    )
    parser.add_argument("--title", action="append", help="KEY=HEADING, a new section")
    parser.add_argument("dist")
    parser.add_argument("pairs", nargs="+")
    # ⚑ argparse's `Namespace` is untyped; `vars()` is the boundary, narrowed once per value.
    opts: dict[str, object] = vars(parser.parse_args(argv))
    root_arg = opts["root"]
    pairs_arg = opts["pairs"]
    title_arg = opts["title"]
    return Options(
        root=Path(root_arg) if isinstance(root_arg, str) else Path.cwd(),
        dist=str(opts["dist"]),
        pairs=_pairs([str(a) for a in pairs_arg] if isinstance(pairs_arg, list) else []),
        layout=LAYOUTS[str(opts["layout"])],
        titles=_titles([str(t) for t in title_arg] if isinstance(title_arg, list) else []),
        write=bool(opts["write"]),
        prune=bool(opts["prune"]),
        dry_run=bool(opts["dry_run"]),
    )


def _verified_drops(options: Options) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Find what a prune would drop and compare it with the independent orphan set (W840).

    Returns:
        the (key, module, name) entries it would drop, and the problems: every pair on which the
        pairing check disagrees, or why it could not be asked. No problems means set equality.

    """
    base = options.root / options.dist
    drops = would_drop(base, (base / "warrants.bib").read_text(encoding="utf-8"))
    try:
        orphans = independent_orphans(options.root, options.dist)
    except UnverifiableError as err:
        return drops, [str(err)]
    return drops, difference({(module, name) for _, module, name in drops}, orphans)


def _gate_prune(options: Options) -> int | None:
    """Refuse a prune the independent check disagrees with, or answer a dry run (W840).

    ⚑ BEFORE ANYTHING IS WRITTEN: a refusal here leaves the bib, the rubric and the appended
    entries all untouched, so a disagreement is never half a prune.

    Returns:
        an exit code when the run is over (a dry run's verdict, or a refusal), else None.

    """
    if not (options.dry_run or (options.prune and options.write)):
        return None
    drops, problems = _verified_drops(options)
    if options.dry_run:
        for key, module, name in drops:
            sys.stdout.write(f"WOULD DROP {key}  {module}::{name}\n")
        verdict = "equal to" if not problems else "DISAGREES WITH"
        sys.stdout.write(f"{len(drops)} would drop; {verdict} the pairing check's orphan set\n")
    for problem in problems:
        sys.stderr.write(f"{problem}\n")
    if problems:
        return EXIT_UNTRANSCRIBABLE
    return 0 if options.dry_run else None


def _apply(options: Options, entries: list[str], rubric: Path | None, rows: list[str]) -> int:
    """Prune stale warrants when asked, then append the entries and the rubric rows.

    ⚑ EVERYTHING WAS BUILT BEFORE THIS RUNS: a refusal (a brace, an untitled section) has already
    happened, so what is written here cannot be half of an update.

    Returns:
        how many stale warrants were dropped.

    """
    base = options.root / options.dist
    dropped = 0
    if options.prune:
        pruned, dropped = prune(base, (base / "warrants.bib").read_text(encoding="utf-8"))
        if dropped:
            (base / "warrants.bib").write_text(pruned, encoding="utf-8")
    if entries:
        append_text(base / "warrants.bib", "\n" + "\n".join(entries))
    if rubric is not None and rows:
        append_text(rubric, "".join(rows))
    return dropped


def main(argv: list[str] | None = None) -> int:
    """Write or print the missing entries, and report the counts on stderr.

    Returns:
        0 on success, 2 when a docstring carries a brace or a new section has no heading.

    """
    options = _options(argv)
    rubric: Path | None = None
    rows: list[str] = []
    try:
        out = emit(options.root, options.dist, options.pairs, options.layout)
        if options.write:
            sections = [section for _, section in options.pairs]
            rubric, rows = new_rubric_rows(options.root / options.dist, sections, options.titles)
    except (BraceError, RubricError) as err:
        sys.stderr.write(f"{err}\n")
        return EXIT_UNTRANSCRIBABLE
    refused = _gate_prune(options)
    if refused is not None:
        return refused
    if options.write:
        dropped = _apply(options, out, rubric, rows)
        sys.stderr.write(
            f"{len(out)} warrants appended, {dropped} stale dropped, {len(rows)} rubric rows\n"
        )
        return 0
    if out:
        sys.stdout.write("\n" + "\n".join(out))
    sys.stderr.write(f"{len(out)} warrants\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
