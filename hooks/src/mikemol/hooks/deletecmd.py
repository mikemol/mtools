# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name the targets of the recursive deletes in a shell command, or refuse a form it cannot read.

W1919's hook refuses a recursive delete whose target the session did not create (W1994 is this
reader). Judging a target needs the target, and a command's text is the only place it is. This
reads that text and nothing else: no filesystem, no environment.

⚑ FOUR FORMS: `rm` with a recursive flag (`-r`, `-R`, `-rf`, `--recursive`, in any order and
combination), `git clean` with a force flag and no dry-run flag (its targets are the pathspecs, or
the working directory when none is given), and `find` with `-delete` (its targets are the leading
path operands, or `.` when none is given). A command that chains several is read segment by
segment, split on `&&`, `||`, `;`, `|` and `&`.

⚑ A TARGET IT CANNOT READ IS REFUSED, NEVER GUESSED: a word built from a variable, a command
substitution or a backtick (`rm -rf $DIR`, `rm -rf "$(cat x)"`) names nothing the hook can judge,
and a command that does not split into words (an unbalanced quote) cannot be read at all. Both
raise `UnreadableError`, and the caller decides what refusing means.

⚑ WHAT IT DOES NOT READ, stated so nobody assumes it: `find ... -exec rm -rf {} +`, a delete
through `xargs`, and a program that deletes by its own means. Those are W1995's remedy to name; this
module reads the four spellings above.

CONSUMED BY: the recursive-delete hook (W1919, W1995).
"""

import shlex
from dataclasses import dataclass
from pathlib import PurePosixPath

OPERATORS = frozenset({"&&", "||", ";", "|", "&"})
EXPANSIONS = ("$", "`")
RM = "rm"
GIT = "git"
FIND = "find"
CLEAN = "clean"
DELETE = "-delete"
HERE = "."
RM_FORM = "rm"
CLEAN_FORM = "git-clean"
FIND_FORM = "find-delete"
PREFIXES = frozenset({"sudo", "command"})
_EXPRESSION_STARTS = ("-", "(", "!")


class UnreadableError(ValueError):
    """A command whose recursive-delete targets cannot be read from its text."""


@dataclass(frozen=True)
class Delete:
    """One recursive delete found in a command: the form it took and the targets it names."""

    form: str
    targets: tuple[str, ...]


def _segments(command: str) -> list[list[str]]:
    # The command's words, split into one list per simple command.
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        words = list(lexer)
    except ValueError as caught:
        msg = f"the command does not split into words: {caught}"
        raise UnreadableError(msg) from caught
    segments: list[list[str]] = [[]]
    for word in words:
        if word in OPERATORS:
            segments.append([])
        else:
            segments[-1].append(word)
    return [segment for segment in segments if segment]


def _split(args: list[str]) -> tuple[list[str], list[str]]:
    # The flags and the operands of an argument list; `--` ends the flags.
    flags: list[str] = []
    for index, word in enumerate(args):
        if word == "--":
            return flags, args[index + 1 :]
        if not word.startswith("-") or word == "-":
            return flags, args[index:]
        flags.append(word)
    return flags, []


def _letters(flags: list[str]) -> str:
    # The single-letter options among short flags, `-rf` giving `rf`.
    return "".join(word[1:] for word in flags if not word.startswith("--"))


def _rm(args: list[str]) -> Delete | None:
    flags, operands = _split(args)
    recursive = "--recursive" in flags or any(c in _letters(flags) for c in "rR")
    return Delete(RM_FORM, tuple(operands)) if recursive else None


def _clean(args: list[str]) -> Delete | None:
    # `git clean` after git's own global options (`-C path`, `-c key=value`, other flags).
    index = 0
    while index < len(args) and args[index].startswith("-"):
        index += 2 if args[index] in {"-C", "-c"} else 1
    if index >= len(args) or args[index] != CLEAN:
        return None
    flags, operands = _split(args[index + 1 :])
    letters = _letters(flags)
    forced = "--force" in flags or "f" in letters
    dry = "--dry-run" in flags or "n" in letters
    if not forced or dry:
        return None
    return Delete(CLEAN_FORM, tuple(operands) or (HERE,))


def _find(args: list[str]) -> Delete | None:
    if DELETE not in args:
        return None
    paths: list[str] = []
    for word in args:
        if word.startswith(_EXPRESSION_STARTS):
            break
        paths.append(word)
    return Delete(FIND_FORM, tuple(paths) or (HERE,))


def _delete_of(segment: list[str]) -> Delete | None:
    # The recursive delete a simple command is, if it is one; a sudo or command prefix is skipped.
    words = list(segment)
    while words and PurePosixPath(words[0]).name in PREFIXES:
        words = words[1:]
    if not words:
        return None
    name, args = PurePosixPath(words[0]).name, words[1:]
    if name == RM:
        return _rm(args)
    if name == GIT:
        return _clean(args)
    return _find(args) if name == FIND else None


def deletes(command: str) -> list[Delete]:
    """Find every recursive delete in `command` and name its targets.

    Returns:
        the deletes in order of appearance; empty when the command holds none.

    Raises:
        UnreadableError: when the command does not split into words, or a delete's target is built
            from a variable, a command substitution or a backtick.

    """
    found: list[Delete] = []
    for segment in _segments(command):
        delete = _delete_of(segment)
        if delete is None:
            continue
        bad = next((t for t in delete.targets if any(mark in t for mark in EXPANSIONS)), None)
        if bad is not None:
            msg = f"the target {bad!r} of a {delete.form} is built by expansion; it cannot be read"
            raise UnreadableError(msg)
        found.append(delete)
    return found
