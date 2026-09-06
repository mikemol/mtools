# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""PreToolUse(Bash) — refuse a COMPOSED command where ONE tool invocation belongs.

⚑ THE SIBLING OF `structural_query`, AND THE SAME FINDING ONE LEVEL OVER. That hook refuses a
TEXTUAL question about a STRUCTURED artifact. This one refuses the COMPOSITION — `&&`, `;`, `|`,
`for` — because a pipeline IS the judgement-not-in-code shape: `tool | tail -5` decides in the turn
what the tool should have had a `--top` mode for; `A && B` sequences two questions a single mode
should answer. Each evaporates when the turn ends and the next reader re-derives it differently.

⚑ PARSE, DO NOT SUBSTRING-MATCH — the false-positive surface IS the design. `grep 'a|b'`,
`awk '{print;n++}'` and `format_for_each.py` all CONTAIN the banned characters and none of them
compose anything. A guard whose first act is to break a working session trains its owner to disable
it, so `shlex(punctuation_chars=True)` does the splitting: a quoted `|` stays inside its token.

⚑⚑ WHY THIS LANDED, AND THE MEASUREMENT THAT FORCED IT (2026-09-06). This repo ran ONE PreToolUse
hook — `structural_query` — while its own plan listed `no_chaining` as adopted. In one session the
absent hook cost three measurement errors of a single class: `substrate/scratch/mdstruct.py … |
tail -1; echo rc=$?` read TAIL's status and reported a peer's tool as exiting 0 on a traceback
(really rc=1, `PIPESTATUS[0]`); `bazel … | grep -q` made bazel take SIGPIPE so a witness arm failed
BECAUSE it matched; and a compound `for` loop tripped the sibling hook twice on an unrelated path.

⚑⚑⚑ THE PIPESTATUS DISCIPLINE WAS ALREADY WRITTEN DOWN — in this repo's own `.githooks/pre-commit`,
as code, after the second instance. It did not transfer to the shell the author types into. That is
this hook's thesis stated against its own author: a judgement that lives in a turn does not survive
the turn, and writing the rule in a comment somewhere else is not the same as a layer that says no.

⚑ ARMED, NOT ADVISORY. `NOCHAIN_HOOK_BLOCK=0` stands it down; otherwise the shared
`STRUCT_HOOK_BLOCK` governs. Advisory mode was measured (linux-sources) to be SILENT TO THE AGENT —
an unarmed hook exits 0 with no `permissionDecision` and the harness reads that as "allow, nothing
to report", so the text reaches nobody. Two states only: armed, or absent.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

from mikemol.hooks import cmdparse

# ⚑⚑ NO `sys.path` PRELUDE, AND ITS ABSENCE IS THE POINT OF THE PACKAGE. The origin carries a
# two-line `sys.path.insert(0, _ROOT)` with a comment explaining that a bare-path invocation puts
# the SCRIPT's directory on `sys.path[0]` and never the repo root — so adopters who tested their
# guards BY MAKING THEM FIRE got `ModuleNotFoundError` and a false ARMED-BUT-INERT red. Five repos
# symlinked the file and the break reached all of them at once.
#
# ⚑⚑⚑ THAT PRELUDE IS A WORKAROUND FOR NOT BEING A PACKAGE, and its own comment says so: *"a
# vendored hook transmits its mechanism, not its preconditions."* An installed distribution has no
# precondition to transmit — `from mikemol.hooks import cmdparse` resolves through the venv the
# console script already runs in, under the harness and under a bare-path probe alike. Porting the
# insert would import the workaround along with the code and re-create the failure it patches.

