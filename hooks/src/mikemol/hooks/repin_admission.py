# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Clause R of the pace input admission: a repin moves every pin to ONE vendored sha (W2311, W2335).

A repo that vendors mikemol wheels takes a software update as a stack whose every non-queue file
is repin-owned and whose every change is the sha in a wheel's name and hash. The pace guard owes it
no ratchet fall, because it forgives no debt. THE WARRANT IS github-14'S, NOT THE OPERATOR'S: he
extended the pinned-repoint ruling (host line 126887, which spoke of repointing to a pinned
tool) to a stack past the pace, and told the operator so they can overrule it. This module is
the pure judgement over the stack's frozen blobs and nothing else: it reads no file, runs nothing
and writes nothing, so what it says is a function of the maps it is given.

⚑ A REPIN IS THE SAME TEXT WITH ITS PINS MOVED TO ONE SHA (W2301 v4, clause R; the a92d93a1 and
04a83d9e reviews). Each text file is compared LINE BY LINE, line terminators kept: a line may differ
only by the sha token of a wheel it names, with that wheel's hashes following it. So one stray line,
a dropped trailing newline, a CRLF, or a digest that changed on a row whose sha did not move all
refuse the stack. Every sha a changed pin moves TO must be the same one, judged per pin (a catch-up
to a sha another pin already holds passes, two pins moving to two shas do not), and a stack that
moves no pin is not a repin.

⚑ WHEELS (the 04a83d9e review, B1 and B2). A wheel is read by its blob: an existing wheel path with
other bytes is no repin. EVERY wheel a moved line names must be ADDED by the stack, so one arriving
wheel cannot stand for two moved pins, and every added wheel must carry the new sha and be named by
a text. A wheel the stack deletes must be named by NO text after the stack: the stack's own new
texts and the repin-owned texts it leaves untouched at HEAD (`held`) are both read, so a stack that
forgot a text cannot leave the tree pinning a deleted wheel.

⚑ WHAT THIS CANNOT SEE, STATED: a NEW wheel's bytes are not read, so a wheel built from a different
source passes if its name carries the new sha; the sha need not be a landed mtools sha; and a line
that names no wheel (a lock `version` line) is held to its sha moving but not to a wheel of its own.
The vendored checksum row and `mikemol-repin` produce all of that; the guard checks the shape.

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
_NAME = re.compile(r"mikemol_[a-z0-9]+-\d+\.\d+\.\d+\+g?[0-9a-f]{7,40}-py3-none-any\.whl")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_SUM = re.compile(r"^[0-9a-f]{64}(?=  \./mikemol_)")
_HEX = re.compile(r"\b[0-9a-f]{7,40}\b")
_VERSION = re.compile(r'^version = "[^"]*"$')
_TERMINATORS = "\r\n"


class _Moved:
    """What the changed pins of the stack's texts moved to: shas, and the wheels they now name."""

    def __init__(self) -> None:
        """Start with nothing moved."""
        self.shas: set[str] = set()
        self.names: set[str] = set()


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


def _moved_to(before: str, after: str) -> set[str]:
    """Collect the shas the sha tokens of a wheel line changed TO.

    Returns:
        the new sha of each token that differs, without the `g`; empty when none moved or when the
        two lines hold a different number of tokens (a refusal, not an error).

    """
    old, new = list(_TOKEN.finditer(before)), list(_TOKEN.finditer(after))
    if len(old) != len(new):
        return set()
    return {
        str(b.group("sha"))
        for a, b in zip(old, new, strict=True)
        if str(a.group("sha")) != str(b.group("sha"))
    }


