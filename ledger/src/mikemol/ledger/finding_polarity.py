# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse a witness that would be BORN reporting the opposite of its own finding.

Moved from substrate (N-a row 6).

⚑⚑⚑ THE DISCRIMINATOR IS EXECUTION, NOT INSPECTION, AND IT IS FREE AT FILING TIME. Nothing in a
command's TEXT separates a CENSUS (reports a value, exits 0 on zero rows as on many) from a
PREDICATE (reports an exit code), so a static check is impossible in principle. But the witness
will run this command on every read anyway; running it ONCE MORE, now, answers the only question
that matters: does it exit the way this kind requires TODAY.

⚑⚑ THE MEASURED CASE: a `refuses:` command returned 0 sites with exit 0, and the freshly-filed
witness immediately reported "the refusal is GONE" against a finding that was true.

⚑ WHAT THIS DOES NOT DETECT IS CENSUS-NESS: a census whose zero result happens to exit non-zero
still registers. What it guarantees is that no witness is born reporting the opposite of its own
finding — the shape that actually cost a false verdict.

⚑⚑ THE `mode:` ARM IS DECIDABLE because the mode reader returns 0 on EXACTLY ONE path, the
DOCUMENTED branch; "still dispatches undocumented" and "the mode is GONE" both return 1.

⚑ THE PROBE RUNS WHERE ITS CALLER SAYS (`cwd`), as every witness does — see `finding_kinds`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.ledger import finding_kinds

if TYPE_CHECKING:
    from pathlib import Path

# The kinds whose polarity a probe can decide. ⚑ `standing` and `unwitnessed` are absent BY
# CONSTRUCTION: neither runs a command, so neither has a polarity to be born wrong about.
PROBED: tuple[str, ...] = ("refuses", "selftest", "mode")


def _did_not_run(cmd: list[str], out: str) -> str:
    """Return the refusal for a command that could not start.

    Returns:
        the refusal.

    """
    return (
        "the command for this witness DID NOT RUN, so it would report 2 forever while looking "
        f"mechanical — an absent instrument is not evidence:\n    {' '.join(cmd)}\n    {out[:200]}"
    )


def _refuses_is_gone(cmd: list[str], out: str) -> str:
    """Return the refusal for a `refuses:` command that currently exits 0.

    ⚑ TWO CAUSES, AND THEY NEED DIFFERENT ANSWERS — so the refusal names both rather than
    asserting one.

    Returns:
        the refusal.

    """
    return (
        "this `refuses:` command EXITS 0 RIGHT NOW, so the witness would be born reporting *the "
        f"refusal is GONE* about a finding you are filing as true:\n    {' '.join(cmd)}\n"
        "⚑ TWO CAUSES, AND THEY NEED DIFFERENT ANSWERS. (a) The refusal genuinely is not "
        "installed — then the finding is OPEN and `refuses:` is right but premature. (b) This is "
        "a CENSUS, not a predicate: it reports a VALUE and exits 0 whether it finds zero rows or "
        "many, so no exit code can carry the claim; its honest kind is `unwitnessed`, naming the "
        "census value as the discriminating quantity no registered kind reads.\n"
        f"    last output: {finding_kinds.evidence(out)}"
    )


def _selftest_is_open(cmd: list[str], code: int, out: str) -> str:
    """Return the refusal for a `selftest:` command that currently fails.

    Returns:
        the refusal.

    """
    return (
        f"this `selftest:` command EXITS {code} RIGHT NOW, so the witness would be born OPEN — "
        "file the finding only once the mechanism it asserts actually holds, or use "
        f"`unwitnessed` if no command can carry the claim:\n    {' '.join(cmd)}\n"
        f"    {finding_kinds.evidence(out)}"
    )


def _mode_is_documented(cmd: list[str], out: str) -> str:
    """Return the refusal for a `mode:` witness that currently reports DOCUMENTED.

    ⚑ AND THE NEAREST HONEST KIND IS NAMED: a flag documented AS A REDIRECT and not dispatched is
    indistinguishable from documented-as-a-mode by any predicate, which is `unwitnessed`.

    Returns:
        the refusal.

    """
    return (
        "this `mode:` witness reports DOCUMENTED RIGHT NOW, so it would be born asserting the "
        f"opposite of a finding filed because the mode is UNDOCUMENTED:\n    {' '.join(cmd)}\n"
        "⚑ THE READER HAS EXACTLY ONE ZERO-PATH, so this is unambiguous: both *dispatches "
        "undocumented* and *the mode is GONE* report 1. Exit 0 means the tool declares it.\n"
        "⚑ IF THE MODE IS DOCUMENTED IN A WAY THE CLAIM DISPUTES — a redirect, a prose mention, a "
        "usage line for a flag that no longer dispatches — no predicate separates that from an "
        "ordinary declaration, and `unwitnessed` is the honest kind.\n"
        f"    last output: {finding_kinds.evidence(out)}"
    )


def probe(cmd: list[str], kind: str, *, cwd: Path) -> str | None:
    """Return None if `cmd` already exits the way `kind` requires, else a REFUSAL string.

    ⚑ A COMMAND THAT CANNOT RUN IS REFUSED TOO, NEVER WAVED THROUGH: registering it files a
    witness that reports UNRUNNABLE forever while looking mechanical.

    Returns:
        None when the registration is sound; the refusal otherwise.

    """
    if kind not in PROBED:
        return None
    code, out = finding_kinds.run(*cmd, cwd=cwd)
    if code is None:
        return _did_not_run(cmd, out)
    if kind == "refuses" and code == 0:
        return _refuses_is_gone(cmd, out)
    if kind == "selftest" and code != 0:
        return _selftest_is_open(cmd, code, out)
    if kind == "mode" and code == 0:
        return _mode_is_documented(cmd, out)
    return None
