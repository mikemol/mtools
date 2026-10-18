# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Find the shell commands that write a file the edit gate never sees (W1560, github-8f 2026-10-18).

⚑ THE OPERATOR'S RULING (2026-10-18, host session line 78599): "mechanization should not be done in
a language we don't have persistent rigor for." A file written by `perl`, `sed -i`, `tee`, a heredoc
append or a `cp` out of a scratch directory is never judged by the edit bar, which runs on the Write
and Edit tools. A `# noqa` line reached a test file that way. So a Bash command that WRITES INTO THE
PROJECT TREE is refused here, in the hook that already refuses an inline interpreter, and the reason
says what to do: Write or Edit the file, or run a tool.

⚑ STRUCTURAL, NOT A GIT QUERY: whether a path is tracked would need a subprocess in a hook that runs
on every command. The rule is the location instead: a redirect, `cp`, `mv` or `install` whose
destination is inside the project root. A write outside it (a scratchpad, `/var/tmp`) is not this
rule's business. `sed -i`, `awk -i inplace`, `perl` and `tee` write in place or beside the input, so
they are refused wherever they appear in command position.

⚑ NO LINK IS FOLLOWED: the destination is normalised as text (`..` collapsed), never resolved, so a
link cannot turn an inside path into an outside one in this check.

⚑ IT FAILS OPEN: with no project root named only the location-free rules apply, and a destination it
cannot read is not a finding.

CONSUMED BY: `no_chaining.analyze` (W1560).
"""

import os
import re
from collections.abc import Sequence
from pathlib import Path

Finding = tuple[str, str]

_SEGMENT_END = frozenset({"|", "||", "&&", ";", "&", "|&"})
_WRAPPERS = frozenset({"env", "timeout", "nice", "command", "exec", "sudo", "xargs"})
_REDIRECTS = frozenset({">", ">>", ">|"})
_COPIERS = frozenset({"cp", "mv", "install"})
_ASSIGN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
_SED_IN_PLACE = re.compile(r"^-[A-Za-z]*i|^--in-place")
_NULL = "/dev/null"
_MIN_PATHS = 2
_FIX = "Write or Edit the file (the edit bar judges it), or run a tool that writes it"
_REASONS = {
    "inplace": f"an in-place edit that bypasses the edit bar — {_FIX}",
    "perl": f"perl: no rigor bar here (operator 2026-10-18) — {_FIX}",
    "tee": f"tee writes a file the edit bar never sees — {_FIX}",
    "redirect": f"a redirect into the project tree — {_FIX}",
    "copy": f"a copy from outside the project into it — {_FIX}",
}


def _name(token: str) -> str:
    # The program a token names: its basename.
    return Path(token).name


def _inside(target: str, root: Path | None, cwd: Path) -> bool:
    """Say whether a destination, read as text, lies inside the project root.

    Returns:
        True when `root` is known and the normalised path is the root or below it.

    """
    if root is None or not target or target == _NULL or target.startswith("&"):
        return False
    given = Path(target)
    path = Path(os.path.normpath(given if given.is_absolute() else cwd / given))
    return path == root or root in path.parents


def _past_wrapper(rest: list[str]) -> list[str]:
    # Drop a wrapper's own flags, numbers and env assignments; what is left starts the real command.
    for index, word in enumerate(rest):
        if not (word.startswith("-") or word.isdecimal() or _ASSIGN.match(word)):
            return rest[index:]
    return []


def _program(words: Sequence[str]) -> tuple[str, list[str]] | None:
    """Find the program of one command, past env assignments and wrapper words.

    Returns:
        the program's name and its arguments, or None when the command has no program.

    """
    rest = list(words)
    while rest:
        head = rest[0]
        if _ASSIGN.match(head):
            rest = rest[1:]
        elif _name(head) in _WRAPPERS:
            rest = _past_wrapper(rest[1:])
        else:
            return _name(head), rest[1:]
    return None


def _commands(tokens: Sequence[str]) -> list[tuple[str, list[str]]]:
    """Split a token stream at the shell operators into (program, arguments) pairs.

    Returns:
        one pair per command that has a program.

    """
    found: list[tuple[str, list[str]]] = []
    current: list[str] = []
    for token in [*tokens, ";"]:
        if token not in _SEGMENT_END:
            current.append(token)
            continue
        program = _program(current)
        if program is not None:
            found.append(program)
        current = []
    return found


def _edits_in_place(name: str, args: Sequence[str]) -> bool:
    # sed -i and gawk's `-i inplace` rewrite their input file.
    if name == "sed":
        return any(_SED_IN_PLACE.match(arg) for arg in args)
    return name in {"awk", "gawk"} and "inplace" in args


def _copies_in(args: Sequence[str], root: Path | None, cwd: Path) -> bool:
    # A cp/mv/install whose destination is inside the project while a source is outside it.
    names = [a for a in args if not a.startswith("-")]
    if len(names) < _MIN_PATHS:
        return False
    *sources, dest = names
    return _inside(dest, root, cwd) and any(not _inside(s, root, cwd) for s in sources)


def _reason(name: str, args: Sequence[str], root: Path | None, cwd: Path) -> str:
    # The reason one command writes outside the edit bar, or "" when it does not.
    if name in {"perl", "tee"}:
        return _REASONS[name]
    if _edits_in_place(name, args):
        return _REASONS["inplace"]
    return _REASONS["copy"] if name in _COPIERS and _copies_in(args, root, cwd) else ""


def findings(tokens: Sequence[str], root: Path | None, cwd: Path) -> list[Finding]:
    """List the file-writing tells of one Bash command, given its shell tokens.

    Returns:
        (token, reason) pairs: in-place editors, `perl`, `tee`, a copy into the project and a
        redirect into it, in the order met.

    """
    found = [(n, r) for n, a in _commands(tokens) if (r := _reason(n, a, root, cwd))]
    found.extend(
        (token, _REASONS["redirect"])
        for index, token in enumerate(tokens[:-1])
        if token in _REDIRECTS and _inside(tokens[index + 1], root, cwd)
    )
    return found
