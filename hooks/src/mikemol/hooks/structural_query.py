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


# ⚑⚑⚑ PROGRAMS WHOSE FIRST NON-FLAG ARGUMENT IS A PATTERN, NOT A PATH. Reported by cassian after
# `grep -n "SKILL.md" x.py` routed a PYTHON file to the markdown owner: the scan read every
# non-flag argument, and for these the first one is what you are searching FOR.
# ⚑⚑ THE SET IS ENUMERATED AND `cat`/`head`/`wc` ARE DELIBERATELY OUTSIDE IT. They take no
# pattern, so dropping THEIR first argument would blind the guard to an ordinary read — which is
# how a fix becomes a de-arming. cassian named that trap and avoided it; the arms in
# `test_a_real_target_after_the_pattern_still_fires` are what hold it here.
_PATTERN_FIRST = frozenset(("grep", "rg", "egrep", "fgrep", "ag", "ack"))

# ⚑⚑ FLAGS THAT CARRY THE PATTERN AS THEIR ARGUMENT. `grep -e PAT file` puts the pattern after a
# flag, so position alone does not find it. ⚑ MEASURED AS A DIVERGENCE FROM cassian'S TREE, not
# inherited: they reported `_FLAGS_WITH_ARG` consuming `-e` before the scan sees it, and here it
# does NOT — that table covers WRAPPERS (timeout, env, sudo, xargs), never the textual programs.
# A fix copied from their report alone would have left this shape firing.
_PATTERN_FLAGS = frozenset(("-e", "--regexp", "-f", "--file"))

# ⚑ THE HEREDOC OPERATORS, AND ONLY THOSE. `>` and `>>` name a DESTINATION that stays in scope —
# see `_scannable` for the operator ruling that makes a redirected write a refusal.
_HEREDOC_OPS = frozenset(("<<", "<<-"))


def _without_heredoc_bodies(args: list[str]) -> list[str]:
    """Drop the tokens strictly between each heredoc tag and its terminator.

    ⚑ THE TAG NAMES ITS OWN TERMINATOR — `<<EOF` ends at the next bare `EOF` — so the body is
    bounded rather than open-ended. An unterminated tag swallows the remainder, which is the safe
    direction: a body token read as an argument would REFUSE a command that reads nothing.

    Returns:
        the arguments with every heredoc body removed.

    """
    out: list[str] = []
    i = 0
    while i < len(args):
        if args[i] not in _HEREDOC_OPS:
            out.append(args[i])
            i += 1
            continue
        # ⚑ `<<` then its TAG; the body runs until that tag appears again as its own token.
        i += 1
        if i >= len(args):
            break
        tag = args[i].strip("'\"")
        i += 1
        while i < len(args) and args[i].strip("'\"") != tag:
            i += 1
        i += 1  # step over the terminator itself
    return out


