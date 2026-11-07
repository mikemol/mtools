# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Clause R of the pace input admission: a repin leaves ONE consistent tree (W2311, W2342).

A repo that vendors mikemol wheels takes a software update as a stack whose every non-queue file
is repin-owned and whose every change is the sha in a wheel's name and hash. The pace guard owes it
no ratchet fall, because it forgives no debt. THE WARRANT IS github-14'S, NOT THE OPERATOR'S: he
extended the pinned-repoint ruling (host line 126887, which spoke of repointing to a pinned
tool) to a stack past the pace, and told the operator so they can overrule it. This module is
the pure judgement over the stack's frozen blobs and nothing else: it reads no file, runs nothing
and writes nothing, so what it says is a function of the maps it is given.

⚑ ONE INVARIANT OVER THE TREE AFTER THE STACK, NOT A CLAUSE PER CASE (github-14's ruling on the
3f44ba69 review, after three rounds of patches each found the next case). The pin texts are
pyproject.toml, MODULE.bazel, uv.lock and vendor/wheels/SHA256SUMS: NEVER the README, whose prose
may name any wheel. Read as they stand once the stack has landed (the stack's texts over HEAD's):

  1. EVERY MENTION OF A DIST AGREES: all pin texts that name a dist name it at the same version and
     sha, so a pin moved in one text and forgotten in another is a disagreement;
  2. EVERY WHEEL NAMED EXISTS: a wheel file a pin text names is among HEAD's wheels or added by the
     stack, and not deleted by it; an existing wheel path is never changed (the blob is compared);
     every wheel the stack adds is named by a pin text;
  3. EVERY CHANGED PIN MOVED TO THE ONE SAME SHA, judged per changed token, and at least one moved;
  4. ONLY REPIN-OWNED FILES CHANGE, LINE BY LINE, terminators kept: a line differs only by the sha
     token of a wheel it names and that wheel's hashes (a digest that changed on a row whose sha
     did not move is a change beyond the sha).

Anything a repin cannot produce fails one of these, which is why the per-case branches (a wheel per
moved line, a deleted wheel named by an untouched text, a sha no wheel carries) are gone: each is
one of the four. A catch-up to a wheel HEAD already holds passes because (2) is about existence.

