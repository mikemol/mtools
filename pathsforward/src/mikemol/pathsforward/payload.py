# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The scheduler payload: the queue forced into the tick's context, budgeted, or refused.

⚑⚑ OPERATOR RULING D4: A PAYLOAD THAT CANNOT FIT IS REFUSED, NEVER TRIMMED SILENTLY. The ladder
is el-openglo's (residue, then evidence, then steps below the top 5/2/1, then the standing rules),
and `PayloadOverBudgetError` is raised when even the last rung is over. The survey measured the
alternatives: mtools emitted 56159 characters under a 12000 budget with `TRUNCATED:` attached.

⚑⚑ `truncated` IS EMITTED ONLY WHEN A RUNG DROPPED SOMETHING, and the budget is measured WITH the
marker on. sre's was a constant True (its 5552-character fixture payload said it was truncated),
and el-openglo's appended the marker after measuring, so a payload could pass the check and
still be over by the marker's length.

⚑ `state_path` IS THE PATH THIS WAS BUILT FROM, NEVER THE FILE'S OWN KEY. mtools' renderer read
`state_path` from the document, so a payload built from a scratch copy named the LIVE file and
every copy-based test targeted live.

⚑ THE FORMAT IS el-openglo's TEXT (D6, pending the operator), made repo-neutral: the scheduler
verbs come from the file's `bindings`, and there is no repo-specific ground-truth command. The
standing rules are three declared keys, emitted verbatim: el-openglo's `preamble`, and mtools'
`standing` (a list) and `host` (an object).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward.digest import v2
from mikemol.pathsforward.model import strlist, text, ticks

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.pathsforward.model import Json, State

PAYLOAD_BUDGET = 6000
CLIP = 160
_ELLIPSIS = "..."
_EVIDENCE = "      evidence:"
_TOP_STEPS = (5, 2, 1)
_HIDDEN = ("done", "dropped")


class PayloadOverBudgetError(RuntimeError):
    """Even the last rung is over budget; arming with it would be arming with a lie."""


@dataclass(frozen=True)
class Request:
    """What a payload is built from: the state, where it was read, and when."""

    state: State
    state_path: Path
    generated_at: str
    budget: int = PAYLOAD_BUDGET


@dataclass(frozen=True)
class _Rung:
    """One step of the ladder: how much to keep, and what that drops."""

    steps: int
    evidence: bool
    residue: bool
    rules: bool
    dropped: tuple[str, ...]


def _binding(state: State, capability: str) -> str:
    """Name the tool bound to a capability, or the capability when unbound.

    Returns:
        the binding.

    """
    raw = state.doc.get("bindings")
    bound = cast("Json", raw).get(capability) if isinstance(raw, dict) else None
    return str(bound) if bound else capability


def header(req: Request) -> list[str]:
    """Build the lines every rung keeps.

    Returns:
        the header lines.

    """
    state, path = req.state, req.state_path
    return [
        "[paths-forward tick] Invoke the paths-forward-loop skill and run ONE tick (section 4).",
        f"state_path={path}",
        f"project_root={text(state.doc, 'project_root')}",
        f"counter={state.counter} state_hash={v2(state.waypoints)} generated_at={req.generated_at}",
        (f"Reconcile first: `mikemol-paths-forward --state {path} --verify <state_hash>`; "
         "exit 4 means the FILE wins."),
        (f"Re-arm when the hash changes: {_binding(state, 'SCHEDULE_CREATE')} a fresh job from "
         f"`--payload`, verify with {_binding(state, 'SCHEDULE_LIST')}, THEN "
         f"{_binding(state, 'SCHEDULE_DELETE')} the predecessor "
         f"(job_id={text(state.doc, 'job_id') or '-'})."),
    ]


def rules(state: State) -> list[str]:
    """Build the standing-rules block: `preamble`, `standing` and `host`, verbatim.

    Returns:
        the block's lines; [] when none of the three keys is set.

    """
    out: list[str] = []
    raw_pre = state.doc.get("preamble")
    pre = raw_pre.splitlines() if isinstance(raw_pre, str) else strlist(state.doc, "preamble")
    if pre:
        out += ["preamble:", *(f"  {line}" for line in pre)]
    standing = strlist(state.doc, "standing")
    if standing:
        out += ["standing:", *(f"  - {line}" for line in standing)]
    host = state.doc.get("host")
    if isinstance(host, dict) and host:
        pairs = cast("Json", host)
        out += ["host:", *(f"  {key}={_host_value(value)}" for key, value in pairs.items())]
    return out


