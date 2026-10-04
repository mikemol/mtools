# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""mikemol.grade: the GRADE LADDER and its interpretation, moved from paperkit's engine `grade.py`.

The PURE half of paperkit's grader: the falsifiability rungs, the clamp, strength and
corroboration orders, and how a measured flip-set becomes a grade. Separated from the sweep
(sandbox, AST mutation, sensitivity) so the CALCULATION (the expensive measurement) and the
INTERPRETATION (this cheap reading over it) are distinct modules.

A LEAF: pure data and pure functions, standard library only. It used to read the scope names
lazily from paperkit's `bib`; they are now `SCOPES` here, so nothing is imported from paperkit.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

type Json = str | int | bool | list[Json] | dict[str, Json] | None
type Record = dict[str, Json]
type OwnerGrades = Mapping[tuple[str, str], Json]
type _Hop = tuple[int, str | None, list[str]]

STRENGTH = {"vacuous": 0, "existence": 1, "indeterminate": 1, "behavioral": 2, "imported": 3}
ORDER = {"existence": 1, "behavioral": 2}  # valid --min-strength thresholds

# Total order for clamping (effective grade = min over self + premises). Conservative:
# vacuous < indeterminate (runs, falsifiability unproven) < existence (presence proven)
# < behavioral (falsifiability proven) < imported (seam: verified whole in a separately-
# gated sibling; a delegated premise never weakens what rests on it, so it ranks at top).
RANK_C = {
    "broken": -1,
    "vacuous": 0,
    "indeterminate": 1,
    "existence": 2,
    "behavioral": 3,
    "imported": 4,
}
GRADE_C = {v: k for k, v in RANK_C.items()}
_FLOOR = min(RANK_C.values())

# Corroboration: a SECOND, ORTHOGONAL evidence axis, NOT another rung on RANK_C above. The grade
# asks "does a mutation flip this check" (FALSIFIABILITY); this asks "is the verdict confirmed by
# INDEPENDENT producers" (CORROBORATION). A check's strength is the PAIR (falsifiability,
# corroboration), never one collapsed scalar. An agree: verdict that passes with two or more
# textually-distinct producers is `distinct`; one witness, or identical producers concurring
# trivially, is `single`.
#
# THE MIDDLE VALUE IS THE HONEST ONE AND EVERY RECORD IS IN IT. This axis used to call two or more
# distinct producers `independent`, a positive claim of DECORRELATION made on the strength of not
# having looked: the test is a `set()` over producer command STRINGS, and nothing traces whether
# they share an upstream. String-distinctness is a fine NECESSARY condition (it catches
# `agree:cat a.txt ||| cat a.txt`) and was only ever wrong as a SUFFICIENT one. So `distinct` says
# what was measured, `independent` is reserved for what a footprint comparison can certify, and
# `correlated` names a MEASURED overlap.
#
# ORDER: `correlated` below `distinct` because the floor's job is to fail CLOSED: a measured
# overlap is a known-weak state, while `distinct` is merely unexamined. A floor of `independent`
# is unreachable until a footprint comparison lands, the honest consequence of never having
# measured it.
CORRO_C = {"single": 0, "correlated": 1, "distinct": 2, "independent": 3}

# Decision-coverage: a THIRD, ORTHOGONAL axis, again NOT a rung on RANK_C. The grade asks "does a
# mutation flip this check" over the raise-monotone branch:/def: atom; this asks "of the decisions
# a check REACHES, how many does it ASSERT on". A finer, NON-monotone flip: cell inverts one
# condition, and is read soundly only when BOTH sibling arms are GENUINELY reached: an inversion
# that does NOT flip the check is then an UNASSERTED decision. `unasserted` < `asserted`; it NEVER
# lowers a grade (incompleteness is not a weaker rung), only names the gap. Absent field means the
# check has no reached-both-arms decision it fails to assert (the common case).
DECISIONS_C = {"unasserted": 0, "asserted": 1}

# Resolution: a FOURTH, ORTHOGONAL axis, again NOT a rung on RANK_C. The grade asks "how strong is
# this claim's evidence"; this asks "did the unfold that produced it actually REACH everything it
# delegates to". An unresolved delegation is a TRUNCATED observation, not a weaker one, so it
# NEVER lowers a grade: it NAMES THE GAP. `truncated` < `resolved`.
#
# The distinction it preserves is the one a bare grade cannot carry: `imported` sits at the TOP of
# RANK_C so a RESOLVED delegation to a healthy owner imposes no clamp, which makes "resolved,
# imposed nothing" and "never resolved, imposed nothing" numerically identical while meaning
# opposite things. A check that cannot be evaluated is tristate (2, never 0 and never 1); the
# unfold needed the same third state.
RESOLUTION_C = {"truncated": 0, "resolved": 1}

