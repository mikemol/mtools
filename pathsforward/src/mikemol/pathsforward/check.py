# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The file's consistency check: every mechanically checkable charter property, reported.

⚑⚑ gabion's check, whole, with el-openglo's reasonless-drop arm. The survey measured
el-openglo's `--check` passing a state with a duplicate live `W1` and a `W999` above counter=24;
gabion's caught both. Each property is its own function so a failure names itself.

⚑ IT REPORTS AND DOES NOT REPAIR (D8, pending the operator). A live file missing `W17` is a
finding for its owner, not something this tool grandfathers by writing residue on their behalf.

⚑ `status=dropped` IS A FINDING (D5, pending the operator): dropping means moving to residue with
a reason, which `--drop` does. The finding says so rather than reading as an unknown status.

⚑ THE EVIDENCE READ IS OPT-IN. `evidence_findings` stats every absolute path a waypoint's
evidence names (skill section 7.8); it touches the filesystem once per path, so it runs only
under `--check-evidence`, never as the bare check.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pathsforward import attach, outcomes, vector
from mikemol.pathsforward.model import (
    BLOCKED_KINDS,
    STATUSES,
    RefusedError,
    strlist,
    symbol_number,
    text,
)
from mikemol.pathsforward.tags import ARTIFACT_GRAINS, parse_tag

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json, State

_DROPPED = "dropped"
_PATH_TRIM = ",;:()[]'\"`"
# ⚑ A SENTENCE MAY END ON A PATH: `/home/x/file.md.` was reported missing. These marks are tried
# off the end one at a time; see `missing` for when a trimmed reading is believed.
_SENTENCE_END = (".", ",", ";", ":", ")")
# ⚑ A BAZEL LABEL IS NOT A PATH: `//pkg:f`, `@repo//pkg:f`, `@@//pkg:f`. summit's W37 evidence
# names `//paperkit:components.bzl`, which `--check-evidence` reported missing.
_LABEL = re.compile(r"@{0,2}[\w.~+-]*//")
# nemik's MalformedBlockerShape: an entry that STARTS as a symbol but is not one whole.
_SYMBOLISH = re.compile(r"^((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+:)?W\d+\b")
_CLEAN_SYMBOL = re.compile(r"((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+:)?W\d+")
# nemik's OperatorAskShape readings (nemik/blocks.py, operator_category), the two it warns on.
_EXPLICIT_ASK = re.compile(r"^\s*operator\s*:\s*(decide|act)\b", re.IGNORECASE)
_ANSWERED = re.compile(r"\b(ruled|keep holding|approved|go-ahead given|decided)\b", re.IGNORECASE)
_BARE_PARTY = re.compile(
    r"^\s*(the\s+)?(operator|user|mikemol|mike|human)\s*(\(\w+\))?\s*$", re.IGNORECASE
)
_ASK_TITLE = re.compile(r"^\s*operator\b[^:]{0,60}:", re.IGNORECASE)


_TITLE_MAX = 150
_CLAUSE_SEPARATORS = (";", "\u2014", " -- ")


def _claimed(state: State) -> list[str]:
    """List every symbol a record claims, live first, in file order.

    Returns:
        the symbols.

    """
    return [text(rec, "symbol") for rec in (*state.waypoints, *state.residue)]


def coverage(state: State) -> list[str]:
    """Charter gate *coverable*: W1..W<counter> each resolve to a live or residue record.

    Returns:
        one finding per issued symbol that resolves to nothing.

    """
    claimed = set(_claimed(state))
    return [
        f"W{n}: issued (counter={state.counter}) but in neither waypoints nor residue"
        for n in range(1, state.counter + 1)
        if f"W{n}" not in claimed
    ]


def duplicates(state: State) -> list[str]:
    """Report a symbol claimed by more than one record, live or residue.

    Returns:
        one finding per symbol claimed twice or more.

    """
    counts = Counter(_claimed(state))
    return [f"{sym}: claimed {n} times" for sym, n in sorted(counts.items()) if n > 1]


