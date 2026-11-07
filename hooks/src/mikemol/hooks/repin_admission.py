# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Clause R of the pace input admission: a repin brings exactly one NEW vendored sha (W2311, W2332).

A repo that vendors mikemol wheels takes a software update as a stack whose every non-queue file
is repin-owned and whose every change is the sha in a wheel's name and hash. The pace guard owes it
no ratchet fall, because it forgives no debt. THE WARRANT IS github-14'S, NOT THE OPERATOR'S: he
extended the pinned-repoint ruling (host line 126887, which spoke of repointing to a pinned
tool) to a stack past the pace, and told the operator so they can overrule it. This module is
the pure judgement over the stack's frozen blobs and nothing else: it reads no file, runs nothing
and writes nothing, so what it says is a function of the two maps it is given.

⚑ A REPIN IS THE SAME TEXT WITH ONE NEW SHA IN IT (W2301 v4, clause R). Each text file is compared,
LINE TERMINATORS KEPT, with the sha tokens and hashes of its wheel lines masked, so one stray line,
a dropped trailing newline or a CRLF leaves the masked texts unequal and refuses the stack. The
shas the stack brings are those in the new texts and added wheel names that HEAD's texts and wheel
names do not already hold; there must be exactly one (either spelling, `+g<sha>` or `+<sha>`), so a
pin held at an older sha is not a second sha, and a stack that moves no sha is not a repin (the
2026-11-07 review of f1710762, B1 and B2). Every wheel the stack adds must be named by a new text.

⚑ WHAT THIS CANNOT SEE, STATED: the wheel bytes are not read, so a wheel built from a different
source passes if its name carries the new sha; and the sha need not be a landed mtools sha. The
vendored checksum row and `mikemol-repin` produce both; the guard checks the shape of the change.

⚑ A SHAPE RULE OUTSIDE THE ROW TABLE, BY DESIGN: the table admits one reviewed change; clause R
admits a software update only, which the design (.claude/design/W2301-pace-input-admission.md, the
"how a row reaches nemik" section) names as the one route that forgives no debt and needs no
per-repin row. It leaves an audit mark: the landing writes `Admission: <repo>/repin-<sha>`.