# The composition operators — each is a place a judgement left the program.
#
# ⚑⚑ MEMBERSHIP IS INHERITED, EXPLANATIONS ARE LOCAL. The origin kept a hand-written literal here
# that LACKED `|&`, justified by a comment claiming shlex "reduces" it to `|` + `&`. It does not:
# with `punctuation_chars=True` it emits `|&` as ONE token, so `make |& grep foo x.py` was ALLOWED
# while `make | grep foo` was denied. A stale comment survived a ruling, an `--explain` that agreed
# for the wrong reason, and a green selftest that proved the arms the hook HAD.
#
# So the set is derived from `cmdparse.OPERATORS` — the one authority — and an operator added there
# is covered here by construction. Only the prose is this hook's own.
_REASONS = {
    "|":  "a pipe — the tool should have the mode that produces this directly",
    "&&": "a sequence — two questions that want one mode, or two calls",
    "||": "a fallback — a shell `case` over an error string is judgement-in-turn",
    ";":  "a sequence — run the calls separately, or add the mode",
    "&":  "a background spawn — use run_in_background, not shell control flow",
    "|&": "a pipe (stdout+stderr) — the tool should have the mode that produces this",
}
OPERATORS: dict[str, str] = {
    op: _REASONS.get(op, "a shell composition — one tool call, or add the mode")
    for op in cmdparse.OPERATORS
}

# ⚑ THE INLINE INTERPRETER IS THE SAME DEFECT WITHOUT A SHELL OPERATOR. `python3 -c "..."` composes
# nothing bash can see, but the program is written in the turn, run once, and discarded. A throwaway
# script is a tool that was never added.
INTERPRETERS = ("python", "python3", "python3.13", "python3.14", "uv", "node", "ruby", "perl",
                "bash", "sh", "zsh")

# The flags meaning "the program is on this command line / on stdin".
INLINE_FLAGS = {
    "-c": "an inline script — this program dies with the turn; put it in a tool",
    "-e": "an inline script — this program dies with the turn; put it in a tool",
}

# Shell control flow. A loop belongs to the tool, not to the turn.
KEYWORDS = {
    "for":   "a loop — the tool should take the whole set and iterate internally",
    "while": "a loop — same: the iteration belongs in a program",
    "until": "a loop — same: the iteration belongs in a program",
    "case":  "a dispatch over strings — the classic judgement-not-in-code shape",
    "if":    "a branch — the decision belongs in the tool that has the data",
}

# ⚑⚑ `cd` IS FLAGGED IN ITS OWN RIGHT. The `&&` already fires on `cd <dir> && cmd`, so the VERDICT
# was never wrong — but the message said only "a sequence", which is true and useless here. A
# refused caller acts on the TEXT, and the text did not name the one-call form that replaces it.
# `cd` also mutates shell state every later command inherits, which an ordinary sequence does not.
DIRECTORY_CHANGE = {
    "cd": ("a directory change — it mutates the shell state every later command "
           "inherits.\n       Use `env -C <dir> <cmd>` (or the tool's own path "
           "argument) so the\n       directory is an INPUT to the one call that "
           "needs it, not an ambient effect."),
}

_STDIN_SCRIPT = ("a stdin script (heredoc) — same as `-c`: it dies with the turn; "
                 "put it in a tool")
_HEREDOC_SCRIPT = ("a heredoc script — same as `-c`: written in the turn, run once, "
                   "discarded")

_HEREDOC_OPEN = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# The fixed tail of every refusal: why this is a defect, what it costs, and what to do instead.
_WHY_TURN = ("  ⚑ the judgement in this pipeline is happening in the TURN, not in a program —\n"
             "     it evaporates when the turn ends and the next reader re-derives it "
             "differently.")
_WHY_RC = ("  ⚑ a pipe also DISCARDS the exit status of every stage but the last: `cmd | tail`\n"
           "     reports TAIL's rc, which is how a tool that failed reads as one that passed.")
_WHAT_TO_DO = ("  run ONE tool call. If no mode answers your question, that is WORK (add the\n"
               "     mode), not grounds for a shell composition — the toolkit expands.")
_SEE_SKILL = "  see .claude/skills/struct-tools/SKILL.md"

# A finding: the token that composed, and why that is judgement-in-the-turn.
Finding = tuple[str, str]


def strip_heredoc_bodies(cmd: str) -> str:
    """Remove heredoc BODIES, keeping the `<<TAG` redirection itself.

    A body is data being handed to a program — a commit message, a config. Its `;` and `|` are
    characters in that data, not operators in this shell. The redirection stays so the
    heredoc-into-interpreter test (about the SHAPE of the call, not its content) still sees it.

    `<<-TAG` and quoted tags (`<<'EOF'`) are both handled; an unterminated heredoc drops the
    remainder, which is the conservative reading — an unterminated body cannot be shell either.

    Returns:
        the heredoc BODIES, keeping the `<<TAG` redirection itself.

    """
    m = _HEREDOC_OPEN.search(cmd)
    if not m:
        return cmd
    head, tag = cmd[:m.end()], m.group(2)
    rest = cmd[m.end():]
    for line_end in re.finditer(r"\n[\t ]*" + re.escape(tag) + r"[\t ]*(?=\n|$)", rest):
        return head + strip_heredoc_bodies(rest[line_end.end():])
    return head