def historical(rec: Json) -> bool:
    """Say whether a residue record is an admitted historical name: not `W<n>`, with a reason.

    ⚑ OPERATOR RULING: summit's `W50b` was issued by a tick that broke the integer rule. It is
    admitted in residue ONLY, and only with a reason, so a stale reference resolves to "W50b,
    residue, here's why". It is never counted against `counter` (it has no number).

    Returns:
        True for a non-`W<n>` symbol whose `reason` is non-blank.

    """
    return symbol_number(text(rec, "symbol")) is None and bool(text(rec, "reason").strip())


def malformed(state: State) -> list[str]:
    """Report a symbol that is not `W<n>` — refused, never `int()`-ed into a crash.

    A historical name in residue with a reason is admitted; live, or reasonless, it is refused.

    Returns:
        one finding per malformed symbol.

    """
    live = [text(w, "symbol") for w in state.waypoints]
    dead = [text(r, "symbol") for r in state.residue if not historical(r)]
    return [f"{sym!r}: not a W<n> symbol" for sym in (*live, *dead) if symbol_number(sym) is None]


def above_counter(state: State) -> list[str]:
    """Report a symbol numbered above `counter`, which no mint could have issued.

    Returns:
        one finding per such symbol.

    """
    return [
        f"{sym}: above counter={state.counter}"
        for sym in _claimed(state)
        if (symbol_number(sym) or 0) > state.counter
    ]


def reasons(state: State) -> list[str]:
    """Report a residue entry with no reason: dropping is a recorded judgement.

    Returns:
        one finding per reasonless residue entry.

    """
    return [
        f"{text(rec, 'symbol')}: residue without a reason"
        for rec in state.residue
        if not text(rec, "reason").strip()
    ]


def edges(state: State) -> list[str]:
    """Report an `enables` or `blocked_on` target that looks like a symbol and resolves nowhere.

    Returns:
        one finding per dangling edge.

    """
    claimed = set(_claimed(state))
    return [
        f"{text(w, 'symbol')} -> {target}: dangling edge"
        for w in state.waypoints
        for target in (*strlist(w, "enables"), *strlist(w, "blocked_on"))
        if symbol_number(target) is not None and target not in claimed
    ]


def statuses(state: State) -> list[str]:
    """Report a live waypoint whose status is outside the enum.

    Returns:
        one finding per bad status; `dropped` names the residue move instead.

    """
    found: list[str] = []
    for w in state.waypoints:
        status = text(w, "status")
        if status == _DROPPED:
            found.append(
                f"{text(w, 'symbol')}: status=dropped in the live list; "
                "use --drop to move it to residue with a reason (D5)"
            )
        elif status not in STATUSES:
            found.append(f"{text(w, 'symbol')}: invalid status {status!r}")
    return found


def blocked(state: State) -> list[str]:
    """Report a blocked waypoint that does not say on whom, or of what kind.

    Returns:
        one finding per under-specified block.

    """
    return [
        f"{text(w, 'symbol')}: blocked without blocked_on and an agent|human blocked_kind"
        for w in state.waypoints
        if text(w, "status") == "blocked"
        and (not strlist(w, "blocked_on") or text(w, "blocked_kind") not in BLOCKED_KINDS)
    ]


def stale_blockers(state: State) -> list[str]:
    """Report a blocked waypoint whose blocker is a LOCAL symbol that is done or dropped (W246).

    ⚑ OPERATOR 2026-10-02: pathsforward holds what does not need nemik. A local symbol's status is
    in this queue, so the writer can say a block can no longer land; a foreign `repo:W<n>` or a
    party is not a local symbol (`symbol_number` refuses it) and stays nemik's to judge.
    `--bump-blocked` prunes a done blocker; a dropped one needs a decision, so it is only named.

    Returns:
        one finding per stale blocker, in queue order.

    """
    done = {text(w, "symbol") for w in state.waypoints if text(w, "status") == "done"}
    dropped = {text(r, "symbol") for r in state.residue}
    found: list[str] = []
    for w in state.waypoints:
        if text(w, "status") != "blocked":
            continue
        for b in strlist(w, "blocked_on"):
            if symbol_number(b) is None:
                continue
            if b in done:
                found.append(
                    f"{text(w, 'symbol')}: blocked on {b}, which is done; run --bump-blocked"
                )
            elif b in dropped:
                found.append(f"{text(w, 'symbol')}: blocked on {b}, which is dropped (residue)")
    return found