# Baseline: the same distinction once more. `broken` is not a weak rung: `grade_from_sens` emits
# it on `not baseline`, i.e. the check never ESTABLISHED anything. But a baseline can fail for two
# categorically different reasons: a FAIL ("the claim is false") or an UNAVAILABLE ("I could not
# REACH the thing"). A check killed by its memory cap used to grade `broken` with "repo is not
# green", about a green repo. The fix is NOT a rung below `broken` (the ladder is a positive cone)
# but this axis: it NEVER lowers a grade, it names WHY no grade was established. `unreachable` is
# not worse than `refuted`: it is a different kind of statement.
BASELINE_C = {"unreachable": 0, "refuted": 1, "established": 2}

# Scope: how much of its claim a check actually reaches. A check may be perfectly falsifiable
# about a PART of what its sentence asserts, so falsifiability and scope are independent: an axis,
# not a rung. It is DECLARED, not measured (no sweep can know a sentence means more than its
# witness tests), and the gate holds the declaration to the measurement; so this axis never
# clamps. Absence means `full`: a claim is read as covering what it says.
#
# MOVED HERE from paperkit's `bib._SCOPES`, same values and same order. The parser still has to
# refuse a typo, so paperkit's `bib` imports this tuple instead of owning it; the old lazy
# `import bib` (and the `SCOPE_C` dict subclass that deferred it) is gone, because grade now
# imports nothing from paperkit. Ordered fragment < full: less coverage is the lower end.
SCOPES = ("fragment", "full")
SCOPE_C = {v: i for i, v in enumerate(SCOPES)}

# The two DERIVATIONS every consumer needs, so none re-declares the rungs. A ladder re-listed
# downstream drifts silently and in the WORST direction: a display order that omits a rung
# SILENTLY DROPS claims from its own total, and an adequacy gate written as a BLACKLIST of failing
# grades PASSES any rung added after it was written (it fails open). Both are stated here as a
# function of RANK_C, so a new rung reaches every consumer by being added ONCE, above.


@dataclass(frozen=True)
class _Ctx:
    """What one `clamp` call reads and memoises while it walks the grounding edges."""

    rby: dict[str, Record]
    og: OwnerGrades
    keys: set[str] | None
    effc: dict[str, _Hop]


def _rank(grade: Json) -> int:
    """Return the rank of a grade name; a missing, non-string or unknown value ranks 0.

    Returns:
        The rung's rank in `RANK_C`, or 0 (vacuous).

    """
    return RANK_C.get(grade, 0) if isinstance(grade, str) else 0


def _key(record: Record) -> str:
    """Return the record's key as text.

    Returns:
        `str(record["key"])`.

    """
    return str(record["key"])


def _strings(value: Json) -> list[str]:
    """Return the string items of a list value; anything that is not a list holds none.

    Returns:
        The items of `value` that are strings, in order.

    """
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _record(value: Json) -> Record | None:
    """Return the value when it is a mapping.

    Returns:
        `value` if it is a dict, else None.

    """
    return value if isinstance(value, dict) else None


def _edge_name(delegation: Record) -> str:
    """Return a delegation edge as `owner#claim`.

    Returns:
        The text `<owner>#<claim>`, with `None` for a missing half.

    """
    return f"{delegation.get('owner')}#{delegation.get('claim')}"


def rungs(descending: bool = True) -> list[str]:
    """Return every grade the ladder defines, in rank order: the display order for any summary.

    Listing rungs by hand is how a report comes to omit one and quietly under-count its own
    population.

    Returns:
        The grade names sorted by rank, highest first when `descending`.

    """
    return sorted(RANK_C, key=RANK_C.__getitem__, reverse=descending)


def below(floor: str) -> list[str]:
    """Return the grades that FAIL a `floor`, derived, so the adequacy gate fails CLOSED.

    Stated as a blacklist it would admit every future rung by default; stated as
    `rank < rank(floor)` a new rung is judged the moment it exists. `floor` must be a defined rung
    (KeyError if it is not: a typo'd floor must not silently grade everything green).

    Returns:
        The grades ranked strictly under `floor`, lowest first.

    """
    return [g for g in rungs(descending=False) if RANK_C[g] < RANK_C[floor]]