def _host_value(value: object) -> str:
    """Render one `host` value; a list is comma-joined.

    Returns:
        the text.

    """
    if isinstance(value, list):
        return ",".join(str(item) for item in cast("list[object]", value))
    return str(value)


def stanza(w: Json) -> str:
    """Render one live waypoint in full.

    Returns:
        a three-line stanza: identity, next step, first line of evidence.

    """
    on = strlist(w, "blocked_on")
    kind = text(w, "blocked_kind") or "-"
    blocked = f" blocked_on={','.join(on)}({kind})" if on else ""
    evidence = text(w, "evidence").splitlines()
    return (
        f"  {text(w, 'symbol')} [{text(w, 'status')}]{blocked} ticks_blocked={ticks(w)} :: "
        f"{text(w, 'title')}\n"
        f"      next: {text(w, 'next_bounded_step')}\n"
        f"{_EVIDENCE} {evidence[0] if evidence else '-'}"
    )


def clip(block: str) -> str:
    """Collapse a stanza to its first line, clipped to CLIP characters.

    Returns:
        the collapsed line.

    """
    head = block.splitlines()[0]
    return head if len(head) <= CLIP else head[: CLIP - len(_ELLIPSIS)] + _ELLIPSIS


def ladder(n_live: int, *, has_rules: bool) -> list[_Rung]:
    """List the rungs in order, from everything to the least a tick can act on.

    Returns:
        the rungs; the last drops the standing rules only when there are some.

    """
    rungs = [
        _Rung(n_live, evidence=True, residue=True, rules=True, dropped=()),
        _Rung(n_live, evidence=True, residue=False, rules=True, dropped=("residue",)),
        _Rung(n_live, evidence=False, residue=False, rules=True,
              dropped=("residue", "evidence")),
    ]
    rungs += [
        _Rung(top, evidence=False, residue=False, rules=True,
              dropped=("residue", "evidence", f"steps-below-{top}"))
        for top in _TOP_STEPS
    ]
    if has_rules:
        last = _TOP_STEPS[-1]
        rungs.append(_Rung(last, evidence=False, residue=False, rules=False,
                           dropped=("residue", "evidence", f"steps-below-{last}", "rules")))
    return rungs


def _compose(req: Request, rung: _Rung) -> str:
    """Render the payload one rung describes, with its truncation marker when it dropped anything.

    Returns:
        the payload text.

    """
    state = req.state
    live = [stanza(w) for w in state.waypoints if text(w, "status") not in _HIDDEN]
    done = [text(w, "symbol") for w in state.waypoints if text(w, "status") == "done"]
    block = rules(state)
    lines = header(req)
    if rung.rules:
        lines += block
    lines.append("waypoints:")
    lines += live[: rung.steps] + [clip(s) for s in live[rung.steps:]]
    if done:
        lines.append(f"  done ({len(done)}): {', '.join(done)}")
    if rung.residue and state.residue:
        lines += ["residue:", *(f"  {text(r, 'symbol')}: {text(r, 'reason')}"
                                for r in state.residue)]
    body = "\n".join(lines)
    if not rung.evidence:
        body = "\n".join(ln for ln in body.splitlines() if not ln.startswith(_EVIDENCE))
    if rung.dropped:
        named = [f"rules({len(block)}-lines)" if d == "rules" else d for d in rung.dropped]
        body += f"\ntruncated=true dropped={','.join(named)} - read state_path for the rest."
    return body


def build(req: Request) -> str:
    """Build the payload from the first rung that fits the budget, marker included.

    Returns:
        the payload, at most `req.budget` characters.

    Raises:
        PayloadOverBudgetError: when no rung fits.

    """
    n_live = sum(1 for w in req.state.waypoints if text(w, "status") not in _HIDDEN)
    size = 0
    for rung in ladder(n_live, has_rules=bool(rules(req.state))):
        body = _compose(req, rung)
        size = len(body)
        if size <= req.budget:
            return body
    msg = (f"payload is {size} characters even at the last rung; the budget is {req.budget}. "
           "Shorten the top waypoint's next_bounded_step or split the waypoint.")
    raise PayloadOverBudgetError(msg)
