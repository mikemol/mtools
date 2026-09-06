# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A paydown-only ratchet over a baseline SET — never a count.

⚑⚑⚑ THE BASELINE IS A SET OF KEYS, AND THAT IS THE WHOLE DESIGN. A count-based ratchet
passes the substitution attack: pay one key down, add another, the cardinality is unchanged
and the gate reports green while the membership churned entirely. The origin measured this
as "six-vs-six different sets". Under set membership the added key is REFUSED even at
constant cardinality, and `test_a_substitution_at_constant_size_is_refused` is the arm that
proves this implementation is the right kind rather than the wrong kind wearing the name.

⚑⚑ A MOVE IS NEITHER PAYDOWN NOR GROWTH, and collapsing the three is what made an earlier
cut of the origin complex enough to trip a complexity rule. A relocated key means the debt
still exists (so it is not paydown) and the total did not rise (so it is not growth). A run
can relocate AND pay down AND grow at once, and each means something different to a reader.

⚑⚑ `write` IS A REQUIRED ARGUMENT, NOT AN AMBIENT ENVIRONMENT VARIABLE. The origin arms
its writes with `SUBSTRATE_RATCHET_WRITE=1`, which it records as a retrofit scar. An
ambient switch that arms a mutation is the same shape as a hook reporting itself armed
while refusing nothing — and under a build system a cached write is a SKIPPED write, so the
mutation silently does not happen. Here the caller says so in the call.

⚑ THE BIRTH MOVE IS `--init-absent`: ABSENT becomes EMPTY, a zero-byte file. It is the
difference between a gate that refuses and a gate that is silently green over nothing,
because ABSENT reads green while asserting nothing. At a repository whose debt is already
zero, EMPTY is not a formality — it is the strongest state the model has, where every
future key is new and therefore refused.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.ratchet.state import BaselineState

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


# ⚑⚑⚑ A MOVE IS NEITHER GROWTH NOR PAYDOWN, AND CONFLATING IT WITH GROWTH BLOCKS THE DRAIN THAT
# EARNS THE PAYDOWN. A rename is content-preserving but KEY-CHANGING: the old key retires and a new
# one is minted for a byte-identical finding. A set ratchet sees "a key appeared" and refuses — and
# because it returns on `added` BEFORE reaching the paydown branch, the churn also stops real
# paydown from recording. So the act of reorganising a tree makes every gate over it read as
# growth, and the credit that reorganisation earns cannot be banked.
#
# MEASURED HERE, one `git mv` of `lint.py` -> `linting.py`, no content change:
#
#     1 new key(s) REFUSED:        + src/mikemol/mdstruct/linting.py:docstring-missing-returns
#     1 key(s) paid down:          - src/mikemol/mdstruct/lint.py:docstring-missing-returns
#
# ⚑⚑ THE IDENTITY IS EVERY FIELD EXCEPT THE PATH. That is the design a peer arrived at over a
# per-gate key schema, where which field holds the path differs by gate and one census even emits
# `name::relpath` with the path SECOND. mtools' grammar is fixed — `path:rule` — so the identity is
# just the rule, and the schema machinery that peer needs has no counterpart here. The CONCEPT
# transfers; the modules would have been a solution to a problem this repository does not have.
def _identity(key: str) -> str:
    """Return the part of a key that survives a move: everything but the path.

    ⚑ `rsplit`, NOT `split` — a path may contain colons and the rule never does, so the LAST field
    is the identity and the rest is the path. Splitting from the left would take a directory as
    the identity for any path carrying one.
    """
    _path, _, rule = key.rpartition(":")
    return rule or key


@dataclass(frozen=True, slots=True)
class Diff:
    """One census against its baseline, partitioned into three independent verdicts."""

    added: frozenset[str]
    paid: frozenset[str]
    moved: frozenset[tuple[str, str]] = frozenset()

    @property
    def grew(self) -> bool:
        """Report whether any key is present now and absent from the baseline."""
        return bool(self.added)


def read_baseline(path: Path) -> tuple[BaselineState, frozenset[str]]:
    """Return the baseline's state and its key set.

    ⚑⚑ ABSENT AND EMPTY ARE DIFFERENT FACTS AND THE CALLER MUST KEEP THEM APART. Both yield
    an empty key set, so a caller reading only the set cannot tell "no baseline was ever
    recorded" from "a baseline was recorded and holds nothing" — and those are opposites: the
    first is a gate asserting nothing, the second is zero tolerance.

    ⚑ AN UNREADABLE FILE IS `UNREAD`, NOT `EMPTY`. A decode error is a fact about the READER,
    not a verdict about the gate, and reporting it as an empty baseline would silently widen
    what the ratchet permits to everything.
    """
    if not path.is_file():
        return BaselineState.ABSENT, frozenset()
    try:
        body = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return BaselineState.UNREAD, frozenset()
    keys = frozenset(line.strip() for line in body.splitlines() if line.strip())
    return (BaselineState.EMPTY if not keys else BaselineState.OK), keys