def _mentions_interpreter(toks: list[str]) -> bool:
    """Report whether an interpreter is named anywhere in this command's tokens.

    Returns:
        whether an interpreter is named anywhere in this command's tokens.

    """
    return any(Path(t).name in INTERPRETERS for t in toks)


def _tokenize(cmd: str) -> list[str]:
    """Split a command into shell words, or [] when it will not parse.

    ⚑ An unbalanced quote is bash's verdict, not ours: let it through and let bash report it.
    Never break the session on a parse failure.

    Returns:
        the a command into shell words, or [] when it will not parse.

    """
    try:
        lx = shlex.shlex(cmd, punctuation_chars=True)
        lx.whitespace_split = True
        return list(lx)
    except ValueError:
        return []


def _classify(tok: str, *, found: list[Finding], pending_interp: bool) -> bool:
    """Record any inline-script tell on `tok`; return the new pending-interp state.

    Returns:
        the any inline-script tell on `tok`; return the new pending-interp state.

    """
    if Path(tok).name in INTERPRETERS:
        # ⚑ SEEN ANYWHERE, NOT ONLY IN COMMAND POSITION — `timeout 300 python3 -c`,
        # `uv run --with x python3 -c` and `PYTHONPATH=. python3 -c` all bury the
        # interpreter behind a wrapper or an env prefix.
        return True
    if not pending_interp:
        return False
    if tok in INLINE_FLAGS:
        found.append((tok, INLINE_FLAGS[tok]))
        return False
    if tok == "-":
        found.append(("-", _STDIN_SCRIPT))
        return False
    # ⚑ THE CASE THAT MUST PASS: a real path argument means this is an invocation of a COMMITTED
    # tool, which is exactly what the rule wants — so it ends the flag scan for this command.
    return tok.startswith("-")


def _scan_tokens(toks: list[str]) -> list[Finding]:
    """Walk the token stream once, collecting every composition point.

    Returns:
        the the token stream once, collecting every composition point.

    """
    found: list[Finding] = []
    at_command_start = True
    pending_interp = False       # an interpreter is open; its flags are in scope
    for tok in toks:
        if tok in OPERATORS:
            found.append((tok, OPERATORS[tok]))
            at_command_start = True
            pending_interp = False
            continue
        # ⚑ COMMAND POSITION IS THE DISCRIMINATOR: `for` leading a command is shell control flow;
        # `for` as an argument (`grep -w for notes.md`) or inside a filename is not.
        if at_command_start and tok in KEYWORDS:
            found.append((tok, KEYWORDS[tok]))
        if at_command_start and tok in DIRECTORY_CHANGE:
            found.append((tok, DIRECTORY_CHANGE[tok]))
        pending_interp = _classify(tok, found=found, pending_interp=pending_interp)
        at_command_start = False
    return found


def analyze(cmd: str) -> list[Finding]:
    """Return the composition points in one Bash command string.

    Parses rather than scans: a `|` inside quotes is data, a `|` between two words is an operator,
    and `for` is a keyword only in command position.

    ⚑ A HEREDOC BODY IS DATA, NOT COMPOSITION. `git commit -F - <<EOF` carries PROSE, and prose
    contains `;` and `|` — a commit message describing a shell pipeline. Scanned as shell, every one
    reads as an operator, and the hook refuses a single tool call for the content of its own
    argument. The body is stripped BEFORE tokenising, and only the body.

    Returns:
        composition points in one Bash command string.

    """
    toks = _tokenize(strip_heredoc_bodies(cmd))
    found = _scan_tokens(toks)

    # ⚑ A HEREDOC INTO AN INTERPRETER YIELDS NO `-c` AND NO `-` TOKEN — the redirection itself is
    # the only tell. Test for the redirection rather than for a still-open interpreter: a bare
    # `python3` with no args is a REPL, not a script.
    if (any(t.startswith("<<") for t in toks)
            and _mentions_interpreter(toks)
            and not any(t in {"-", "-c", "-e"} for t, _ in found)):
        found.append(("<<", _HEREDOC_SCRIPT))

    # dedupe, preserving first-seen order
    seen: set[str] = set()
    out: list[Finding] = []
    for tok, why in found:
        if tok not in seen:
            seen.add(tok)
            out.append((tok, why))
    return out


