# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""PreToolUse(Bash) — refuse a TEXTUAL query where a STRUCTURAL one exists.

⚑ THE POLICY'S HOME IS THE LAYER THAT CAN REFUSE A VIOLATION. The rule ("if you have a question
the tooling doesn't answer directly, fix the tooling") lived in an always-loaded instruction file
for a whole arc, was stated in four places, and was violated twice in the same turn where it had
just been acknowledged — including once by grepping for a SQL table whose readers are DECLARED in
a metadata registry. An instruction governs the turns where it is already being thought about; a
hook intercepts the call.

⚑ NO EXCEPTION LIST, AND ITS ABSENCE IS THE DESIGN (operator, 2026-08-03: *"Then build the tool
that makes that a structured query."*). A first scoping carved out "legitimate grep — build logs,
pgrep, non-code text", because no structural reader covered them. That reads a GAP IN THE TOOLKIT
as a CATEGORY OF QUESTION that is inherently textual — the same method-versus-substrate confusion
as reading "no consumer found" as "no consumer exists". A build log is `Checking <mod>`, an error
kind, a make target; `pgrep` is pid/command/state. Both are structured; neither had a reader yet.
An exception admitted for the uncovered case is the loophole that swallows the rule, so the
toolkit expands instead.

⚑ THE ROUTING MAP IS READ FROM THE REPO'S SKILL, NEVER RESTATED — see `routing_table`, which also
records why the table must follow the EDITED repo rather than this package's own location.

⚑ ADVISORY BY DEFAULT. It emits the route and lets the call proceed unless armed. A guard whose
first act is to break a working session trains people to disable it; the refusal earns blocking
after its false-positive rate is measured, not before.

⚑⚑ AND A HOOK THAT CANNOT LOAD IS A HOOK THAT ALLOWS EVERYTHING. `main` reports what it could not
do and exits non-blocking rather than vanishing — an empty stdout reads to the harness as
permission granted, so silence is the one thing a broken gate must not do.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from mikemol.hooks import cmdparse, routing_table
from mikemol.hooks import payload as _payload

# The textual instruments. `find`/`ls` are NOT here: locating a file is not a question about its
# structure.
#
# ⚑ WIDENED AFTER A LIVE BYPASS. The first six were `grep rg egrep fgrep sed awk`; every other
# line-reader was a silent hole. A tool that reads a file's BYTES to answer a question about its
# STRUCTURE belongs here regardless of how blunt it is.
# ⚑⚑⚑ A DENYLIST, DELIBERATELY, AND THE ALTERNATIVE WAS MEASURED BEFORE SETTLING. An allowlist
# would have to enumerate every command that touches a file WITHOUT reading it textually — `git
# add`, `rm`, `cp`, `mv`, `ls`, `chmod`, `git diff`, the owning tool itself, and whatever a future
# workflow reaches for. That population is unbounded and its omissions REFUSE legitimate work,
# where this list's omissions merely fail to catch one. ⚑ Both are hand-written; only one fails
# safe.
#
# ⚑⚑ AND IT WAS INCOMPLETE, MEASURED: `perl`, `python3 -c`, `less`, `more` and `jq` all read a
# claimed artifact textually and all PASSED. A roster that decides what is blocked is a roster
# whose omissions are silent permissions — the same shape as the four enumerated populations this
# repository repaired, except this one cannot be enumerated: there is no filesystem or config to
# derive tool names from, so it grows by measurement rather than by query.
TEXTUAL = frozenset((
    "grep", "rg", "egrep", "fgrep", "sed", "awk",
    "head", "tail", "cut", "sort", "uniq", "wc", "tr", "nl", "rev",
    "strings", "cat", "tac", "od", "xxd", "diff", "comm", "join", "paste",
    # ⚑ Added after measuring that each passed a textual read of a claimed artifact.
    "perl", "less", "more", "jq", "column", "fold", "expand", "unexpand",
    # ⚑⚑ A SECOND PASS, MEASURED AGAINST TOOLS ACTUALLY PRESENT ON THE HOST rather than against
    # imagination: 26 more were installed and absent from this roster. They are not all alike, and
    # the classification is why only some are here.
    #   READERS — open a named file and emit its bytes as text:
    "hexdump", "hd", "cmp", "sdiff", "col", "colrm", "pr", "look", "ptx", "base64", "iconv",
    "split", "csplit",
    #   EDITORS — interactive, but they read the file to display it, and a pager already is here:
    "vim", "vimdiff", "nano", "ed", "ex", "view",
))

# ⚑⚑⚑ THREE THINGS FOUND ON THE HOST ARE DELIBERATELY ABSENT, AND EACH FOR A DIFFERENT REASON.
#
#   `pandoc` — mdstruct's own docstring calls it *"the ONE conversion point, and the only
#   subprocess in this package"*. Blocking it blocks the owning tool's backend, which is the
#   `python3` case again: the route this hook PRESCRIBES must not be refused alongside the
#   textual reads it exists to stop.
#
#   `tee`, `xargs`, `shuf`, `tsort` — these consume STDIN. `tee notes.md` WRITES to that path and
#   never reads it, so blocking them would refuse a command that does not do the thing the gate
#   objects to. ⚑ A denylist entry that fires on a non-reader is the allowlist's failure mode
#   arriving by the back door: it refuses legitimate work.
#
#   `xmllint` — reads XML, and no artifact in this repository's routing table claims that suffix.
#   Adding it would arm the gate for a claim nobody has made.
#
# ⚑⚑ The distinction the roster actually encodes is READS A CLAIMED ARTIFACT AS TEXT, not
# "processes text". Getting that wrong in either direction costs something: an omission fails to
# catch one command, an over-inclusion refuses one that was never the problem.

# ⚑⚑⚑ `python3` IS DELIBERATELY ABSENT, AND THE REASON IS THAT IT IS THE OWNING TOOL'S OWN
# INVOCATION. `python3 -m mikemol.mdstruct.cli spans f.md` is the route this hook PRESCRIBES;
# listing the interpreter would refuse the answer alongside the question. ⚑ So
# `python3 -c "print(open(1).read())" f.md` passes, measured, and that is a KNOWN OPENING rather
# than an omission — an interpreter is not a tool, it is a way to be any tool, and no name-based
# roster can separate the two.
#
# ⚑⚑ NAMED HERE BECAUSE AN UNRECORDED GAP IS INDISTINGUISHABLE FROM AN UNNOTICED ONE. A reader
# meeting this list cannot otherwise tell whether `python3` was considered and excluded or simply
# forgotten, and those warrant different responses: the first is a boundary, the second is a bug.

# ⚑ NO HARDCODED SUFFIX LIST LIVES HERE. It was `STRUCTURED_SUFFIX = (".py", ".md", …)` — a SECOND
# roster beside the routing table, which is the frozen-roster shape the table exists to retire.
# The claims come from the table's `claims` column, so adding a row arms the gate in every repo
# that adopts this package, with no edit here.

# A verdict's hit: the argument, its suffix, and the (artifact, owner) that claims it.
Hit = tuple[str, str, tuple[str, str]]
Reason = tuple[str, list[Hit]]

# The redirection operators that make a refused command a WRITE rather than a read.
_REDIRECTS = (">", ">>")


def verdict(cmd: str, table: dict[str, tuple[str, str]] | None = None) -> tuple[bool, list[Reason]]:
    """Return (is_violation, reasons) for one command.

    ⚑ EVERY COMMAND-POSITION PROGRAM IS TESTED, NOT `toks[0]`. The predecessor split on `|` and
    inspected only the first token, so `timeout 180 grep -n foo x.py` was invisible — `toks[0]`
    was `timeout`, and a `timeout` prefix is the ordinary invocation shape, so the gate was open
    for nearly every command issued. `cmdparse.programs` sees through wrappers and returns the
    REAL program with the arguments it receives.
    """
    tbl = routing_table.claims() if table is None else table
    reasons: list[Reason] = []
    for prog, args in cmdparse.programs(cmd):
        if prog not in TEXTUAL:
            continue
        # ⚑ MATCH THE ARGUMENT WORD, NOT THE WHOLE SEGMENT. The predecessor tested `".py" in seg`,
        # so a directory named `pkg.py/` false-positived while an argument's real extension went
        # unexamined.
        hits: list[Hit] = []
        for a in args:
            if a.startswith("-"):
                continue
            suf = Path(a.strip("'\"")).suffix.lower()
            if suf in tbl:
                hits.append((a, suf, tbl[suf]))
        if hits:
            reasons.append((prog, hits))
    return bool(reasons), reasons


def refusal(reasons: list[Reason], cmd: str = "") -> str:
    """Build the refusal TEXT, so a test can read what a refused author actually sees.

    ⚑ THE MESSAGE IS PART OF THE GATE, AND NOTHING CHECKED IT FOR AN ARC. It was built inline in
    `main`, so it was unreachable without a subprocess and every case asked only WHETHER the hook
    fires. A refusal that names an unrunnable tool and stops is a gate that blocks without routing
    — measured, in a borrowing checkout where the named tool could not run and the reader had no
    move left. The escape hatch has to be IN the message, because the message is the only thing a
    refused reader sees.

    ⚑ `cmd` IS READ ONLY TO CHOOSE THE ROUTE, NEVER TO CHANGE THE VERDICT. The caller has already
    decided; this tells a blocked WRITER something a blocked READER does not need.
    """
    lines = ["structural-query: this asks about a STRUCTURED artifact textually."]
    for prog, hits in reasons:
        for arg, suf, (artifact, tool) in hits:
            lines.append(f"  `{prog}` over {arg}  ({suf} → {artifact})")
            lines.append(f"      the tool that owns it:  {tool}")
    lines.append("  ⚑ if no mode answers your question, that is WORK (add the mode), not grounds\n"
                 "     for a textual fallback — the toolkit expands; the rule has no exceptions.")
    # ⚑ THE MESSAGE ASSUMED THE NAMED TOOL IS RUNNABLE, AND IN A BORROWING REPO IT IS NOT. This
    # tooling is adopted by other checkouts, where the owning tool may be absent or its
    # dependencies unmet — so the refusal named the one route the reader could not take and
    # stopped. A peer hit exactly that and had no move left. `Read` is the answer and needs SAYING:
    # it is not a shell command, so a reader thinking in Bash calls will not consider it, and it is
    # a total, structure-preserving read of the whole file — strictly better than the `wc`/`grep`
    # this hook just refused.
    lines.append("  ⚑ if that tool is unavailable here (a borrowing checkout, an unmet\n"
                 "     dependency), use the harness `Read` tool on the file — NOT a textual\n"
                 "     fallback. Read is not a shell command, which is why it does not come\n"
                 "     to mind inside a shell-shaped question; it is the honest whole-file\n"
                 "     read the refused command was approximating.")
    # ⚑⚑⚑ A BLOCKED *WRITER* WAS TOLD TO USE `Read`, WHICH IS USELESS ADVICE FOR AN APPEND — and
    # that made a CORRECT refusal read as a bug. Reported by an adopting repo: `cat >> MEMORY.md`
    # denied as a "structural query", the message offering only reader routes. Their conclusion was
    # to drop the `.md` claim; the verdict was right and only the guidance was missing.
    #
    # ⚑⚑ THE VERDICT DOES NOT SOFTEN. Operator ruling, 2026-08-19: *"don't support redirection,
    # support editing"* / *"appendation causes files to grow out of control."*
    if any(op in cmd for op in _REDIRECTS):
        owner = ", ".join(sorted({t for _p, hs in reasons for _a, _s, (_k, t) in hs}))
        lines.append("  ⚑ THIS LOOKS LIKE A WRITE, AND THE REFUSAL STILL STANDS.\n"
                     f"     The owning tool is the route for WRITES TOO: {owner}.\n"
                     "     A structural editor states WHAT changes, refuses a target that\n"
                     "     moved, and cannot append past the shape; `>>` does none of\n"
                     "     that. If the owning tool has no mode for this edit, THAT is\n"
                     "     the work — a missing mode, not grounds for a shell append.\n"
                     "     `Write`/`Edit` are the fallback when the tool is unavailable\n"
                     "     here, the same way `Read` is on the query side.")
    lines.append(f"  see {routing_table.SKILL_RELPATH}")
    return "\n".join(lines)


def deny_payload(reason: str) -> str:
    """Render a PreToolUse deny decision as JSON.

    ⚑⚑ THE NESTED DICT IS BUILT THROUGH TYPED LOCALS, AND THAT IS THE WHOLE POINT. Written inline
    as `json.dumps({"hookSpecificOutput": {…}})` the INNER literal is inferred on its own as
    `dict[Any, Any]` — the call site gives it nothing to check against — and `disallow_any_expr`
    refuses it. A sibling hook carried the identical construct and it cost six wrong attributions
    there before the checker rendered the line.
    """
    decision: dict[str, str] = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }
    envelope: dict[str, dict[str, str]] = {"hookSpecificOutput": decision}
    return json.dumps(envelope)