def _file_verdict(path: str, before: str | None, after: str | None, moved: _Moved) -> str | None:
    """Judge one text file's change, line by line, and note what its pins moved to.

    Returns:
        why it is more than a repin, or None.

    """
    if before is None or after is None:
        return f"{path} is added or removed, which a repin does not do"
    more = f"{path} changes more than the vendored sha"
    old, new = _lines(before), _lines(after)
    if len(old) != len(new):
        return more
    for (b0, e0, w0), (b1, e1, w1) in zip(old, new, strict=True):
        if (b0, e0, w0) == (b1, e1, w1):
            continue
        if e0 != e1 or w0 != w1 or _mask_line(b0, belongs=w0) != _mask_line(b1, belongs=w1):
            return more
        if not b0.lstrip().startswith("#"):
            to = _moved_to(b0, b1)
            if not to:
                return f"{path} changes a digest on a pin whose sha did not move"
            moved.shas |= to
            moved.names.update(str(found.group(0)) for found in _NAME.finditer(b1))
    return None


def _owned(path: str) -> bool:
    """Say whether a repin owns `path`.

    Returns:
        True for a text file a repin rewrites or a vendored mikemol wheel.

    """
    return path in TEXT_FILES or _WHEEL.fullmatch(path) is not None


def _wheel_reason(old: Side, new: Side, held: Side, moved: _Moved, sha: str) -> str | None:
    """Judge the wheels of a change against what the pins moved to.

    Returns:
        why a wheel makes it no repin; None when the wheels are the repin's.

    """
    texts = [text for path, text in {**held, **new}.items() if path in TEXT_FILES and text]
    added: set[str] = set()
    for path in sorted(set(old) | set(new)):
        named = _WHEEL.fullmatch(path)
        if named is None:
            continue
        name = path.rpartition("/")[2]
        if new.get(path) is None:
            if any(name in text for text in texts):
                return f"{path} is deleted but a text still names it"
        elif old.get(path) is not None:
            if old[path] != new[path]:
                return f"{path} is an existing wheel with other bytes"
        elif str(named.group("sha")) != sha:
            return f"{path} carries a sha other than the one the pins moved to"
        elif any(name in text for text in texts):
            added.add(name)
        else:
            return f"{path} is named by no file of the stack"
    missing = sorted(moved.names - added)
    if missing:
        return f"a moved pin names {missing[0]}, which the stack does not add"
    return None if added else f"no wheel of the stack carries the new sha {sha}"


def _verdict(old: Side, new: Side, held: Side) -> tuple[str | None, str]:
    """Judge a change as a repin.

    Returns:
        (the reason it is not one, or None; the one sha every pin moved to when it is, else empty).

    """
    paths = sorted(set(old) | set(new))
    if not paths:
        return "the stack changes no file", ""
    stray = [path for path in paths if not _owned(path)]
    if stray:
        return f"{', '.join(stray)} is not a repin-owned file", ""
    moved = _Moved()
    for path in paths:
        if _WHEEL.fullmatch(path) is None:
            reason = _file_verdict(path, old.get(path), new.get(path), moved)
            if reason is not None:
                return reason, ""
    if len(moved.shas) != 1:
        return f"a repin moves every pin to one sha; this stack moves them to {len(moved.shas)}", ""
    (sha,) = moved.shas
    reason = _wheel_reason(old, new, held, moved, sha)
    return (reason, "") if reason is not None else (None, sha)


def admits(old: Side, new: Side, held: Side | None = None) -> str | None:
    """Judge a stack's change as a repin.

    Args:
        old: each changed path's text at HEAD, None when absent there; a wheel's value is its blob
            id at HEAD, not its text.
        new: each changed path's text in the frozen stack, None when the stack deletes it; a wheel's
            value is its blob id, not its text.
        held: the repin-owned texts the stack does NOT change, as HEAD holds them; a deleted wheel
            must be named by none of them either.

    Returns:
        None when the stack is a repin; otherwise the reason it is not.

    """
    return _verdict(old, new, held or {})[0]


def new_sha(old: Side, new: Side, held: Side | None = None) -> str | None:
    """Name the one sha every pin of a repin moved to, for the audit trailer.

    Returns:
        the sha when the change is a repin; None when it is not.

    """
    reason, sha = _verdict(old, new, held or {})
    return sha if reason is None else None