⚑ WHAT THIS CANNOT SEE, STATED: a NEW wheel's bytes are not read, so a wheel built from a different
source passes if its name carries the new sha; the sha need not be a landed mtools sha; a pin text
that does not name a dist is simply silent about it (the relation is "every text that names a dist
names it the same", not "every text names every dist"); and the README is not read as a pin.

⚑ A SHAPE RULE OUTSIDE THE ROW TABLE, BY DESIGN: the table admits one reviewed change; clause R
admits a software update only, which the design (.claude/design/W2301-pace-input-admission.md, the
"how a row reaches nemik" section) names as the one route that forgives no debt and needs no
per-repin row. It leaves an audit mark: the landing writes `Admission: <repo>/repin-<sha>`.

CONSUMED BY: `ratchet_pace` at submit and at landing (W2329).
"""

import re
from collections.abc import Mapping

Side = Mapping[str, str | None]
README = "vendor/wheels/README.md"
PIN_TEXTS = frozenset({"pyproject.toml", "MODULE.bazel", "uv.lock", "vendor/wheels/SHA256SUMS"})
TEXT_FILES = PIN_TEXTS | {README}
_WHEEL = re.compile(
    r"vendor/wheels/mikemol_[a-z0-9_]+-\d+\.\d+\.\d+\+g?(?P<sha>[0-9a-f]{7,40})-py3-none-any\.whl"
)
_TOKEN = re.compile(r"(?P<head>\d+\.\d+\.\d+\+)g?(?P<sha>[0-9a-f]{7,40})(?=-py3-none-any|\")")
_MENTION = re.compile(
    r"mikemol_(?P<dist>[a-z0-9_]+)-(?P<ver>\d+\.\d+\.\d+)\+g?(?P<sha>[0-9a-f]{7,40})"
    r"-py3-none-any\.whl"
)
_LOCK_VERSION = re.compile(r'^version = "(?P<ver>\d+\.\d+\.\d+)\+g?(?P<sha>[0-9a-f]{7,40})"$')
_LOCK_NAME = re.compile(r'^name = "mikemol-(?P<dist>[a-z0-9-]+)"$')
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_SUM = re.compile(r"^[0-9a-f]{64}(?=  \./mikemol_)")
_HEX = re.compile(r"\b[0-9a-f]{7,40}\b")
_VERSION = re.compile(r'^version = "[^"]*"$')
_TERMINATORS = "\r\n"
_WHEEL_DIR = "vendor/wheels/"

type Pins = dict[str, set[tuple[str, str]]]
"""dist -> the (version, sha) pairs the pin texts name it at."""


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


def _file_verdict(path: str, before: str | None, after: str | None, moved: set[str]) -> str | None:
    """Judge one text file's change line by line (invariant 4), noting the shas it moved to (3).

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
            moved |= to
    return None


def _owned(path: str) -> bool:
    """Say whether a repin owns `path`.

    Returns:
        True for a text file a repin rewrites or a vendored mikemol wheel.

    """
    return path in TEXT_FILES or _WHEEL.fullmatch(path) is not None


def _mentions(text: str, pins: Pins, files: set[str]) -> None:
    """Add what a pin text says about each dist to `pins` and `files`, comment lines left out."""
    dist = ""
    for body, _ending, _belongs in _lines(text):
        if body.lstrip().startswith("#"):
            continue
        named = _LOCK_NAME.match(body)
        if body.startswith("name = "):
            dist = str(named.group("dist")).replace("-", "_") if named else ""
        version = _LOCK_VERSION.match(body)
        if version is not None and dist:
            pins.setdefault(dist, set()).add((str(version.group("ver")), str(version.group("sha"))))
        for found in _MENTION.finditer(body):
            seen = (str(found.group("ver")), str(found.group("sha")))
            pins.setdefault(str(found.group("dist")), set()).add(seen)
            files.add(str(found.group(0)))


def _disagreement(after: Side) -> tuple[str | None, set[str]]:
    """Judge invariant 1 over the pin texts as they stand after the stack.

    Returns:
        (why two texts name one dist differently, or None; every wheel file the texts name).

    """
    pins: Pins = {}
    files: set[str] = set()
    for path, text in sorted(after.items()):
        if path in PIN_TEXTS and text:
            _mentions(text, pins, files)
    for dist, seen in sorted(pins.items()):
        if len(seen) != 1:
            return f"the pin texts name {dist} at {len(seen)} different versions or shas", files
    return None, files


def _wheels_reason(old: Side, new: Side, wheels: Mapping[str, str], named: set[str]) -> str | None:
    """Judge invariant 2: the wheels the texts name exist after the stack, and none is altered.

    Returns:
        why a wheel makes the tree no repin's; None when every named wheel is there.

    """
    present = {path for path in wheels if new.get(path, "kept") is not None}
    present |= {path for path, blob in new.items() if _WHEEL.fullmatch(path) and blob}
    for path in sorted(set(old) | set(new)):
        if _WHEEL.fullmatch(path) is None:
            continue
        if old.get(path) is not None and new.get(path) is not None and old[path] != new[path]:
            return f"{path} is an existing wheel with other bytes"
        added = old.get(path) is None and new.get(path) is not None
        if added and path.removeprefix(_WHEEL_DIR) not in named:
            return f"{path} is named by no file of the stack"
    for file in sorted(named):
        if f"{_WHEEL_DIR}{file}" not in present:
            return f"a pin text names {file}, which the tree does not hold after the stack"
    return None


def _moved_pins(old: Side, new: Side) -> tuple[str | None, set[str]]:
    """Judge every changed text line by line and collect the shas its PIN texts moved to.

    ⚑ ONLY A PIN TEXT'S TOKENS COUNT AS A MOVE (the ebfd1f6e review, B1): the README is owned, so
    its lines may carry a changed sha, but its prose names no pin, and a stack that moves only a
    README token moved no pin at all.

    Returns:
        (why a text is more than a repin, or None; the shas the pin texts moved to).

    """
    moved: set[str] = set()
    for path in sorted(set(old) | set(new)):
        if _WHEEL.fullmatch(path) is not None:
            continue
        into = moved if path in PIN_TEXTS else set()
        reason = _file_verdict(path, old.get(path), new.get(path), into)
        if reason is not None:
            return reason, set()
    return None, moved


def _carried(sha: str, named: set[str]) -> bool:
    """Say whether a wheel file a pin text names carries `sha`.

    Returns:
        True when some named wheel file is at that sha.

    """
    found = (_MENTION.finditer(name) for name in named)
    return any(str(hit.group("sha")) == sha for hits in found for hit in hits)


def _verdict(old: Side, new: Side, held: Side, wheels: Mapping[str, str]) -> tuple[str | None, str]:
    """Judge a change as a repin.

    Returns:
        (the reason it is not one, or None; the one sha every changed pin moved to, else empty).

    """
    paths = sorted(set(old) | set(new))
    if not paths:
        return "the stack changes no file", ""
    stray = [path for path in paths if not _owned(path)]
    if stray:
        return f"{', '.join(stray)} is not a repin-owned file", ""
    reason, moved = _moved_pins(old, new)
    if reason is None and len(moved) != 1:
        reason = f"a repin moves every pin to one sha; this stack moves them to {len(moved)}"
    if reason is not None:
        return reason, ""
    disagreement, named = _disagreement({**held, **new})
    sha = next(iter(moved))
    reason = disagreement or _wheels_reason(old, new, wheels, named)
    if reason is None and not _carried(sha, named):
        reason = f"no wheel a pin text names carries the new sha {sha}"
    return (reason, "") if reason is not None else (None, sha)


def admits(
    old: Side, new: Side, held: Side | None = None, wheels: Mapping[str, str] | None = None
) -> str | None:
    """Judge a stack's change as a repin.

    Args:
        old: each changed path's text at HEAD, None when absent there; a wheel's value is its blob
            id at HEAD, not its text.
        new: each changed path's text in the frozen stack, None when the stack deletes it; a wheel's
            value is its blob id, not its text.
        held: the pin texts the stack does NOT change, as HEAD holds them.
        wheels: every wheel path HEAD holds, with its blob id, changed by the stack or not.

    Returns:
        None when the stack is a repin; otherwise the reason it is not.

    """
    return _verdict(old, new, held or {}, wheels or {})[0]


def new_sha(
    old: Side, new: Side, held: Side | None = None, wheels: Mapping[str, str] | None = None
) -> str | None:
    """Name the one sha every changed pin of a repin moved to, for the audit trailer.

    Returns:
        the sha when the change is a repin; None when it is not.

    """
    reason, sha = _verdict(old, new, held or {}, wheels or {})
    return sha if reason is None else None