def all_landed(state: State) -> list[str]:
    """Report a block whose every blocker is a local symbol that has landed (W479).

    ⚑ nemik's allBlockersLanded, local half: a foreign `repo:W<n>` or a party's state is not in
    this queue, so a block naming one is never judged here.

    Returns:
        one finding per waypoint that is ready, not blocked.

    """
    landed = {text(w, "symbol") for w in state.waypoints if text(w, "status") == "done"}
    landed |= {text(r, "symbol") for r in state.residue}
    return [
        f"{text(w, 'symbol')}: every blocker has landed; it is ready, not blocked"
        for w in state.waypoints
        if text(w, "status") == "blocked"
        and (on := strlist(w, "blocked_on"))
        and all(b in landed for b in on)
    ]


def malformed_blockers(state: State) -> list[str]:
    """Report a blocked_on entry that is a symbol with prose run on (nemik MalformedBlocker).

    It draws no edge, so it can never be seen to land; the reason belongs in evidence.

    Returns:
        one finding per such entry.

    """
    return [
        f"{text(w, 'symbol')}: blocked_on {b!r} is a symbol with prose attached"
        for w in state.waypoints
        for b in strlist(w, "blocked_on")
        if _SYMBOLISH.match(b.strip()) and not _CLEAN_SYMBOL.fullmatch(b.strip())
    ]


def _operator_fault(texts: list[str], title: str) -> str | None:
    """Read a human block's asks the way nemik's operator_category does, for its two warnings.

    Returns:
        the fault, or None when some entry states a live ask or names a condition.

    """
    if all(_BARE_PARTY.match(t) for t in texts) and _ASK_TITLE.match(title):
        texts = [title]
    # nemik's precedence: a live ask (or a condition) wins, then a bare party, then answered.
    if any(
        _EXPLICIT_ASK.match(t) or not (_BARE_PARTY.match(t) or _ANSWERED.search(t)) for t in texts
    ):
        return None
    if any(_BARE_PARTY.match(t) for t in texts):
        return "states no ask"
    return "records the operator's answer already"


def operator_asks(state: State) -> list[str]:
    """Report a human block that asks the operator nothing, or that is already answered (W479).

    ⚑ nemik's OperatorAskShape on this queue alone; nemik also groups the same ask across
    repos, which stays nemik's. Write `operator: decide ...` or `operator: act ...`.

    Returns:
        one finding per such block.

    """
    found: list[str] = []
    for w in state.waypoints:
        if text(w, "status") != "blocked" or text(w, "blocked_kind") != "human":
            continue
        on = strlist(w, "blocked_on")
        if on and (fault := _operator_fault(on, text(w, "title"))) is not None:
            found.append(f"{text(w, 'symbol')}: blocked on the operator but {fault}")
    return found


def titles(state: State) -> list[str]:
    """Report a live waypoint with a blank title (nemik WaypointShape's title minLength, W479).

    Returns:
        one finding per blank title.

    """
    return [
        f"{text(w, 'symbol')}: blank title" for w in state.waypoints if not text(w, "title").strip()
    ]


def bundled_titles(state: State) -> list[str]:
    """Report an open waypoint whose title bundles several clauses (nemik BundledTitleShape, W505).

    nemik's pattern: over 150 chars AND a ';', an em dash or ' -- '. nemik warns; here it
    refuses (operator ruling 2026-10-03: a bundled title is a defect, fixed by atomizing or by
    moving material to evidence; the measured false-positive rate is no exemption). A done
    waypoint is exempt, as in nemik: splitting finished work is noise.

    Returns:
        one finding per bundled open title.

    """
    return [
        f"{text(w, 'symbol')}: bundled title (over 150 chars with several clauses); atomize it"
        for w in state.waypoints
        if text(w, "status") != "done"
        and len(title := text(w, "title")) > _TITLE_MAX
        and any(sep in title for sep in _CLAUSE_SEPARATORS)
    ]


