# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The scheduler payload: the queue forced into the tick's context, budgeted, or refused.

⚑⚑ OPERATOR RULING D4: A PAYLOAD THAT CANNOT FIT IS REFUSED, NEVER TRIMMED SILENTLY. The ladder
drops residue, then evidence, then `host`, then the steps below the top 5/2/1, then the collapsed
lower waypoints, and `PayloadOverBudgetError` is raised when even the last rung is over. The
survey measured the alternatives: mtools emitted 56159 characters under a 12000 budget with
`TRUNCATED:` attached.

⚑⚑ TWO THINGS ARE NEVER A RUNG (coordinator ruling, 2026-09-23): the STANDING RULES (`preamble`
and `standing`) and the FIRST READY WAYPOINT'S STEP. The rules are the guardrails — among them
the GIT_*-decoy rule written after a real incident — and a tick that loses them can repeat it;
the step is the unit of work the tick needs. mtools' W24 once lost its step to `steps-below-1`,
and the fix for that then dropped the rules instead. When the two together do not fit, the
payload is refused, naming both sizes.

⚑ LIVE WAYPOINTS ARE LISTED working, ready, blocked (skill section 3), each group in file order.
A blocked W22 listed above a ready W24 put the tick's attention on the item it cannot work.

⚑⚑ `truncated` IS EMITTED ONLY WHEN A RUNG DROPPED SOMETHING, and the budget is measured WITH the
marker on. sre's was a constant True (its 5552-character fixture payload said it was truncated),
and el-openglo's appended the marker after measuring, so a payload could pass the check and
still be over by the marker's length.

⚑ `state_path` IS THE PATH THIS WAS BUILT FROM, NEVER THE FILE'S OWN KEY. mtools' renderer read
`state_path` from the document, so a payload built from a scratch copy named the LIVE file and
every copy-based test targeted live.

⚑ THE RECONCILE COMMAND IS ABSOLUTE. A cron tick's PATH does not carry the venv, so the bare
`mikemol-paths-forward` it once named did not resolve there.

⚑ THE FORMAT IS el-openglo's TEXT (D6, pending the operator), made repo-neutral: the scheduler
verbs come from the file's `bindings`, and there is no repo-specific ground-truth command. The
rules are three declared keys, emitted verbatim: el-openglo's `preamble`, and mtools'
`standing` (a list) and `host` (an object). `host` describes the machine, not a guardrail, so
it is droppable.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward.digest import v2
from mikemol.pathsforward.model import ordered, strlist, text, ticks

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json, State

PROG = "mikemol-paths-forward"
PAYLOAD_BUDGET = 6000
CLIP = 160
_ELLIPSIS = "..."
_EVIDENCE = "      evidence:"
_TOP_STEPS = (5, 2, 1)
_HIDDEN = ("done", "dropped")
_READY = "ready"


class PayloadOverBudgetError(RuntimeError):
    """Even the last rung is over budget; arming with it would be arming with a lie."""


def script_command() -> str:
    """Name this tool by an absolute path, because a cron tick's PATH does not carry the venv.

    Tried in order: the running console script (`sys.argv[0]`, resolved), the console script
    beside the running interpreter, then that interpreter with `-m`.

    Returns:
        an absolute command.

    """
    script = Path(sys.argv[0])
    if script.name == PROG and script.is_file():
        return str(script.resolve())
    python = Path(sys.executable).absolute()
    sibling = python.parent / PROG
    if sibling.is_file():
        return str(sibling)
    return f"{python} -m mikemol.pathsforward"


@dataclass(frozen=True)
class Request:
    """What a payload is built from: the state, where it was read, when, and by which command."""

    state: State
    state_path: Path
    generated_at: str
    budget: int = PAYLOAD_BUDGET
    command: str = field(default_factory=script_command)


@dataclass(frozen=True)
class _Rung:
    """One step of the ladder: how much to keep, and what that drops."""

    steps: int
    evidence: bool
    residue: bool
    host: bool
    collapsed: bool
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
        (f"Reconcile first: `{req.command} --state {path} --verify <state_hash>`; "
         "exit 4 means the FILE wins."),
        (f"Re-arm when the hash changes: {_binding(state, 'SCHEDULE_CREATE')} a fresh job from "
         f"`--payload`, verify with {_binding(state, 'SCHEDULE_LIST')}, THEN "
         f"{_binding(state, 'SCHEDULE_DELETE')} the predecessor "
         f"(job_id={text(state.doc, 'job_id') or '-'})."),
    ]


def guards(state: State) -> list[str]:
    """Build the standing rules every rung keeps: `preamble` and `standing`, verbatim.

    Returns:
        the block's lines; [] when neither key is set.

    """
    out: list[str] = []
    raw_pre = state.doc.get("preamble")
    pre = raw_pre.splitlines() if isinstance(raw_pre, str) else strlist(state.doc, "preamble")
    if pre:
        out += ["preamble:", *(f"  {line}" for line in pre)]
    standing = strlist(state.doc, "standing")
    if standing:
        out += ["standing:", *(f"  - {line}" for line in standing)]
    return out