def _scannable(prog: str, args: list[str]) -> list[str]:
    """Return the arguments that name artifacts this command READS.

    ⚑⚑⚑ TWO SHAPES ARE EXCLUDED, AND BOTH WERE MEASURED AS LIVE DEFECTS:

    * a SEARCH PATTERN — for `grep` and friends the first non-flag argument, or the argument of
      `-e`/`-f`, is what you search FOR rather than a file you open.
    * a REDIRECTED WRITE — `cat > x.py <<EOF ... EOF` reports as `cat` with the redirection target
      and the whole heredoc body in `args`, so a claimed suffix appearing anywhere in the body was
      read as a textual query. The command CREATES a file; it reads nothing.

    ⚑ THE DISCRIMINATOR FOR THE SECOND IS THE REDIRECTION, NOT THE PROGRAM. Keying on `cat` would
    disarm `cat notes.md`, which is exactly what this gate is for.

    Returns:
        the arguments worth testing against the claims table.

    """
    # ⚑⚑⚑ ONLY THE HEREDOC BODY IS DROPPED, AND A FIRST CUT DROPPED THE REDIRECTION TARGET TOO —
    # WHICH TWO EXISTING ARMS REFUSED, CORRECTLY. `cat >> scratch/tool.py` is a shell APPEND to a
    # claimed artifact, and the gate refuses it on an operator ruling recorded in
    # `test_a_shell_append_to_a_claimed_artifact_still_fires`: *"don't support redirection, support
    # editing"* / *"appendation causes files to grow out of control"*. That arm's own comment says
    # an earlier fix exempting `>>` was the wrong repair AND NAMES THE MEASURED DAMAGE — a staging
    # block appended to and never drained outgrew the budget of the reader loading it every
    # session. I reproduced that exact wrong repair; the arm is what caught it.
    #
    # ⚑⚑ SO THE DISCRIMINATOR IS THE HEREDOC, NOT REDIRECTION IN GENERAL. `>` and `>>` name a
    # DESTINATION, which is a real artifact being written and stays in scope. `<<` introduces a
    # BODY — arbitrary text the command creates, never a path it touches — and everything from the
    # delimiter onward is that body.
    # ⚑⚑⚑ ONLY THE TOKENS BETWEEN THE TAG AND ITS TERMINATOR, AND MY FIRST CUT DROPPED EVERYTHING
    # AFTER `<<` — WHICH LOSES A REAL CATCH. cassian built the terminator-aware bound and I
    # measured the difference here rather than adopting the description:
    #
    #     A heredoc write, its terminator, and then a grep of a claimed artifact tokenise into ONE
    #     invocation whose arguments run from the redirection through the grep's own target.
    #     Dropping from the tag onward left only the redirection and its destination — the grep
    #     vanished. Bounding at the terminator keeps the grep and its target in the scan.
    #
    # The tokeniser does not split on the newline after the terminator, so a heredoc followed by
    # ANY command folded that command into the same invocation. Ordinary shell, not an exotic case.
    #
    # ⚑⚑ AN UNTERMINATED TAG TREATS THE REST AS BODY, and that direction is deliberate — cassian's
    # reasoning, which holds on inspection: a body token read as an ARGUMENT is a FALSE REFUSAL of
    # a command that reads nothing, while an argument read as BODY is a missed catch in a command
    # that is WRITING. The first blocks work that is fine; the second lets through a write whose
    # destination is still scanned.
    # ⚑ FROZENSET, NOT A TUPLE LITERAL: ruff's preview `literal-membership` refuses the inline
    # form and the ratchet minted a key for it. Fixed in the file rather than the baseline.
    args = _without_heredoc_bodies(args)

    if prog not in _PATTERN_FIRST:
        return [a for a in args if not a.startswith("-")]

    # ⚑ THE PATTERN IS DROPPED ONCE: either the argument of a pattern-taking flag, or — failing
    # that — the first bare word. A command with only a pattern and no file then scans nothing,
    # which is correct: it reads stdin.
    out: list[str] = []
    skip_next = False
    dropped_first = False
    for a in args:
        if skip_next:
            skip_next = False
            dropped_first = True
            continue
        if a in _PATTERN_FLAGS:
            skip_next = True
            continue
        if a.startswith("-"):
            continue
        if not dropped_first:
            dropped_first = True
            continue
        out.append(a)
    return out