def grade_from_sens(baseline: bool, sens: Sequence[Json], reachable: bool = True) -> Record:
    """Return the cmd/custom verdict as a pure function of (baseline-passes, flip-set).

    Was paperkit's private `_grade_from_sens`; public here because three paperkit tools import it.
    `reachable` carries the resolver's tristate the last hop: a caller that reads `.passed`
    collapses UNAVAILABLE onto FAIL and both arrive here as `baseline=False`; passing
    `reachable=False` says WHICH, so the record stops asserting "repo is not green" about a repo
    whose check merely could not run. The GRADE is unchanged either way: the axis names the gap,
    it does not move the rung (see `BASELINE_C`).

    Returns:
        The grade record: `broken` when the baseline fails, `behavioral` when some mutation flips
        the check, else `indeterminate`.

    """
    if not baseline:
        return {
            "grade": "broken",
            "tests": [],
            "baseline": "unreachable" if not reachable else "refuted",
            "why": (
                "check could not be REACHED in a pristine sandbox — its toolchain or a "
                "resource it needs was unavailable, so nothing was established about "
                "the claim (this is NOT a statement that the repo is red)"
            )
            if not reachable
            else "check does not pass in a pristine sandbox — repo is not green",
            "not_higher": "—",
            "not_lower": "—",
        }
    if sens:
        return {
            "grade": "behavioral",
            "tests": list(sens),
            "baseline": "established",
            "why": f"falsifiable — corrupting {len(sens)} input(s) flips it red",
            "not_higher": (
                "behavioral is the top tier; a proof-grade (total, postulate-free witness) "
                "tier is not yet defined"
            ),
            "not_lower": (
                f"not indeterminate/vacuous: a mutation DOES flip it "
                f"(sensitive to {len(sens)} input(s))"
            ),
        }
    return {
        "grade": "indeterminate",
        "tests": [],
        "why": (
            "no generic mutation flips it — vacuous OR a negative-assertion check; "
            "needs a targeted counter-fixture"
        ),
        "not_higher": (
            "to rise: a targeted counter-fixture (a positive mutation) would prove it behavioral"
        ),
        "not_lower": "not provably vacuous: it runs a cmd:, not a presupposed file:",
    }


def mark_content_sensitive(records: list[Record], content: set[str]) -> list[Record]:
    """Mark each behavioral check content_sensitive iff a flipped test is the document's content.

    The document's OWN content is bib, rubric and out, not merely config or engine: a behavioral
    check sensitive only to config or the engine can-fail by CRASH but does not test the
    document's content. A pure reading over the grade records plus the content-file names.

    Returns:
        The same `records`, each behavioral one now carrying `content_sensitive`.

    """
    for r in records:
        if r["grade"] == "behavioral":
            r["content_sensitive"] = any(Path(t).name in content for t in _strings(r["tests"]))
    return records


def _delegated(r: Record, og: OwnerGrades) -> int | None:
    """Return the owner's EFFECTIVE rank for a delegation edge, or None if we do not hold it.

    A grade is TWO-DIMENSIONAL (self, effective) and an owner entry may carry the pair as a dict
    or, for a caller that holds only one number, a bare grade string. The bound is the EFFECTIVE
    component: what the owner's own project already clamped it to. Reading `grade` here instead
    would truncate the unfold at the boundary.

    An edge we cannot resolve is marked UNRESOLVED on the record, a third state distinct from
    both "clamps" and "does not clamp": "no constraint recorded" and "constraint recorded as:
    none" render identically once collapsed.

    Returns:
        The owner's effective rank, or None when there is no delegation or no owner grade held.

    """
    d = _record(r.get("delegates_to"))
    if not d:
        return None
    owner, claim = d.get("owner"), d.get("claim")
    g = og.get((owner, claim)) if isinstance(owner, str) and isinstance(claim, str) else None
    if g is None:
        r["unresolved"] = [_edge_name(d)]
        return None
    if isinstance(g, dict):
        r["delegated"] = g  # carry the owner's pair for the reader
        g = g.get("effective_grade", g.get("grade"))
    else:
        r["delegated"] = {"grade": g, "effective_grade": g, "clamped_by": None}
    return RANK_C.get(g) if isinstance(g, str) else None


def _note_unresolved(r: Record, premise: str) -> None:
    """Append a premise key to the record's `unresolved` list, creating it if absent."""
    cur = r.setdefault("unresolved", [])
    if isinstance(cur, list):
        cur.append(premise)


