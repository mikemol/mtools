# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The control-flow construct roster, the (construct, kind) SQL form table, the boundary operand.

Cleanroomed from substrate's `scratch/_pycodemod_control.py` (W606, commit 1 of 4): the roster,
`SQL_FORM`, `sql_form` and the boundary tables. The census that walks a file and emits sites is a
later module; this one is the vocabulary it reports in. What moved and what did not:

⚑⚑⚑ THE ROSTER IS REPORTED BY CONSTRUCT, IN GROUPS. A frozen list of "what counts" is where a census
silently shrinks, so the roster is wide and a reader who judges one group out of scope can subtract
it. A bare total invites the argument the per-construct breakdown settles.

⚑⚑ `SQL_FORM` IS KEYED ON THE PAIR (construct, kind), NEVER ON THE SITE'S TEXT, and a missing key is
the string `unknown`. A plausible guess in that column is noise that reads like analysis; the
unknowns are the finding, so an unclassified site never carries a form.

⚑ THE EXTERNAL AND MODE TABLES ARE A `Boundary` OPERAND, not module globals. The origin's tables
named what counts as outside the program (filesystem, process, clock) and what counts as
configuration (`sys.argv`, `os.environ`); they are the standard library's, so `PYTHON_BOUNDARY`
carries them as an explicit value a caller can replace. ⚑ WHETHER A LOOP IS OVER ROWS is decided by
the store-read predicates of `storeflow`, whose `StoreVocab` is a required operand here too: an
empty one makes no loop a row loop, so every early exit reports `unknown`, claiming no SQL form.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pycodemod.storeflow import has_read, touches

if TYPE_CHECKING:
    import ast
    from collections.abc import Collection

    from mikemol.pycodemod.storeflow import StoreVocab

CONTROL_KINDS = (
    "external",
    "row-iteration",
    "row-branch",
    "early-exit",
    "mode-branch",
    "unclassified",
)

CONSTRUCT_GROUPS: dict[str, tuple[str, ...]] = {
    "branch": ("if", "elif", "else", "ternary", "match", "case"),
    "loop": ("for", "while", "for-else", "while-else", "comp-for"),
    "guard": ("comp-if",),
    "exit": (
        "break",
        "continue",
        "return-in-loop",
        "return-guard",
        "exit",
        "raise",
        "raise-in-cond",
        "assert",
    ),
    "handler": ("try", "except", "finally", "try-else", "with"),
    "short-circuit": ("and", "or", "or-default", "get-default", "get-none"),
    "fold": ("any", "all", "next-default", "filter"),
    "suspend": ("yield", "yield-from"),
}
CONSTRUCTS = tuple(c for group in CONSTRUCT_GROUPS.values() for c in group)

# ⚑ THE LOOP SET IS ALSO THE "NEVER A MODE-BRANCH" SET: iterating an argument is not branching on
# configuration, and filing it there moves a site out of an honest `unclassified` into a kind that
# reads as a decision someone made.
LOOP_CONSTRUCTS = ("for", "while", "comp-for", "for-else", "while-else", "yield", "yield-from")
EARLY_EXIT_CONSTRUCTS = ("break", "continue", "return-in-loop")
# ⚑ `sys.exit` IS EXTERNAL, NOT MODE: terminating a process is where no rung can reach, and scoring
# it as work that belongs in the engine inflates the half the headline ratio calls migratable.
ALWAYS_EXTERNAL = ("exit",)

UNKNOWN_FORM = "unknown"
EXTERNAL_FORM = "external boundary, stays"
MODE_FORM = "not SQL - selects WHICH statement runs"

SQL_FORM: dict[tuple[str, str], str] = {
    ("for", "row-iteration"): "the SELECT itself - the engine iterates the set",
    ("comp-for", "row-iteration"): "the SELECT itself",
    ("while", "row-iteration"): "recursive CTE",
    ("for-else", "row-iteration"): "NOT EXISTS over the same SELECT",
    ("while-else", "row-iteration"): "NOT EXISTS over the same SELECT",
    ("if", "row-branch"): "WHERE",
    ("elif", "row-branch"): "CASE WHEN",
    ("else", "row-branch"): "CASE ELSE",
    ("ternary", "row-branch"): "CASE",
    ("comp-if", "row-branch"): "WHERE",
    ("and", "row-branch"): "WHERE ... AND ...",
    ("or", "row-branch"): "WHERE ... OR ...",
    ("or-default", "row-branch"): "COALESCE",
    ("get-default", "row-branch"): "COALESCE / LEFT JOIN with a default",
    ("get-none", "row-branch"): "LEFT JOIN",
    ("any", "row-branch"): "EXISTS",
    ("all", "row-branch"): "NOT EXISTS (negated predicate)",
    ("next-default", "row-branch"): "LIMIT 1 + COALESCE",
    ("filter", "row-branch"): "WHERE",
    ("match", "row-branch"): "CASE",
    ("case", "row-branch"): "CASE WHEN",
    ("assert", "row-branch"): "CHECK constraint",
    ("yield", "row-iteration"): "the SELECT's own output - the cursor IS the generator",
    ("yield-from", "row-iteration"): "the SELECT's own output",
}
# An early exit's form depends on WHAT the enclosing loop iterates, not on the exit itself.
SQL_FORM_EXIT_ROW = {
    "break": "LIMIT 1 / EXISTS",
    "continue": "WHERE NOT (...)",
    "return-in-loop": "LIMIT 1",
}


