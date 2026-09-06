# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""ONE Bash-command tokenizer, shared by every hook in this package.

⚑⚑ WHY THIS IS ITS OWN MODULE, AND IT IS A MEASURED DEFECT NOT A TIDINESS URGE. The chaining hook
parsed commands with `shlex(punctuation_chars=True)` and tracked COMMAND POSITION across
operators; the structural-query hook did not — it used `cmd.split("|")` then `seg.strip().split()`
and tested ONLY `toks[0]`. So every `timeout 180 grep -n foo x.py` sailed through: `toks[0]` was
`timeout`, the textual tool was never seen, and the gate was open for essentially every command a
session actually issues, because a `timeout` prefix is the default invocation shape. The bypass
was demonstrated live, by the controller, while verifying an unrelated audit.

Two hooks needed the same capability and only one had it. So the tokenizer is lifted HERE and
imported, rather than copied a second time.

⚑⚑ AND THE COPY IS THE POINT OF THE PACKAGE, NOT JUST OF THIS MODULE. `OPERATORS` below was once
duplicated in the chaining hook, whose private copy LACKED `|&` — justified by a comment claiming
shlex "reduces" `|&` to `|` + `&`. It does not: with `punctuation_chars=True` it emits `|&` as ONE
token. So `make |& grep foo x.py` was ALLOWED there while `make | grep foo` was denied. Measured
end-to-end by a peer session with controls on both sides.

⚑⚑⚑ THE ORIGIN TREE ANSWERED THAT WITH A CROSS-CHECK — a `consumer_operators()` function that
imported the other hook at call time and compared the two sets, plus a selftest arm asserting they
agreed. THAT FUNCTION IS DELIBERATELY NOT PORTED, and its absence is the repair rather than a
regression: it existed to detect a divergence between two literals, and inside one distribution
there is only ever one literal to import. A guard against a defect the structure has made
unconstructible is a guard that can only ever report on itself. **The cases it protected are kept
in full** — `|&` still has its own tests here — because those assert what the tokenizer DOES, which
is a fact about shlex and outlives the arrangement of the callers.