def _eff(k: str, ctx: _Ctx, stack: tuple[str, ...] = ()) -> _Hop:
    """Return the effective rank of `k`, the premise that pins it, and the chain to that premise.

    The pin alone is the LAST step; the path is the prefix. An importer asking "do I distrust
    this witness or chase its premise" is answerable from the chain and only sometimes from the
    final name. A key with no record imposes no constraint (it is outside this argument, or never
    graded; the caller's `keys` set marks the second case unresolved on the premise's dependant).

    Returns:
        (rank, pin, path), memoised in `ctx.effc`.

    """
    if k in ctx.effc:
        return ctx.effc[k]
    r = ctx.rby.get(k)
    if r is None:
        return (RANK_C["behavioral"], None, [])  # not in scope: impose no constraint
    best = _rank(r["grade"])
    by: str | None = None
    path: list[str] = []
    de = _delegated(r, ctx.og)  # resolve the delegation edge, if we can
    if de is not None and de < best:
        owner = _edge_name(_record(r.get("delegates_to")) or {})
        best, by = de, owner
        # the owner's own pin continues the chain across the boundary
        og_pin = (_record(r.get("delegated")) or {}).get("clamped_by")
        path = [owner, str(og_pin)] if og_pin else [owner]
    for d in _strings(r.get("rests-on", [])):  # clamp over GROUNDING edges
        # A premise with NO record is skipped, and silence about that is indistinguishable from
        # an edge that resolved to no constraint. `keys` (the bib's own key set) separates a key
        # outside this argument from one IN it and never graded.
        if d not in ctx.rby and ctx.keys is not None and d in ctx.keys:
            _note_unresolved(r, d)
        if d in ctx.rby and d not in stack and d != k:
            dg, _, dpath = _eff(d, ctx, (*stack, k))
            if dg < best:
                best, by, path = dg, d, [d, *dpath]
    ctx.effc[k] = (best, by, path)
    return ctx.effc[k]


def _reaches_truncation(k: str, rby: dict[str, Record], stack: tuple[str, ...] = ()) -> bool:
    """Return whether ANY claim in k's grounding cone has an unresolved edge.

    Walked over rests-on rather than read off `clamp_path`: the path records what CLAMPED, and a
    truncated premise that clamps nothing leaves it empty, precisely the case this must catch.

    Returns:
        True when `k` or anything it transitively rests on carries an unresolved edge.

    """
    r = rby.get(k)
    if r is None or k in stack:
        return False
    if r.get("unresolved"):
        return True
    return any(_reaches_truncation(y, rby, (*stack, k)) for y in _strings(r.get("rests-on", [])))


def clamp(
    records: list[Record],
    owner_grades: OwnerGrades | None = None,
    keys: set[str] | None = None,
) -> list[Record]:
    """Clamp by entailment: no claim is better grounded than its weakest premise.

    A claim is no better grounded than the weakest premise it (transitively) depends on along
    rests-on. Annotates each record with effective_grade, clamp (rungs dropped from the
    self-contained grade), clamped_by (the premise that pins it), clamp_path, scope, unresolved,
    resolution, and the admissible interval (effective_min, effective_max, interval_width).

    `owner_grades` optionally supplies the OTHER SIDE of a delegation edge: {(owner, claim): grade}
    from the owning project's own grade records. A record carrying `delegates_to` then clamps
    against the owner's REAL grade instead of the flat `imported` tag, so a weak imported premise
    weakens what rests on it. It is a parameter and not a lookup because certificates are BUILD
    ARTIFACTS: the caller supplies what it holds. Absent it, `imported` stays at the top; the rank
    is the DEFAULT for an unresolved edge, never a claim about delegated strength.

    `keys` is the bib's own key set; a premise in it with no record is an unfold that stopped.

    Returns:
        The same `records`, annotated.

    """
    rby = {_key(r): r for r in records}
    ctx = _Ctx(rby, owner_grades or {}, keys, {})
    for r in records:
        e, by, path = _eff(_key(r), ctx)
        r["effective_grade"] = GRADE_C[e]
        r["clamp"] = _rank(r["grade"]) - e
        r["clamped_by"] = by
        r["clamp_path"] = [*path]  # the prefix, not just the last step
        # DISCLOSE the scope beside the clamp it produced: a consumer gating on coverage reads a
        # VALUE, never infers it from an arithmetic difference. Defaulted here rather than at
        # parse so an ungraded record and a full-scope one read alike downstream.
        r["scope"] = r.get("entails", "full")
        # Surface the truncation as a VALUE: silence about an unresolved edge is
        # indistinguishable from an edge that resolved to no constraint.
        r.setdefault("unresolved", [])
        r["resolution"] = "truncated" if r["unresolved"] else "resolved"
    # resolution is TRANSITIVE, like the clamp: a claim resting on a truncated premise has a
    # truncated reading too, even though its OWN edges all resolved.
    for r in records:
        if r["resolution"] == "resolved" and _reaches_truncation(_key(r), rby):
            r["resolution"] = "truncated"
    return _bracket(records, rby)