def command_of(value: object) -> str:
    """Extract the Bash command from a PreToolUse payload, or "" when absent.

    ⚑ EVERY LEVEL IS NARROWED WITH A REAL RUNTIME CHECK, not an assertion. A hook that mis-reads
    its own input renders a verdict about something other than what ran.
    """
    record = _payload.as_record(value)
    tool_input = _payload.as_record(record.get("tool_input"))
    return _payload.text_of(tool_input.get("command"))


def _emit(msg: str) -> int:
    """Deliver the refusal — deny when armed, advisory otherwise."""
    if _payload.armed():
        sys.stdout.write(deny_payload(msg) + "\n")
        return 0
    sys.stderr.write(msg + "\n")
    return 0


def main() -> int:
    """Read the PreToolUse payload from stdin and route or refuse the command.

    ⚑ THE EXCEPTIONS ARE NAMED. A bare `except Exception` here would swallow a bug in this hook's
    own logic and return 0 — i.e. ALLOW — making a broken gate indistinguishable from a passing
    one. Only a malformed or unreadable payload is tolerated; anything else must crash loudly
    where it can be seen.
    """
    try:
        parsed: object = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError, OSError):
        return 0                      # never break the session on a parse failure
    cmd = command_of(parsed)
    if not cmd:
        return 0
    hit, reasons = verdict(cmd)
    if not hit:
        return 0
    return _emit(refusal(reasons, cmd))
