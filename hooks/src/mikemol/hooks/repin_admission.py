# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Clause R of the pace input admission: a repin that changes only the vendored sha (W2311).

A repo that vendors mikemol wheels takes a software update as a stack whose every non-queue file
is repin-owned and whose every change is the sha in a wheel's name and hash. The pace guard owes it
no ratchet fall, because it forgives no debt (operator ruling, host line 126887). This module is
the pure judgement over the stack's frozen blobs and nothing else: it reads no file, runs nothing
and writes nothing, so what it says is a function of the two maps it is given.

⚑ A REPIN IS THE SAME TEXT WITH ONE SHA IN IT (W2301 v4, clause R). Each text file is compared with
the sha tokens and the hashes of its mikemol lines masked, so one stray line (a new dependency, a
changed index) leaves the masked texts unequal and refuses the stack. A comment line is masked
whole, since the repo's comments name the sha in prose. The new shas, read from every changed text
file and every added wheel name, must be exactly one value, in either spelling (`+g<sha>` or
`+<sha>`).

⚑ WHAT THIS CANNOT SEE, STATED: the wheel bytes are not read, so a wheel built from a different
source passes if its name carries the sha; and the sha need not be a landed mtools sha. The
vendored checksum row and `mikemol-repin` produce both; the guard checks the shape of the change.

CONSUMED BY: nothing yet; `ratchet_pace` calls it once the admission wiring lands (W2301 part C).
"""

import re
from collections.abc import Mapping

TEXT_FILES = frozenset({"pyproject.toml", "MODULE.bazel", "uv.lock", "vendor/wheels/SHA256SUMS"})
_WHEEL = re.compile(
    r"vendor/wheels/mikemol_[a-z0-9]+-\d+\.\d+\.\d+\+g?(?P<sha>[0-9a-f]{7,40})-py3-none-any\.whl"
)
_TOKEN = re.compile(r"(?<=\d\+)g?(?P<sha>[0-9a-f]{7,40})(?=-py3-none-any|\")")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_SUM = re.compile(r"^[0-9a-f]{64}(?=  \./mikemol_)", re.MULTILINE)
_HEX = re.compile(r"\b[0-9a-f]{7,40}\b")
_VERSION = re.compile(r'^version = "[^"]*"$')


def _mikemol_lines(text: str) -> list[tuple[str, bool]]:
    """Pair each line with whether it belongs to a mikemol wheel.

    A line belongs when it names mikemol, or when it is the `version` line of a lock package whose
    `name` line did.

    Returns:
        (line, belongs) for every line of `text`.

    """
    paired: list[tuple[str, bool]] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("[[package]]"):
            inside = False
        elif line.startswith("name = "):
            inside = "mikemol" in line
        paired.append((line, "mikemol" in line or (inside and _VERSION.match(line) is not None)))
    return paired


def _mask_line(line: str, *, belongs: bool) -> str:
    """Blank the repinned values of one line.

    Returns:
        a comment line with its hex runs blanked, a mikemol line with its sha tokens and hashes
        blanked, any other line as it was.

    """
    if line.lstrip().startswith("#"):
        return _HEX.sub("H", line)
    if belongs:
        return _SUM.sub("D", _DIGEST.sub("sha256:D", _TOKEN.sub("S", line)))
    return line


def _mask(text: str) -> str:
    """Blank the sha tokens and hashes of the mikemol lines, and the hex in comment lines.

    Returns:
        the text with only the repinned values replaced.

    """
    lines = [_mask_line(line, belongs=belongs) for line, belongs in _mikemol_lines(text)]
    return "\n".join(lines)


def _shas(text: str) -> set[str]:
    """Read the shas the mikemol lines of `text` carry.

    Returns:
        each distinct sha, without the `g`.

    """
    found: set[str] = set()
    for line, belongs in _mikemol_lines(text):
        if belongs and not line.lstrip().startswith("#"):
            found.update(token.group("sha") for token in _TOKEN.finditer(line))
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


def admits(old: Mapping[str, str | None], new: Mapping[str, str | None]) -> str | None:
    """Judge a stack's change as a repin.

    Args:
        old: each changed path's text at HEAD, None when absent there or not text.
        new: each changed path's text in the frozen stack, None when the stack deletes it; a wheel's
            value is not read, only whether it is present.

    Returns:
        None when the stack is a repin; otherwise the reason it is not.

    """
    paths = sorted(set(old) | set(new))
    if not paths:
        return "the stack changes no file"
    stray = [path for path in paths if not _owned(path)]
    if stray:
        return f"{', '.join(stray)} is not a repin-owned file"
    shas: set[str] = set()
    for path in paths:
        named = _WHEEL.fullmatch(path)
        if named is None:
            reason = _file_reason(path, old.get(path), new.get(path))
            if reason is not None:
                return reason
            shas |= _shas(new.get(path) or "")
        elif new.get(path) is not None:
            shas.add(named.group("sha"))
    if len(shas) != 1:
        return f"a repin names exactly one sha; this stack names {len(shas)}"
    return None