def partition(current: Iterable[str], baseline: Iterable[str]) -> Diff:
    """Split the census against its baseline into growth and paydown."""
    cur, base = frozenset(current), frozenset(baseline)
    added, paid = cur - base, base - cur

    # ⚑ A KEY IS A MOVE WHEN A RETIRED KEY SHARES ITS IDENTITY. Pairing is by identity alone, so a
    # finding that relocates is neither new debt nor discharged debt — the debt still exists and
    # the total did not rise.
    paid_by_identity: dict[str, str] = {_identity(k): k for k in paid}
    moved = frozenset(
        (paid_by_identity[_identity(k)], k) for k in added if _identity(k) in paid_by_identity)
    relocated_from = {src for src, _dst in moved}
    relocated_to = {dst for _src, dst in moved}
    return Diff(added=frozenset(added - relocated_to),
                paid=frozenset(paid - relocated_from),
                moved=moved)


def write_baseline(path: Path, keys: Iterable[str], *, write: bool) -> None:
    """Record `keys` as the baseline, and CONFIRM WHAT LANDED rather than what was intended.

    ⚑⚑ `write` IS KEYWORD-ONLY AND REQUIRED. There is no environment variable and no
    default: a mutation nobody asked for in the call is a mutation nobody can find in the
    call. Passing `write=False` is a no-op rather than an error, so a dry run is expressible
    without a second code path.

    ⚑ THE READBACK IS NOT A FORMALITY. A write that succeeds and a write that lands are
    different claims, and a baseline that did not land reads as ABSENT on the next run —
    which reads green while asserting nothing.
    """
    if not write:
        return
    wanted = frozenset(keys)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{key}\n" for key in sorted(wanted)), encoding="utf-8")
    _state, landed = read_baseline(path)
    if landed != wanted:
        msg = (f"baseline at {path} did not round-trip: "
               f"{len(wanted)} keys written, {len(landed)} read back")
        raise OSError(msg)


def ratchet(current: Iterable[str], path: Path, *, write: bool) -> tuple[int, list[str]]:
    """Run the paydown-only ratchet. Return (exit code, report lines).

    0 = pass, 1 = the debt grew or the baseline cannot be trusted.

    ⚑⚑ ABSENT EXITS 1. A missing baseline is a DEFECT, not a clean slate — the gate has
    nothing to check against and would otherwise report green over nothing, which is the
    precise failure this machinery exists to refuse. The birth move is explicit
    (`--init-absent`), because a baseline that creates itself on first run grandfathers
    whatever happened to be present at that moment, and nobody chose that set.

    ⚑ PAYDOWN LOWERS THE BASELINE PERMANENTLY. A paid-down key cannot return without the
    gate refusing, so a repair cannot silently regress. That is what makes the ratchet a
    ratchet rather than a report.
    """
    state, base = read_baseline(path)
    if state.is_defect:
        return 1, [
            f"baseline {state}: {path}",
            ("  a gate with no baseline reports green over nothing — "
             "run with --init-absent to record the zero-tolerance floor"),
        ]
    if state is BaselineState.UNREAD:
        return 1, [f"baseline {state}: {path} could not be read",
                   "  this is a fact about the reader, not a verdict about the gate"]
    diff = partition(current, base)
    lines: list[str] = []
    # ⚑ MOVES ARE REPORTED, NEVER SILENT. A relocation that vanished from the transcript would be
    # indistinguishable from nothing having happened — and the whole reason to separate it from
    # growth is that a reader needs to see the debt moved rather than infer it from two numbers
    # that cancelled.
    if diff.moved:
        lines.append(f"{len(diff.moved)} key(s) MOVED (same finding, new path):")
        lines.extend(f"  ~ {src} -> {dst}" for src, dst in sorted(diff.moved))
    if diff.added:
        lines.append(f"{len(diff.added)} new key(s) REFUSED:")
        lines.extend(f"  + {key}" for key in sorted(diff.added))
    if diff.paid:
        verb = "LOWERED" if write and not diff.added else "would lower"
        lines.append(f"{len(diff.paid)} key(s) paid down — baseline {verb}:")
        lines.extend(f"  - {key}" for key in sorted(diff.paid))
    if diff.added:
        return 1, lines
    # ⚑ THE BASELINE IS LOWERED ONLY WHEN NOTHING GREW. Lowering alongside growth would
    # bank the paydown and lose the refusal in the same run, so a mixed run reports both
    # and writes neither.
    # ⚑⚑ A MOVE LOWERS THE BASELINE TOO, and that is the point of separating it. The debt did not
    # change; its address did. Leaving the baseline unwritten would make the next run refuse the
    # same relocation again — the ratchet would block a reorganisation permanently rather than
    # once, which is the defect this whole distinction exists to remove.
    if diff.paid or diff.moved:
        write_baseline(path, current, write=write)
    return 0, lines or [f"baseline {state}: {len(base)} key(s), unchanged"]
