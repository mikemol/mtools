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
from pathlib import PurePosixPath
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
def _plausible_move(old_path: str, new_path: str) -> bool:
    """Report whether `new_path` is a plausible destination for `old_path`.

    ⚑⚑ A SHARED IDENTITY IS NOT EVIDENCE OF A MOVE — that is the false absolution. The move shapes
    this evidences are path-LOCAL, which is a peer's design and the half a count asymmetry cannot
    supply on its own:

        a module split into its own directory: "src/x.py" becomes "src/x/leaf.py"
        a module renamed within its directory: "pkg/x.py" becomes "pkg/y.py"

    ⚑ ANYTHING ELSE IS NOT A MOVE THIS CAN EVIDENCE, so it is not churn. Widening the predicate to
    "some file with this rule moved" launders every new violation carrying that rule — measured in
    this repository's own first cut, where a retirement of "a.py" absolved an unrelated "z.py".

    Returns:
        whether `new_path` is a plausible destination for `old_path`.

    """
    if old_path == new_path:
        return False
    stem = old_path.removesuffix(".py")
    if new_path.startswith(stem + "/"):
        return True
    return PurePosixPath(old_path).parent == PurePosixPath(new_path).parent


def _identity(key: str) -> str:
    """Return the part of a key that survives a move: everything but the path.

    ⚑ `rsplit`, NOT `split` — a path may contain colons and the rule never does, so the LAST field
    is the identity and the rest is the path. Splitting from the left would take a directory as
    the identity for any path carrying one.

    Returns:
        part of a key that survives a move: everything but the path.

    """
    _path, _, rule = key.rpartition(":")
    return rule or key