def host_block(state: State) -> list[str]:
    """Build the droppable `host` block, verbatim.

    Returns:
        the block's lines; [] when `host` is unset or empty.

    """
    host = state.doc.get("host")
    if isinstance(host, dict) and host:
        pairs = cast("Json", host)
        return ["host:", *(f"  {key}={_host_value(value)}" for key, value in pairs.items())]
    return []


def rules(state: State) -> list[str]:
    """Build the whole rules block: the standing rules, then `host`.

    Returns:
        the block's lines; [] when none of the three keys is set.

    """
    return guards(state) + host_block(state)


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


def _shown(state: State) -> list[Json]:
    """List the unhidden waypoints in the one order every view shares (`model.ordered`).

    Returns:
        the live waypoints.

    """
    return [w for w in ordered(state.waypoints) if text(w, "status") not in _HIDDEN]


def _pinned(live: list[Json]) -> int:
    """Find the first ready waypoint, whose stanza every rung keeps whole.

    Returns:
        its index, or 0 when none is ready (the top stanza is always kept).

    """
    return next((i for i, w in enumerate(live) if text(w, "status") == _READY), 0)


def ladder(n_live: int, *, has_host: bool) -> list[_Rung]:
    """List the rungs in order, from everything to the least a tick can act on.

    Returns:
        the rungs; the host rung exists only when there is a host block to drop.

    """
    rungs = [
        _Rung(n_live, evidence=True, residue=True, host=True, collapsed=True, dropped=()),
        _Rung(n_live, evidence=True, residue=False, host=True, collapsed=True,
              dropped=("residue",)),
        _Rung(n_live, evidence=False, residue=False, host=True, collapsed=True,
              dropped=("residue", "evidence")),
    ]
    trimmed: tuple[str, ...] = ("residue", "evidence")
    if has_host:
        trimmed += ("host",)
        rungs.append(_Rung(n_live, evidence=False, residue=False, host=False, collapsed=True,
                           dropped=trimmed))
    rungs += [
        _Rung(top, evidence=False, residue=False, host=False, collapsed=True,
              dropped=(*trimmed, f"steps-below-{top}"))
        for top in _TOP_STEPS
    ]
    last = _TOP_STEPS[-1]
    rungs.append(_Rung(last, evidence=False, residue=False, host=False, collapsed=False,
                       dropped=(*trimmed, f"steps-below-{last}", "collapsed")))
    return rungs


def _waypoint_lines(live: list[Json], rung: _Rung) -> list[str]:
    """Render the live waypoints one rung keeps: the top and the first ready whole.

    Returns:
        the lines; a collapsed waypoint is one clipped line, or absent on the last rung.

    """
    keep = _pinned(live)
    out: list[str] = []
    for i, w in enumerate(live):
        if i < rung.steps or i == keep:
            out.append(stanza(w))
        elif rung.collapsed:
            out.append(clip(stanza(w)))
    return out


def _compose(req: Request, rung: _Rung) -> str:
    """Render the payload one rung describes, with its truncation marker when it dropped anything.

    Returns:
        the payload text.

    """
    state = req.state
    done = [text(w, "symbol") for w in state.waypoints if text(w, "status") == "done"]
    lines = header(req) + guards(state)
    if rung.host:
        lines += host_block(state)
    lines.append("waypoints:")
    lines += _waypoint_lines(_shown(state), rung)
    if done:
        lines.append(f"  done ({len(done)}): {', '.join(done)}")
    if rung.residue and state.residue:
        lines += ["residue:", *(f"  {text(r, 'symbol')}: {text(r, 'reason')}"
                                for r in state.residue)]
    body = "\n".join(lines)
    if not rung.evidence:
        body = "\n".join(ln for ln in body.splitlines() if not ln.startswith(_EVIDENCE))
    if rung.dropped:
        body += (f"\ntruncated=true dropped={','.join(rung.dropped)} - read state_path "
                 "for the rest.")
    return body


def _kept_sizes(state: State) -> tuple[int, int]:
    """Measure the two things no rung drops: the standing rules and the first ready stanza.

    Returns:
        (standing-rules characters, first-ready-stanza characters).

    """
    live = _shown(state)
    step = len(stanza(live[_pinned(live)])) if live else 0
    return len("\n".join(guards(state))), step


def build(req: Request) -> str:
    """Build the payload from the first rung that fits the budget, marker included.

    Returns:
        the payload, at most `req.budget` characters.

    Raises:
        PayloadOverBudgetError: when no rung fits; it names both sizes no rung drops.

    """
    rungs = ladder(len(_shown(req.state)), has_host=bool(host_block(req.state)))
    size = 0
    for rung in rungs:
        body = _compose(req, rung)
        size = len(body)
        if size <= req.budget:
            return body
    standing, step = _kept_sizes(req.state)
    msg = (f"payload is {size} characters even at the last rung; the budget is {req.budget}. "
           f"The standing rules are {standing} characters and the first ready waypoint's "
           f"stanza is {step}; neither is ever dropped. Shorten one, or split the waypoint.")
    raise PayloadOverBudgetError(msg)