def causes(state: State) -> list[str]:
    """Report a local caused_by that resolves nowhere here (nemik CausedByResolves, W479).

    A foreign `repo:W<n>` is not a local symbol and stays nemik's to resolve.

    Returns:
        one finding per unresolved local cause.

    """
    claimed = set(_claimed(state))
    return [
        f"{text(w, 'symbol')}: caused_by {cause} resolves to neither a waypoint nor residue"
        for w in state.waypoints
        if symbol_number(cause := text(w, "caused_by").strip()) is not None and cause not in claimed
    ]


def edges_into_dropped(state: State) -> list[str]:
    """Report an `enables` into a residue symbol: it resolves, but nothing can enable it (W479).

    Returns:
        one finding per stale edge.

    """
    dropped = {text(r, "symbol") for r in state.residue}
    return [
        f"{text(w, 'symbol')} -> {target}: enables a dropped item (stale edge)"
        for w in state.waypoints
        for target in strlist(w, "enables")
        if target in dropped
    ]


def field_types(state: State) -> list[str]:
    """Report a list field stored as something other than a list.

    Returns:
        one finding per mistyped list field.

    """
    return [
        f"{text(w, 'symbol')}: {key} is {type(w.get(key)).__name__}, not a list"
        for w in state.waypoints
        for key in ("blocked_on", "enables", "touches")
        if key in w and not isinstance(w.get(key), list)
    ]


def weights(state: State) -> list[str]:
    """Report a stored weight that is not an integer (a bool is not one).

    Returns:
        one finding per malformed weight; an absent weight is fine.

    """
    return [
        f"{text(w, 'symbol')}: weight {w.get('weight')!r} is not an integer"
        for w in state.waypoints
        if "weight" in w
        and (not isinstance(w.get("weight"), int) or isinstance(w.get("weight"), bool))
    ]


def comma_tags(state: State) -> list[str]:
    """Report a touches[] tag that carries a comma: several tags joined into one.

    ⚑ MEASURED (nemik-45, 2026-09-27): three nemik tags such as 'adapter,cleanup' were accepted as
    one tag, so an overlap on 'adapter' could never match them. `--update --touches` repairs it.

    Returns:
        one finding per comma-joined tag.

    """
    return [
        f"{text(w, 'symbol')}: touches tag {tag!r} holds a comma; split it with --update --touches"
        for w in state.waypoints
        for tag in strlist(w, "touches")
        if "," in tag
    ]


def _grammar_fault(raw: str) -> str | None:
    """Name what is wrong with one tag under the W120 grammar.

    Returns:
        the fault, or None for a well-formed tag.

    """
    tag = parse_tag(raw)
    if tag.grain == "unknown":
        return "has an unknown prefix (file:, mod: or party:, or none for a topic)"
    if tag.write and tag.grain not in ARTIFACT_GRAINS:
        return "marks a write on a tag that names no bytes (!w is for file: and mod:)"
    if tag.grain == "file" and (tag.name.startswith("/") or ".." in tag.name.split("/")):
        return "is not a repo-relative path (a leading / or a .. segment)"
    return None


def tag_grammar(state: State) -> list[str]:
    """Report a touches[] tag the W120 grammar refuses.

    ⚑ THREE FAULTS, each a tag that would compare wrongly once leases read the grammar: an
    unknown prefix (`path:` is not `file:`, and is never quietly a topic), `!w` on a topic or
    `party:` tag (no bytes to exclude over), and a `file:` path that escapes the repo.

    ⚑ A DONE WAYPOINT IS NOT JUDGED: it can never be leased, and its tags are history written
    before the grammar existed (W18's `gcalculus:proceedings/...`, measured when this landed).

    Returns:
        one finding per faulty tag on a waypoint that is not done.

    """
    return [
        f"{text(w, 'symbol')}: touches tag {tag!r} {fault}"
        for w in state.waypoints
        if text(w, "status") != "done"
        for tag in strlist(w, "touches")
        if (fault := _grammar_fault(tag)) is not None
    ]


def witnessed_live(state: State) -> list[str]:
    """Report a witnessed waypoint whose status says a mind should work it.

    ⚑ A WITNESS DECIDES IT, NOT A TICK (nemik:W59, nemik:W64, 2026-09-27): its evaluator
    (nemik-witnesses --apply) only ever moves it to done, so `ready` would make the loop pick it
    and `working` claims a mind is on it. Convention: blocked, kind agent, on nemik-witnesses.

    Returns:
        one finding per witnessed waypoint that is ready or working.

    """
    return [
        f"{text(w, 'symbol')}: witnessed but {text(w, 'status')}; a witness, not a tick, "
        "marks it done (block it on nemik-witnesses)"
        for w in state.waypoints
        if text(w, "witness") and text(w, "status") in {"ready", "working"}
    ]