@dataclass(frozen=True, slots=True)
class Boundary:
    """What counts as outside the program, and what counts as configuration - caller-supplied.

    `roots` are module names whose attributes are external; `names` are bare names; `attrs` are
    method names that reach outside; `exceptions` are exception types whose handler is external on
    the TYPE. `mode_dotted` are (root, attribute) pairs read as configuration, and `mode_names` bare
    names read as configuration. ⚑ THE MODE TEST RUNS BEFORE THE ROOT TEST in the census: `os` is a
    root, and `os.environ` must still be configuration.
    """

    roots: frozenset[str]
    names: frozenset[str]
    attrs: frozenset[str]
    exceptions: frozenset[str]
    mode_dotted: frozenset[tuple[str, str]]
    mode_names: frozenset[str]


# ⚑ NOT `hashlib`, `random` OR `uuid`: external means no rung can reach it, a claim about
# reachability and not about purity, and counting content-addressing as irreducible would inflate
# the one number the census exists to produce.
PYTHON_BOUNDARY = Boundary(
    roots=frozenset(
        {
            "os",
            "subprocess",
            "shutil",
            "glob",
            "tempfile",
            "socket",
            "urllib",
            "http",
            "requests",
            "pathlib",
            "io",
            "gzip",
            "zipfile",
            "tarfile",
            "struct",
            "signal",
            "threading",
            "multiprocessing",
            "concurrent",
            "fcntl",
            "select",
            "platform",
            "getpass",
            "atexit",
            "time",
            "shlex",
            "pickle",
            "csv",
            "webbrowser",
            "resource",
        }
    ),
    names=frozenset({"open", "input", "print", "__file__", "Path", "eval", "exec", "compile"}),
    attrs=frozenset(
        {
            "read",
            "readline",
            "readlines",
            "write",
            "writelines",
            "communicate",
            "flush",
            "seek",
            "unlink",
            "mkdir",
            "makedirs",
            "listdir",
            "walk",
            "rmtree",
            "check_output",
            "check_call",
            "call",
            "Popen",
            "run_command",
        }
    ),
    exceptions=frozenset(
        {
            "OSError",
            "IOError",
            "FileNotFoundError",
            "PermissionError",
            "EOFError",
            "BrokenPipeError",
            "TimeoutError",
            "ConnectionError",
            "KeyboardInterrupt",
            "CalledProcessError",
            "SystemExit",
            "UnicodeDecodeError",
        }
    ),
    mode_dotted=frozenset({("sys", "argv"), ("os", "environ")}),
    mode_names=frozenset({"__name__", "__main__"}),
)


def sql_form(construct: str, kind: str, *, loop_is_row: bool) -> str:
    """Return the relational form of a (construct, kind) pair, or `unknown` when none is named.

    ⚑ KEYED ON THE PAIR AND THE LOOP'S PROVENANCE, never on a site's text: an early exit has a form
    only when the enclosing loop iterates rows.

    Returns:
        the external or mode form for those kinds, the loop-dependent form for an early exit, else
        the table entry or `unknown`.

    """
    if kind == "external":
        return EXTERNAL_FORM
    if kind == "mode-branch":
        return MODE_FORM
    if kind == "early-exit":
        return SQL_FORM_EXIT_ROW.get(construct, UNKNOWN_FORM) if loop_is_row else UNKNOWN_FORM
    return SQL_FORM.get((construct, kind), UNKNOWN_FORM)


def is_row_loop(
    iterable: ast.AST | None,
    rows: Collection[str],
    rfns: Collection[str],
    vocab: StoreVocab,
) -> bool:
    """Report whether a loop's iterable (or `while` test) carries rows, for `sql_form`.

    Returns:
        True when the expression mentions a row name or contains a store read by `vocab`.

    """
    return touches(iterable, rows) or has_read(iterable, rfns, vocab)