def verdict(cmd: str, table: dict[str, tuple[str, str]] | None = None) -> tuple[bool, list[Reason]]:
    """Return (is_violation, reasons) for one command.

    ⚑ EVERY COMMAND-POSITION PROGRAM IS TESTED, NOT `toks[0]`. The predecessor split on `|` and
    inspected only the first token, so `timeout 180 grep -n foo x.py` was invisible — `toks[0]`
    was `timeout`, and a `timeout` prefix is the ordinary invocation shape, so the gate was open
    for nearly every command issued. `cmdparse.programs` sees through wrappers and returns the
    REAL program with the arguments it receives.

    Returns:
        (is_violation, reasons) for one command.

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
        for a in _scannable(prog, args):
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

    Returns:
        the the refusal TEXT, so a test can read what a refused author actually sees.

    """
    lines = ["structural-query: this asks about a STRUCTURED artifact textually."]
    for prog, hits in reasons:
        for arg, suf, (artifact, tool) in hits:
            lines.extend((
                f"  `{prog}` over {arg}  ({suf} → {artifact})",
                f"      the tool that owns it:  {tool}",
            ))
    # ⚑ THE SECOND LINE EXISTS BECAUSE THE MESSAGE ASSUMED THE NAMED TOOL IS RUNNABLE, AND IN A
    # BORROWING REPO IT IS NOT. This tooling is adopted by other checkouts, where the owning tool
    # may be absent or its dependencies unmet — so the refusal named the one route the reader could
    # not take and stopped. A peer hit exactly that and had no move left. `Read` is the answer and
    # needs SAYING: it is not a shell command, so a reader thinking in Bash calls will not consider
    # it, and it is a total, structure-preserving read of the whole file — strictly better than the
    # `wc`/`grep` this hook just refused.
    # ⚑⚑ THE EXPLANATION SITS ABOVE BOTH RATHER THAN BETWEEN THEM, which is what lets these be one
    # `extend`. It previously separated two `append` calls, and a comment standing between two
    # halves of one emission reads as if it governs only the half beneath it.
    lines.extend((
        # ⚑ EACH ELEMENT PARENTHESISED, because inside a collection literal an implicit
        # concatenation and a forgotten comma are the SAME BYTES — two elements silently becoming
        # one, which is exactly this emission's failure mode. The parentheses say which was meant.
        ("  ⚑ if no mode answers your question, that is WORK (add the mode), not grounds\n"
         "     for a textual fallback — the toolkit expands; the rule has no exceptions."),
        ("  ⚑ if that tool is unavailable here (a borrowing checkout, an unmet\n"
         "     dependency), use the harness `Read` tool on the file — NOT a textual\n"
         "     fallback. Read is not a shell command, which is why it does not come\n"
         "     to mind inside a shell-shaped question; it is the honest whole-file\n"
         "     read the refused command was approximating."),
    ))
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

    Returns:
        the a PreToolUse deny decision as JSON.

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

    Returns:
        the the Bash command from a PreToolUse payload, or "" when absent.

    """
    record = _payload.as_record(value)
    tool_input = _payload.as_record(record.get("tool_input"))
    return _payload.text_of(tool_input.get("command"))


def _emit(msg: str) -> int:
    """Deliver the refusal — deny when armed, advisory otherwise.

    Returns:
        The process exit code. ⚑⚑ IT IS 0 IN BOTH BRANCHES, AND THAT IS THE POINT RATHER THAN AN
        OVERSIGHT: this hook speaks to the harness through its STDOUT payload, not its status, so
        an armed refusal exits 0 carrying a `deny` decision. A nonzero exit would read as *the
        hook crashed*, which the harness treats as no decision at all — the fail-open shape this
        repository refuses everywhere else.

    """
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

    Returns:
        the the PreToolUse payload from stdin and route or refuse the command.

    """
    try:
        parsed: object = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError, OSError):
        return 0                      # never break the session on a parse failure
    cmd = command_of(parsed)
    if not cmd:
        return 0
    # ⚑⚑⚑ AN EMPTY ROUTING TABLE ALLOWS EVERY COMMAND, SILENTLY. `claims()` resolves the table
    # relative to the CWD, so a hook invoked from anywhere without a `.claude/skills/` tree reads
    # ZERO claims and every textual read of every artifact passes. ⚑ MEASURED: from `hooks/` the
    # table holds 0 entries and a plain `grep` of a claimed artifact returns a clean verdict; from
    # the repo root it holds 1 and the same command refuses. The gate reads as armed either way.
    # ⚑⚑ THIS IS THE SHAPE THE HOOK ITSELF EXISTS TO REFUSE — a check whose silence is
    # indistinguishable from a pass — and it is the shape this repository refused from a peer's
    # `check_scratch_runtime.py`, which printed SKIPPED and exited 0. Absence of the table is
    # reported rather than skipped, so a misconfigured hook is visible instead of open.
    # ⚑ IT DOES NOT REFUSE THE COMMAND. A hook that blocked every Bash call on a missing table
    # would take the session down over its own configuration; the honest act is to say the gate
    # is not covering anything and let the command through.
    if not routing_table.claims():
        sys.stderr.write(
            "structural-query: ⚑ NO ROUTING TABLE resolved from "
            f"{routing_table.project_dir()} — this gate is allowing every command.\n"
            "  It is not armed here: a textual read of a claimed artifact would pass unseen.\n"
        )
        return 0
    hit, reasons = verdict(cmd)
    if not hit:
        return 0
    return _emit(refusal(reasons, cmd))