def verify_hop(
    record: Record,
    premises: Mapping[str, str],
    owner_grades: OwnerGrades | None = None,
) -> tuple[bool, str, str]:
    """Recompute ONE hop's effective grade from its own data plus its premises' RESULTS.

    A chain that merely RECORDS its steps asks the reader to trust the computation that produced
    it. A chain that CERTIFIES them gives the reader a per-hop obligation they can discharge
    alone: given this hop's self grade, its delegation, and the effective grades of the claims
    directly beneath it, this function reproduces the hop, consulting nothing above it. The step
    is total and the fold over it is unique: any function agreeing on the base case (a claim with
    no premises: effective = self) and on this step IS this fold.

    THE BOUND THAT MAKES A HOP CHECKABLE AT ALL: the clamp is a MIN, so `eff(k) <= eff(d)` for
    every premise d: a hop can only ever LOWER, never raise, and by no more than its weakest
    premise. A recorded hop violating that monotonicity is detectable locally.

    Returns:
        (ok, expected, why): whether the record's effective grade is what this hop recomputes to,
        the recomputed grade, and what pins it (or the reason it failed).

    """
    best, why = _rank(record.get("grade")), "self"
    og = owner_grades or {}
    d = _record(record.get("delegates_to"))
    if d:
        owner, claim = d.get("owner"), d.get("claim")
        g = og.get((owner, claim)) if isinstance(owner, str) and isinstance(claim, str) else None
        if isinstance(g, dict):
            g = g.get("effective_grade", g.get("grade"))
        if isinstance(g, str) and RANK_C.get(g, 0) < best:
            best, why = RANK_C[g], _edge_name(d)
    for k, pg in premises.items():
        if RANK_C.get(pg, 0) < best:
            best, why = RANK_C[pg], k
    expected = GRADE_C[best]
    got = record.get("effective_grade")
    if got != expected:
        return (False, expected, f"hop recomputes to {expected} (via {why}), record says {got}")
    # the bound: a hop may only LOWER, and never below its weakest premise
    for k, pg in premises.items():
        if _rank(got) > RANK_C.get(pg, 0):
            return (False, expected, f"monotonicity violated: {got} exceeds premise {k}'s {pg}")
    return (True, expected, why)


def _lo(k: str, rby: dict[str, Record], pess: dict[str, int], stack: tuple[str, ...] = ()) -> int:
    """Return the PESSIMISTIC rank of `k`: every unresolved premise read at the ladder's floor.

    Returns:
        The rank, memoised in `pess`; a key with no record imposes no constraint.

    """
    if k in pess:
        return pess[k]
    r = rby.get(k)
    if r is None:
        return RANK_C["behavioral"]  # not in scope: impose no constraint (as in `_eff`)
    best = _rank(r["grade"])
    if r.get("unresolved"):  # the pessimistic reading of a truncation
        best = min(best, _FLOOR)
    if r.get("delegates_to") and not r.get("unresolved"):
        g = (_record(r.get("delegated")) or {}).get("effective_grade")
        if g is not None:
            best = min(best, _rank(g))
    for y in _strings(r.get("rests-on", [])):
        if y in rby and y not in stack and y != k:
            best = min(best, _lo(y, rby, pess, (*stack, k)))
    pess[k] = best
    return best


def _bracket(records: list[Record], rby: dict[str, Record]) -> list[Record]:
    """Annotate the ADMISSIBLE INTERVAL an unresolved unfold leaves behind.

    `effective_grade` is the OPTIMISTIC endpoint: an unresolved delegation imposes no constraint,
    so the reading assumes the best about what it never looked at, a truncation that silently
    reads as strength. The fix is a PAIR of bounds on the RESULT, computed by the same operator
    over the same ladder:

        effective_min   every unresolved premise at the ladder's FLOOR   (pessimistic)
        effective_max   every unresolved premise imposing nothing        (= effective_grade)

    The true grade lies inside, and WHERE it lies is exactly the unresolved edge. The interval's
    WIDTH is the cost of not having unfolded, in the same units as the answer, monotone, and
    shrinking to zero as edges resolve. It also separates the two owner shapes a single number
    cannot: an owner whose WITNESS is weak has both endpoints low; an owner whose PREMISE is
    unresolved has a WIDE interval.

    Returns:
        The same `records`, each carrying effective_min, effective_max and interval_width.

    """
    pess: dict[str, int] = {}
    for r in records:
        e_lo = _lo(_key(r), rby, pess)
        r["effective_min"] = GRADE_C[e_lo]
        r["effective_max"] = r["effective_grade"]
        r["interval_width"] = _rank(r["effective_max"]) - e_lo
    return records