CONSUMED BY: `ratchet_pace` at submit and at landing (W2329).
"""

import re
from collections.abc import Mapping

Side = Mapping[str, str | None]
TEXT_FILES = frozenset(
    {
        "pyproject.toml",
        "MODULE.bazel",
        "uv.lock",
        "vendor/wheels/SHA256SUMS",
        "vendor/wheels/README.md",
    }
)
_WHEEL = re.compile(
    r"vendor/wheels/mikemol_[a-z0-9]+-\d+\.\d+\.\d+\+g?(?P<sha>[0-9a-f]{7,40})-py3-none-any\.whl"
)
_TOKEN = re.compile(r"(?P<head>\d+\.\d+\.\d+\+)g?(?P<sha>[0-9a-f]{7,40})(?=-py3-none-any|\")")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_SUM = re.compile(r"^[0-9a-f]{64}(?=  \./mikemol_)")
_HEX = re.compile(r"\b[0-9a-f]{7,40}\b")
_VERSION = re.compile(r'^version = "[^"]*"$')
_TERMINATORS = "\r\n"


def _lines(text: str) -> list[tuple[str, str, bool]]:
    """Split a text into (body, terminator, belongs) per line, terminators kept.

    A line belongs to a mikemol wheel when it names a `mikemol_` wheel file, or is the `version`
    line of a lock package whose `name` line names a mikemol dist.

    Returns:
        one triple per line of `text`.

    """
    split: list[tuple[str, str, bool]] = []
    inside = False
    for raw in text.splitlines(keepends=True):
        body = raw.rstrip(_TERMINATORS)
        if body.startswith("[[package]]"):
            inside = False
        elif body.startswith("name = "):
            inside = "mikemol" in body
        belongs = "mikemol_" in body or (inside and _VERSION.match(body) is not None)
        split.append((body, raw[len(body) :], belongs))
    return split


def _mask_line(body: str, *, belongs: bool) -> str:
    """Blank the repinned values of one line.

    Returns:
        a comment line with its hex runs blanked, a wheel line with its sha tokens and hashes
        blanked, any other line as it was.

    """
    if body.lstrip().startswith("#"):
        return _HEX.sub("H", body)
    if belongs:
        return _SUM.sub("D", _DIGEST.sub("sha256:D", _TOKEN.sub(r"\g<head>S", body)))
    return body


def _mask(text: str) -> str:
    """Blank the sha tokens and hashes of the wheel lines, keeping every line terminator.

    Returns:
        the text with only the repinned values replaced.

    """
    return "".join(
        _mask_line(body, belongs=belongs) + ending for body, ending, belongs in _lines(text)
    )


def _shas_in(text: str) -> set[str]:
    """Read the shas the wheel lines of `text` carry.

    Returns:
        each distinct sha, without the `g`.

    """
    found: set[str] = set()
    for body, _ending, belongs in _lines(text):
        if belongs and not body.lstrip().startswith("#"):
            found.update(token.group("sha") for token in _TOKEN.finditer(body))
    return found


def _shas_of(side: Side) -> set[str]:
    """Collect every sha a side of the change holds: its texts and the wheels it has.

    Returns:
        the distinct shas.

    """
    found: set[str] = set()
    for path, text in side.items():
        named = _WHEEL.fullmatch(path)
        if named is not None and text is not None:
            found.add(named.group("sha"))
        elif text is not None and path in TEXT_FILES:
            found |= _shas_in(text)
    return found


def _owned(path: str) -> bool:
    """Say whether a repin owns `path`.

    Returns:
        True for a text file a repin rewrites or a vendored mikemol wheel.

    """
    return path in TEXT_FILES or _WHEEL.fullmatch(path) is not None


def _file_reason(path: str, before: str | None, after: str | None) -> str | None:
    """Judge one text file's change.

    Returns:
        why it is more than a repin, or None.

    """
    if before is None or after is None:
        return f"{path} is added or removed, which a repin does not do"
    if _mask(before) != _mask(after):
        return f"{path} changes more than the vendored sha"
    return None


def _unnamed_wheel(paths: list[str], new: Side) -> str | None:
    """Find an added wheel no new text names; it is part of no repin.

    Returns:
        the reason, naming the wheel; None when every added wheel is named.

    """
    texts = [text for path, text in new.items() if path in TEXT_FILES and text is not None]
    for path in paths:
        added = _WHEEL.fullmatch(path) is not None and new.get(path) is not None
        if added and not any(path.rpartition("/")[2] in text for text in texts):
            return f"{path} is named by no file of the stack"
    return None


def _verdict(old: Side, new: Side) -> tuple[str | None, str]:
    """Judge a change as a repin.

    Returns:
        (the reason it is not one, or None; the one new sha when it is, else empty).

    """
    paths = sorted(set(old) | set(new))
    if not paths:
        return "the stack changes no file", ""
    stray = [path for path in paths if not _owned(path)]
    if stray:
        return f"{', '.join(stray)} is not a repin-owned file", ""
    for path in paths:
        if _WHEEL.fullmatch(path) is None:
            reason = _file_reason(path, old.get(path), new.get(path))
            if reason is not None:
                return reason, ""
    fresh = sorted(_shas_of(new) - _shas_of(old))
    if len(fresh) != 1:
        return f"a repin brings exactly one new sha; this stack brings {len(fresh)}", ""
    unnamed = _unnamed_wheel(paths, new)
    return (unnamed, "") if unnamed is not None else (None, fresh[0])


def admits(old: Side, new: Side) -> str | None:
    """Judge a stack's change as a repin.

    Args:
        old: each changed path's text at HEAD, None when absent there or not text.
        new: each changed path's text in the frozen stack, None when the stack deletes it; a wheel's
            value is not read, only whether it is present.

    Returns:
        None when the stack is a repin; otherwise the reason it is not.

    """
    return _verdict(old, new)[0]


def new_sha(old: Side, new: Side) -> str | None:
    """Name the one sha a repin brings, for the audit trailer.

    Returns:
        the sha when the change is a repin; None when it is not.

    """
    reason, sha = _verdict(old, new)
    return sha if reason is None else None