def vectors(state: State) -> list[str]:
    """Report a stored vector outside the WV:1 grammar, or one without a valid source (W257).

    ⚑ THE WRITER REFUSES AT WRITE TIME, THIS CATCHES THE REST: a hand edit, a merge, or a file
    written by an older tool. nemik reads the stored string, so a bad one must not sit silently.

    Returns:
        one finding per bad vector.

    """
    found: list[str] = []
    for w in state.waypoints:
        vec, source = text(w, "vector"), text(w, "vector_source")
        if not vec and not source:
            continue
        try:
            vector.parse(vec)
            vector.refuse_source(source)
        except RefusedError as err:
            found.append(f"{text(w, 'symbol')}: {err}")
    return found


def unscored(state: State) -> int:
    """Count the live waypoints with no vector; unscored is a census, never a finding (W257).

    Returns:
        the count.

    """
    return sum(1 for w in state.waypoints if text(w, "status") != "done" and not text(w, "vector"))


def root(state: State) -> list[str]:
    """Report a `project_root` that is not an absolute, existing directory.

    Returns:
        [] or one finding.

    """
    value = text(state.doc, "project_root")
    path = Path(value)
    if value and path.is_absolute() and path.is_dir():
        return []
    return [f"project_root {value!r}: not an absolute existing directory"]


def check(state: State) -> list[str]:
    """Run every property.

    Returns:
        every finding, grouped by property in a fixed order.

    """
    return [
        *coverage(state),
        *duplicates(state),
        *malformed(state),
        *above_counter(state),
        *reasons(state),
        *edges(state),
        *statuses(state),
        *blocked(state),
        *stale_blockers(state),
        *all_landed(state),
        *malformed_blockers(state),
        *operator_asks(state),
        *titles(state),
        *bundled_titles(state),
        *causes(state),
        *edges_into_dropped(state),
        *field_types(state),
        *weights(state),
        *comma_tags(state),
        *tag_grammar(state),
        *witnessed_live(state),
        *vectors(state),
        *root(state),
        *outcomes.findings(state),
        *attach.findings(state),
    ]


def _absolute_paths(rec: Json) -> list[str]:
    """Pick the absolute-path tokens out of a record's evidence; a bazel label is not one.

    Returns:
        the tokens, trimmed of surrounding punctuation.

    """
    tokens = (token.strip(_PATH_TRIM) for token in text(rec, "evidence").split())
    return [token for token in tokens if token.startswith("/") and not _LABEL.match(token)]


def _readings(token: str) -> list[str]:
    """List a token's readings: itself, then each shorter by one trailing sentence mark.

    Returns:
        the readings, longest first; the last ends in no sentence mark.

    """
    readings = [token]
    while readings[-1].endswith(_SENTENCE_END):
        readings.append(readings[-1][:-1])
    return readings


def missing(token: str) -> str | None:
    """Resolve an evidence token against the filesystem, sentence punctuation allowed.

    ⚑ THE RULE: the token names an existing file when ANY reading exists, tried longest first,
    so a real name ending in `.` is kept whenever it exists, and `/x/file.md.` at a sentence's
    end is `/x/file.md` when that exists. Only when no reading exists is it missing, and it is
    reported by its shortest reading, without the sentence's punctuation.

    Returns:
        None when a reading exists, else the path to report as missing.

    """
    readings = _readings(token)
    if any(Path(reading).exists() for reading in readings):
        return None
    return readings[-1]


def evidence_findings(state: State) -> list[str]:
    """Report an absolute path named in evidence that does not exist (opt-in: it stats files).

    Returns:
        one finding per missing path.

    """
    return [
        f"{text(w, 'symbol')}: evidence names {path}, which does not exist"
        for w in state.waypoints
        for path in (missing(token) for token in _absolute_paths(w))
        if path is not None
    ]