@dataclass(frozen=True, slots=True)
class Diff:
    """One census against its baseline, partitioned into three independent verdicts."""

    added: frozenset[str]
    paid: frozenset[str]
    moved: frozenset[tuple[str, str]] = frozenset()
    suspect: frozenset[str] = frozenset()

    @property
    def grew(self) -> bool:
        """Report whether any key is present now and absent from the baseline.

        ⚑ SUSPECT KEYS ARE INCLUDED IN `added` AND THEREFORE COUNT AS GROWTH. `suspect` says
        WHY a key was refused, never WHETHER — a state that softened the verdict would be the
        `strict=`-defaulting-off defect wearing a different name.
        """
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

    Returns:
        baseline's state and its key set.

    """
    if not path.is_file():
        return BaselineState.ABSENT, frozenset()
    try:
        body = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return BaselineState.UNREAD, frozenset()
    # ⚑⚑⚑ A `#` LINE IS A COMMENT, NOT A KEY, AND THIS READER TREATED IT AS ONE. Measured: the
    # domain witness appends a nonce to this file as a `#` comment — deliberately, so that the
    # digest moves while the census does not — and the gate REFUSED, reporting the nonce as a
    # paid-down key and an unrelated finding as new. ⚑ The witness's own comment claimed the nonce
    # was "outside the census, so the verdict is unchanged". It was not, and only running both
    # instruments in one gate showed it: each was correct alone.
    #
    # ⚑⚑ THE DIRECTION MATTERS. A comment read as a key inflates the baseline, which is the SAFE
    # direction for a paydown-only ratchet — it never absolves real debt. But it makes the file
    # un-annotatable, and a baseline nobody may explain is one whose entries lose their reasons.
    keys = frozenset(
        stripped for line in body.splitlines()
        if (stripped := line.strip()) and not stripped.startswith("#"))
    return (BaselineState.EMPTY if not keys else BaselineState.OK), keys


def partition(current: Iterable[str], baseline: Iterable[str]) -> Diff:
    """Split the census against its baseline into growth and paydown.

    Returns:
        the the census against its baseline into growth and paydown.

    """
    cur, base = frozenset(current), frozenset(baseline)
    added, paid = cur - base, base - cur

    # ⚑⚑⚑ IDENTITY ALONE IS NOT ENOUGH, AND ASSUMING IT WAS IS A FALSE-ABSOLUTION BUG. A peer hit
    # this on its first live run and this repository shipped the same defect an hour after reading
    # that warning without reading the module that carried it. MEASURED in the committed code:
    #
    #     a baseline of one key at "a.py", a census of two at "b.py" and "z.py", the same rule
    #     on all three: TWO moves recognised, ZERO additions, grew = False, THE GATE PASSED.
    #
    # One retired key absolved TWO new ones: a.py moved to b.py, and a genuinely-new violation at
    # an unrelated z.py was laundered as churn. A file split into ten would absolve nine real
    # findings. That is a stale green inside the machinery whose purpose is refusing stale greens.
    #
    # ⚑⚑ THE BOUND IS A COUNT ASYMMETRY, which is the peer's own answer: a move is ONE-TO-ONE. A
    # one-old-to-many-new fan-out is not churn, it is churn plus growth, and it must be reported as
    # SUSPECT rather than absolved. Only an unambiguous pairing — exactly one retired key and
    # exactly one added key sharing an identity — is a move.
    #
    # ⚑ THE HONEST LIMITATION, CARRIED RATHER THAN QUIETLY DROPPED: if a finding relocates AND a
    # genuinely-new violation of the same rule appears elsewhere in the same run, the pairing is
    # ambiguous and BOTH are refused as growth. That is the safe direction — a domain too wide
    # fails loudly, a domain too narrow serves a stale green.
    added_by_identity: dict[str, list[str]] = {}
    for key in added:
        added_by_identity.setdefault(_identity(key), []).append(key)
    paid_by_identity: dict[str, list[str]] = {}
    for key in paid:
        paid_by_identity.setdefault(_identity(key), []).append(key)

    # ⚑⚑ BOTH CONDITIONS: an unambiguous one-to-one pairing AND a plausible path move. The count
    # asymmetry alone refuses a legitimate 2-old-to-2-new directory move; path plausibility alone
    # re-admits the fan-out. Together they pair a relocation and refuse everything else.
    moved = frozenset(
        (paid_keys[0], added_keys[0])
        for ident, added_keys in added_by_identity.items()
        if len(added_keys) == 1
        and len(paid_keys := paid_by_identity.get(ident, [])) == 1
        and _plausible_move(paid_keys[0].rpartition(":")[0], added_keys[0].rpartition(":")[0]))
    relocated_from = {src for src, _dst in moved}
    relocated_to = {dst for _src, dst in moved}

    # ⚑⚑⚑ SUSPECT IS THE THIRD OUTCOME ARRIVING AT THE RATCHET. This repository's standing rule
    # is that a comparison which CANNOT BE MADE reports INVALID rather than FALSE — and the
    # ratchet was the one place holding that rule while violating it. A refusal because a key is
    # plainly new and a refusal because the evidence was AMBIGUOUS are different facts, and a
    # two-valued verdict reports them identically.
    #
    # ⚑⚑ A KEY IS SUSPECT WHEN IT WAS PATH-PLAUSIBLE AGAINST SOME RETIREMENT AND LOST ONLY ON
    # AMBIGUITY — the 1-old-to-N-new fan-out, where at most one of the N is the move and nothing
    # in the census says which. The operator reading a refusal needs exactly this: "I refused
    # this and I could not have told you it was real" is a different instruction from "this is
    # new debt".
    #
    # ⚑ IT NEVER CHANGES THE VERDICT, AND THAT IS THE WHOLE DESIGN. The peer implementation this
    # was compared against carries the same state behind a `strict=` flag defaulting OFF, so its
    # fan-out is CHURN unless asked — measured. Here the refusal is unconditional and `suspect`
    # is pure vocabulary, which means it cannot become a way to let something through.
    suspect = frozenset(
        key
        for ident, added_keys in added_by_identity.items()
        if len(added_keys) > 1
        for key in added_keys
        if any(_plausible_move(old.rpartition(":")[0], key.rpartition(":")[0])
               for old in paid_by_identity.get(ident, [])))

    return Diff(added=frozenset(added - relocated_to),
                paid=frozenset(paid - relocated_from),
                moved=moved,
                suspect=suspect)


def write_baseline(path: Path, keys: Iterable[str], *, write: bool) -> None:
    """Record `keys` as the baseline, and CONFIRM WHAT LANDED rather than what was intended.

    ⚑⚑ `write` IS KEYWORD-ONLY AND REQUIRED. There is no environment variable and no
    default: a mutation nobody asked for in the call is a mutation nobody can find in the
    call. Passing `write=False` is a no-op rather than an error, so a dry run is expressible
    without a second code path.

    ⚑ THE READBACK IS NOT A FORMALITY. A write that succeeds and a write that lands are
    different claims, and a baseline that did not land reads as ABSENT on the next run —
    which reads green while asserting nothing.

    Raises:
        OSError: when the keys read back differ from the keys written — the readback above,
            surfaced rather than swallowed, because a baseline that did not land is silent.

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

    Returns:
        the the paydown-only ratchet. Return (exit code, report lines).

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
        # ⚑ THE MARK IS ON THE KEY, NOT IN A SEPARATE SECTION. A second list would let a reader
        # scan the refusals and never reach the ambiguity — the operator seeing "+ b.py:rule1"
        # needs to know AT THAT LINE that this one could not be told apart from a relocation.
        lines.extend(f"  {'?' if key in diff.suspect else '+'} {key}"
                     for key in sorted(diff.added))
    if diff.suspect:
        lines.append(f"  ? = {len(diff.suspect)} of these is/are AMBIGUOUS: path-plausible "
                     f"against a retired key, refused because a fan-out hides which")
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