⚑ WRAPPERS DO NOT END THE SEARCH. `timeout`, `env`, `xargs`, `sudo`, `nice` and friends are
TRANSPARENT: the real command is behind them. A scan that stops at the first word cannot see it,
which is precisely the bug. `VAR=value` prefixes and a leading `\` (quoting to defeat an alias) are
stripped for the same reason.

⚑ NO SHEBANG — THIS IS AN IMPORTED MODULE, NOT A SCRIPT. The origin tree kept these as files in a
`scripts/` directory, so every one carried a shebang and an exe bit; as package modules they are
imported, and the linter says so.
"""

from __future__ import annotations

import shlex
from pathlib import Path

# Shell operators that START a new command. THIS IS THE AUTHORITY — the single one, now that the
# package holds every consumer. An operator added here is covered everywhere by construction.
OPERATORS: frozenset[str] = frozenset({"|", "||", "&&", ";", "&", "|&"})

# ⚑⚑⚑ REDIRECTION IS DELIBERATELY *NOT* MODELLED, AND THE REFUSAL OF A WRITE IS CORRECT. A
# `WRITE_REDIRECTS` exemption was begun so `cat >> x.py` would pass, treating a peer's report as a
# false positive. Operator ruling, 2026-08-19: *"don't support redirection, support editing"* /
# *"appendation causes files to grow out of control."* A shell append is an unbounded,
# unstructured, unreviewable write to an artifact that has a structural editor.
#
# ⚑⚑ AND THE DAMAGE WAS MEASURED. A `MEMORY.md` staging block appended to and never drained (its
# self-clear regex matched 0 of 44 lines across 167 recorded regens) grew past the 200-line budget
# of the reader that loads it EVERY SESSION. Exempting `>>` would have blessed exactly that
# mechanism — a fix that removes an alarm because the alarm is inconvenient.
#
# ⚑ SO THE GAP WAS IN THE REFUSAL TEXT, NOT THE VERDICT, and it is repaired in the hook's message
# rather than here: a blocked WRITER told to use `Read` gets useless advice, which made a CORRECT
# refusal read as a bug.

# ⚑ TRANSPARENT PREFIXES — a wrapper delegates to the command after it, so finding one means KEEP
# LOOKING, not stop. Every entry here was a live bypass shape.
WRAPPERS: frozenset[str] = frozenset({
    "timeout", "env", "xargs", "command", "builtin", "exec",
    "nice", "ionice", "nohup", "stdbuf", "time", "watch",
    "sudo", "doas", "setsid", "script",
    "uv", "poetry", "pipenv", "hatch", "rye",
})

# A wrapper's own operand — never the program being wrapped.
_UV_SUBCOMMANDS: frozenset[str] = frozenset({
    "run", "tool", "pip", "venv", "sync", "add", "exec", "shell",
})

# ⚑ A duration suffix on a `timeout` operand: `timeout 30s`, `1.5h`.
_DURATION_SUFFIXES = "smhd"

# Wrappers whose first non-flag word is a SUBCOMMAND of the wrapper itself.
_SUBCOMMAND_WRAPPERS: frozenset[str] = frozenset({"uv", "poetry", "pipenv", "hatch", "rye"})

# ⚑⚑⚑ A WRAPPER FLAG THAT TAKES A SEPARATE ARGUMENT HIDES THE PROGRAM BEHIND IT, and that was a
# LIVE BYPASS of the same class this module exists to close — one flag-shape deeper than the
# `timeout 180 grep` case above. MEASURED against this module before the fix:
#
#     env -u LD_PRELOAD grep -n foo notes.md   -> programs() reported ('LD_PRELOAD', ...)
#     sudo -u nobody    grep -n foo notes.md   -> ('nobody', ...)
#     timeout -s KILL 5 grep -n foo notes.md   -> ('KILL', ...)
#     env -C /tmp       grep -n foo notes.md   -> ('tmp', ...)
#
# Four of eight shapes. In every one the real program (`grep`) was never reported, so a hook
# gating on `programs()` was OPEN for those shapes. The flag was skipped correctly; its ARGUMENT
# was then read as the program. Found by a contributor auditing its own code against this repo's
# bar, and reproduced here before the patch was taken.
#
# ⚑⚑ `_is_operand` IS DELIBERATELY NOT WIDENED TO COVER THESE. A flag's argument can be ANY string
# — a signal name, a username, a path — which is value-shaped and would defeat that function's
# conservative "cannot name a program" test, reopening the wrapper bypass to buy this one. The
# arg-taking flags are ENUMERABLE per wrapper; the strings they may carry are not. Quantify over
# the flags, never over their values.
#
# ⚑ ONLY THE SEPARATED FORM NEEDS CONSUMING. `-C/tmp` and `--chdir=/tmp` carry the value in the
# same token, which `_debare` already reads as a flag — consuming a following word for those would
# swallow the real program and turn a bypass into a blindness.
_FLAGS_WITH_ARG: dict[str, frozenset[str]] = {
    "timeout": frozenset({"-s", "--signal", "-k", "--kill-after"}),
    "env": frozenset({"-C", "--chdir", "-u", "--unset", "-S", "--split-string"}),
    "sudo": frozenset({"-u", "--user", "-g", "--group", "-C", "--close-from", "-h", "--host",
                       "-p", "--prompt", "-r", "--role", "-t", "--type", "-U", "--other-user"}),
    "doas": frozenset({"-u", "-C", "-a"}),
    "nice": frozenset({"-n", "--adjustment"}),
    "ionice": frozenset({"-c", "--class", "-n", "--classdata", "-p", "--pid"}),
    "stdbuf": frozenset({"-i", "--input", "-o", "--output", "-e", "--error"}),
    "xargs": frozenset({"-a", "--arg-file", "-E", "-I", "-i", "--replace", "-L", "--max-lines",
                        "-n", "--max-args", "-P", "--max-procs", "-s", "--max-chars", "-d",
                        "--delimiter"}),
    "watch": frozenset({"-n", "--interval", "-d", "--differences"}),
    "script": frozenset({"-c", "--command", "-f", "--flush"}),
}

# ⚑ A bare short flag is exactly two characters: the dash and its letter (`-C`, `-n`). A token
# LONGER than that whose two-character prefix is an arg-taking short flag carries its value GLUED
# (`-C/tmp`), so its argument is not a separate following word.
_SHORT_FLAG_LEN = 2


def _debare(tok: str) -> str | None:
    r"""Reduce a token to the program it names, or None if it names none.

    Strips a leading `\` (alias-defeating quote) and resolves a path to its basename, so
    `/usr/bin/grep` and `\grep` both read as `grep`.
    """
    if not tok:
        return None
    t = tok.lstrip("\\")
    if not t or t.startswith("-"):
        return None
    if "=" in t and not t.startswith("/") and t.split("=", 1)[0].isidentifier():
        return None                      # VAR=value assignment, not a program
    return Path(t).name


def _is_operand(word: str, wrapper: str) -> bool:
    """Report whether `word` is an operand OF the wrapper, not the program it wraps.

    ⚑ CONSERVATIVE BY DESIGN: only forms that CANNOT name a program are consumed. Guessing wrong
    here silently reopens the bypass, so a doubtful token ends the skip and is treated as the
    program.

    Returns:
        whether `word` is an operand OF the wrapper, not the program it wraps.

    """
    if word.replace(".", "", 1).isdigit():                 # timeout 180 / 1.5
        return True
    if word[:-1].replace(".", "", 1).isdigit() and word[-1] in _DURATION_SUFFIXES:
        return True                                        # timeout 30s
    if wrapper in _SUBCOMMAND_WRAPPERS:
        return word in _UV_SUBCOMMANDS
    return False


def tokenize(cmd: str) -> list[str]:
    """Split a command into shell words with operators separated.

    Returns [] if the command will not parse.

    ⚑ AN UNBALANCED QUOTE IS BASH'S VERDICT, NOT OURS: return empty and let the command through
    rather than breaking the session on a parse failure.

    Returns:
        the a command into shell words with operators separated.

    """
    try:
        lx = shlex.shlex(cmd, punctuation_chars=True)
        lx.whitespace_split = True
        return list(lx)
    except ValueError:
        return []


def commands(cmd: str) -> list[list[str]]:
    """Split the command string into its individual commands.

    Each element is one command's words, operators removed. `a | b && c` yields three lists. This
    is what lets a caller ask "is a textual tool in command position ANYWHERE in this line", which
    is the question `toks[0]` could not answer.

    Returns:
        the the command string into its individual commands.

    """
    out: list[list[str]] = []
    cur: list[str] = []
    for tok in tokenize(cmd):
        if tok in OPERATORS:
            if cur:
                out.append(cur)
            cur = []
            continue
        cur.append(tok)
    if cur:
        out.append(cur)
    return out


def programs(cmd: str) -> list[tuple[str, list[str]]]:
    """Return every program INVOKED, seeing through wrappers, with its own arguments.

    ⚑ THE CAPABILITY THE BYPASS PROVED WAS MISSING. `timeout 180 grep -c x f.py` yields
    ('grep', ['-c', 'x', 'f.py']) — the wrapper and its numeric argument are consumed, and the real
    program is reported with the arguments IT receives. A wrapper's own flags (`env -i`,
    `timeout -s KILL`) are skipped too.

    Returns:
        every program INVOKED, seeing through wrappers, with its own arguments.

    """
    found: list[tuple[str, list[str]]] = []
    for words in commands(cmd):
        i = 0
        while i < len(words):
            name = _debare(words[i])
            if name is None:                      # a flag or VAR= prefix: skip it
                i += 1
                continue
            if name in WRAPPERS:
                # ⚑ CONSUME THE WRAPPER *AND ITS OPERANDS*. `timeout 180 grep` puts a DURATION
                # between the wrapper and the real program; a first draft skipped only the wrapper
                # and then reported `180` as the program. An operand that cannot name a program (a
                # number, a duration like `1.5s`, a bare subcommand word for uv/poetry) is skipped;
                # the first token that could be a program ends the skip.
                i += 1
                takes_arg = _FLAGS_WITH_ARG.get(name, frozenset())
                while i < len(words):
                    raw = words[i]
                    nxt = _debare(raw)
                    if nxt is None:                 # a flag: still the wrapper's
                        # ⚑ IF THIS FLAG TAKES A SEPARATE ARGUMENT, CONSUME THAT TOO — else the
                        # argument (`KILL`, `nobody`, `/tmp`) is read as the program and the real
                        # program goes invisible. That is the measured bypass above.
                        bare = raw.lstrip("\\")
                        attached = "=" in bare or (
                            len(bare) > _SHORT_FLAG_LEN and bare[:_SHORT_FLAG_LEN] in takes_arg
                        )
                        i += 1
                        if bare in takes_arg and not attached and i < len(words):
                            i += 1                  # skip the flag's separate argument
                        continue
                    if _is_operand(nxt, name):
                        i += 1
                        continue
                    break
                continue
            found.append((name, words[i + 1:]))
            break                                  # the rest of THIS command is args
    return found
