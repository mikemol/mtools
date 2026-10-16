# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Add rule names to a dist's `[tool.ruff.lint] ignore` list, as text, keeping what is there.

⚑⚑ A REWRITE CAN MAKE A RULE CONTRADICT THE TARGET, AND THE FIX IS THE SAME EVERY TIME. Dropping a
keyword-only `*,` marker (Codon rejects it) leaves booleans in positional slots, which ruff's
boolean-positional rules refuse; hoisting a `TYPE_CHECKING` import (Codon has no such guard) leaves
an import that ruff's typing-only rules want guarded. Six dists were fixed by hand with the same
two edits before this existed (mtools:W1374 audit), so the edit is a function: given the file's
text and the rule names, return the text with the names added, or None when there is no `ignore`
list to add them to.

⚑ ENUMERABLE, NEVER A LINE: the entry goes in the dist's pyproject list, the one place the bar
accepts a suppression, with the reason as a comment beside it. A rule already listed is not added
twice, and nothing else in the file moves.
"""

import re
from typing import cast

_TABLE = "[tool.ruff.lint]"
_NEXT_TABLE = re.compile(r"^\[", re.MULTILINE)
_SINGLE = re.compile(r"^ignore = \[(?P<items>[^\n\]]*)\]$", re.MULTILINE)
_MULTI = re.compile(r"^ignore = \[\n(?P<body>.*?)^\]$", re.MULTILINE | re.DOTALL)


def _section(text: str) -> tuple[int, int] | None:
    # The start and end of the `[tool.ruff.lint]` table's own keys, or None when it is absent.
    at = f"\n{text}".find(f"\n{_TABLE}\n")
    if at < 0:
        return None
    start = at + len(_TABLE) + 1
    after = _NEXT_TABLE.search(text, start)
    return start, after.start() if after else len(text)


def _entries(rules: list[str], reason: str) -> str:
    comment = "".join(f"    # {line}\n" for line in reason.splitlines())
    return comment + "".join(f'    "{rule}",\n' for rule in rules)


def _single_items(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _extend_oneline(text: str, bounds: tuple[int, int], path: str, rules: list[str]) -> str | None:
    # A file already listed on one line gets the missing rules appended on that line.
    start, end = bounds
    body = text[start:end]
    entry = re.search(rf'^"{re.escape(path)}" = \[(?P<items>[^\n\]]*)\]$', body, re.MULTILINE)
    if entry is None:
        return None
    held = _single_items(cast("str", entry.group("items")))
    fresh = [rule for rule in rules if f'"{rule}"' not in held]
    if not fresh:
        return text
    joined = ", ".join([*held, *(f'"{rule}"' for rule in fresh)])
    line = f'"{path}" = [{joined}]'
    return text[:start] + body[: entry.start()] + line + body[entry.end() :] + text[end:]


def _extend_multiline(
    text: str, bounds: tuple[int, int], path: str, rules: list[str]
) -> str | None:
    # A file already listed over several lines gets the missing rules before the closing bracket;
    # any other spelling of its key is not ours to edit, so the answer is None, never a second key.
    start, end = bounds
    body = text[start:end]
    found = re.search(
        rf'^"{re.escape(path)}" = \[\n(?P<items>.*?)^\]$', body, re.MULTILINE | re.DOTALL
    )
    if found is None:
        return None
    fresh = [rule for rule in rules if f'"{rule}"' not in cast("str", found.group("items"))]
    if not fresh:
        return text
    cut = found.end("items")
    added = "".join(f'    "{rule}",\n' for rule in fresh)
    return text[:start] + body[:cut] + added + body[cut:] + text[end:]


def add_for_file(text: str, path: str, rules: list[str], reason: str) -> str | None:
    """Add `rules` for ONE file to `[tool.ruff.lint.per-file-ignores]`, with `reason` above them.

    ⚑ NARROWER THAN THE GLOBAL LIST, AND THE ONLY ROUTE FOR A DIST THAT PINS ITS GLOBAL LIST
    (hooks' `test_the_ignore_list_is_exactly_three_rules`, mtools:W1399): the exemption names the
    file that needed it, never a glob. A file already listed with a one-line list is extended; a
    file not yet listed gets a new entry at the end of the table.

    Returns:
        the new text; the text unchanged when every rule is already listed for the file; None when
        there is no per-file table, or the file's entry is not a one-line list.

    """
    header = "[tool.ruff.lint.per-file-ignores]"
    at = f"\n{text}".find(f"\n{header}\n")
    if at < 0:
        return None
    start = at + len(header) + 1
    after = _NEXT_TABLE.search(text, start)
    bounds = (start, after.start() if after else len(text))
    body = text[bounds[0] : bounds[1]]
    if re.search(rf'^"{re.escape(path)}" = ', body, re.MULTILINE):
        # ⚑ NEVER A SECOND KEY: TOML refuses a duplicate, and a refused pyproject blinds every
        # checker (measured on hooks, whose commit_kata.py entry spans lines).
        return _extend_oneline(text, bounds, path, rules) or _extend_multiline(
            text, bounds, path, rules
        )
    comment = "".join(f"# {line}\n" for line in reason.splitlines())
    listed = ", ".join(f'"{rule}"' for rule in rules)
    block = f'{comment}"{path}" = [{listed}]\n'
    tail = "\n" if after else ""
    return text[:start] + body.rstrip("\n") + "\n\n" + block + tail + text[bounds[1] :]


def add(text: str, rules: list[str], reason: str) -> str | None:
    """Add `rules` to the `[tool.ruff.lint]` ignore list, with `reason` as comments above them.

    Returns:
        the new text; the text unchanged when every rule is already listed; None when the table
        has no `ignore` list to extend.

    """
    bounds = _section(text)
    if bounds is None:
        return None
    start, end = bounds
    head, body, tail = text[:start], text[start:end], text[end:]
    fresh = [rule for rule in rules if f'"{rule}"' not in body]
    if not fresh:
        return text
    multi = _MULTI.search(body)
    if multi is not None:
        cut = multi.end("body")
        return head + body[:cut] + _entries(fresh, reason) + body[cut:] + tail
    single = _SINGLE.search(body)
    if single is None:
        return None
    items = _single_items(cast("str", single.group("items")))
    lines = "".join(f"    {item},\n" for item in items)
    block = f"ignore = [\n{lines}{_entries(fresh, reason)}]"
    return head + body[: single.start()] + block + body[single.end() :] + tail