def command_of(payload: object) -> str:
    """Extract the Bash command from a PreToolUse payload, or "" if absent.

    ⚑⚑ `object` IS THE HONEST TYPE OF AN UNTRUSTED VALUE; `Any` IS THE DISHONEST ONE. The payload
    arrives as untyped JSON, and every level is narrowed with a real runtime `isinstance` before
    anything is read from it — a check, not an assertion. A `cast` would ASSERT what this VALIDATES,
    and a guard that mis-reads its input renders a verdict about something other than what ran.

    Returns:
        the the Bash command from a PreToolUse payload, or "" if absent.

    """
    if not isinstance(payload, dict):
        return ""
    raw_input = payload.get("tool_input")
    if not isinstance(raw_input, dict):
        return ""
    command = raw_input.get("command")
    return command if isinstance(command, str) else ""


def deny_payload(reason: str) -> str:
    """Render a PreToolUse deny decision as JSON.

    ⚑ THE NESTED DICT IS BUILT THROUGH TYPED LOCALS. Written inline as
    `json.dumps({"hookSpecificOutput": {…}})` the INNER literal is inferred on its own as
    `dict[Any, Any]` — the call site gives it nothing to check against — and `disallow_any_expr`
    refuses it.

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


def armed() -> bool:
    """Report whether this hook should DENY rather than advise.

    ⚑ AN EXPLICIT OFF MUST WIN OVER THE SHARED ON. `STRUCT_HOOK_BLOCK` arms both hooks as a
    convenience, but reading it as a bare `or` makes `NOCHAIN_HOOK_BLOCK=0` unable to stand this
    hook down while its sibling blocks — the per-hook switch has to be able to override the shared
    one, or staging one hook ahead of the other is impossible.

    Returns:
        whether this hook should DENY rather than advise.

    """
    own = os.environ.get("NOCHAIN_HOOK_BLOCK")
    if own is not None:
        return own == "1"
    return os.environ.get("STRUCT_HOOK_BLOCK") == "1"


def refusal(found: list[Finding]) -> str:
    """Build the refusal TEXT, so a test can read what the hook says.

    Returns:
        the the refusal TEXT, so a test can read what the hook says.

    """
    lines = ["no-chaining: this command COMPOSES where one tool call belongs."]
    lines.extend(f"  `{tok}`  {why}" for tok, why in found)
    # ⚑ THE TAILS ARE MODULE CONSTANTS, NOT INLINE LITERALS, AND THE FIRST FIX WAS WRONG.
    # `repeated-append` correctly objected to four `.append` calls; rewriting them as one
    # `extend` over a tuple of implicitly-concatenated strings traded one preview key for
    # THREE (`ISC004`). Hoisting the text out is the fix that satisfies both: one `extend`
    # over named constants, no adjacent-string literals inside a collection.
    lines.extend((_WHY_TURN, _WHY_RC, _WHAT_TO_DO, _SEE_SKILL))
    return "\n".join(lines)


def main() -> int:
    """Read the PreToolUse payload from stdin and refuse or allow the command.

    ⚑ THE EXCEPTIONS ARE NAMED. A bare `except Exception` would swallow a bug in this hook's own
    logic and return 0 — i.e. ALLOW — making a broken gate indistinguishable from a passing one.
    Only a malformed payload is tolerated.

    Returns:
        the the PreToolUse payload from stdin and refuse or allow the command.

    """
    try:
        payload: object = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError, OSError):
        return 0                      # never break the session on a parse failure
    cmd = command_of(payload)
    if not cmd.strip():
        return 0

    found = analyze(cmd)
    if not found:
        return 0

    msg = refusal(found)
    if armed():
        sys.stdout.write(deny_payload(msg) + "\n")
        return 0
    sys.stderr.write(msg + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
