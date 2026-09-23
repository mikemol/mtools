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
    # ⚑⚑⚑ `script` IS NOT HERE, AND ITS PRESENCE READ A PATH AS A PROGRAM. Membership means *the
    # real program follows this token*, which holds for `setsid grep …` and fails for
    # `script -c 'grep x' /dev/null`: the wrapped program is INSIDE the quoted argument, and the
    # token after it is the typescript FILE. MEASURED before the repair: `programs()` reported
    # `null`.
    # ⚑⚑ FOUND BY `cassian-observability`, who drove both copies of this module over 17 commands
    # rather than reading them — 0 disagreements, and this one shape wrong in both. They named
    # `sudo -C` and `xargs -I` as worth checking for the same property and explicitly did NOT
    # claim they shared it; measured, both are correct, because for those the program really does
    # follow.
    # ⚑ IT STAYS IN `_FLAGS_WITH_ARG` so `-c`'s argument is still consumed rather than read as a
    # program. The two tables answer different questions: one asks *does a program follow*, the
    # other *does this flag take an argument*, and `script` is yes to the second and no to the
    # first.
    # ⚑⚑ THE BOUND, STATED RATHER THAN CLOSED: the wrapped program is not recovered, because
    # recovering it means parsing shell out of an opaque token. `script` reports `script`, which
    # is what `sh -c` and `bash -c` already report and what the routing hook relies on when it
    # refuses `python3 -c` by naming the interpreter.
    "sudo", "doas", "setsid",
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

    Returns:
        The bare program name, or `None` when the token names no program at all — an empty
        token, a flag, or a `VAR=value` assignment prefix. ⚑ `None` IS LOAD-BEARING RATHER THAN
        AN ERROR CASE: `programs()` uses it to decide a token belongs to a wrapper rather than
        naming the command, and reading it as "no program here, move on" is what keeps a flag's
        ARGUMENT from being reported as the program — the measured bypass this module closes.

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

    ⚑ A NEWLINE THAT ENDS A COMMAND COMES BACK AS A `;` TOKEN — see `separate_lines`.

    Returns:
        the a command into shell words with operators separated.

    """
    try:
        lx = shlex.shlex(separate_lines(cmd), punctuation_chars=True)
        lx.whitespace_split = True
        return list(lx)
    except ValueError:
        return []


# ⚑⚑⚑ A HEREDOC BODY IS STDIN DATA, NEVER ARGV — AND THE TOKENIZER READ IT AS SHELL. MEASURED on
# HEAD: `cat >> ledger <<'EOF'` whose body held `step; grep x notes.md` was REFUSED by the
# structural-query hook, because shlex split the body's `;` as an operator and the body's second
# half became a `grep` in command position. The same body carrying an apostrophe went the other
# way: shlex raised on the unbalanced quote, `tokenize` returned [], and a REAL read after the
# terminator passed unseen. Both are one defect — the body was never removed before tokenizing.
#
# ⚑⚑ SO THE BODY IS CUT HERE, ONCE, before any consumer sees a token, on bash's own rules:
#   * the operator is `<<` or `<<-` OUTSIDE quotes and comments; `<<<` is a HERE-STRING, whose
#     word is an ordinary shell word and stays exactly as it was.
#   * the delimiter is the word after the operator with its quoting removed (`'EOF'`, `"EOF"`,
#     `\EOF` all end at a bare `EOF` line); several heredocs on one line take their bodies in order.
#   * a body ends at a line that IS the delimiter — `<<-` first strips leading TABS. A line that
#     merely CONTAINS the delimiter (`see EOF here`) is body.
#   * an unterminated body runs to the end, as bash reads it.
# ⚑ THE BODY IS REPLACED BY A NEWLINE, because the line after a terminator starts a NEW command,
# and a newline IS a separator now that `separate_lines` reads it as one. It was once `\n;\n`,
# written while the tokenizer ignored newlines; a literal `;` would read as chaining to a hook
# that refuses `;` (no-chaining imports this stripper), and a heredoc line ending in `|` must
# continue onto the line after the terminator, as bash reads it.
_HEREDOC_WORD_END = frozenset(" \t\n;|&<>()")
_QUOTES = frozenset("'\"")
_DELIMITER_QUOTING = frozenset("'\"\\")
_COMMENT_MAY_FOLLOW = frozenset(" \t\n;|&()")
_BODY_SEPARATOR = "\n"


class _HeredocStripper:
    """One left-to-right pass over a command, copying everything except heredoc bodies."""

    def __init__(self, cmd: str) -> None:
        """Hold the command and the pass's cursor, output, quote state and pending delimiters."""
        self.cmd = cmd
        self.i = 0
        self.out: list[str] = []
        self.quote = ""
        self.pending: list[tuple[str, bool]] = []

    def run(self) -> str:
        """Copy the command through, dropping each heredoc body.

        Returns:
            the command with every heredoc body replaced by a command separator.

        """
        while self.i < len(self.cmd):
            self._step()
        return "".join(self.out)

    def _take(self, end: int) -> None:
        """Copy the text from the cursor up to `end`, and move the cursor there."""
        end = min(end, len(self.cmd))
        self.out.append(self.cmd[self.i:end])
        self.i = end

    def _line_end(self, start: int) -> int:
        """Return the index of the newline ending the line at `start`, or the command's length.

        Returns:
            the index of the next newline at or after `start`, or `len(cmd)`.

        """
        end = self.cmd.find("\n", start)
        return len(self.cmd) if end < 0 else end

    def _step(self) -> None:
        """Advance over one lexical unit: a character, an escape, a comment, or a heredoc."""
        cmd, i = self.cmd, self.i
        ch = cmd[i]
        if self.quote:
            self._step_quoted(ch)
        elif ch == "\\":
            self._take(i + 2)
        elif ch in _QUOTES:
            self.quote = ch
            self._take(i + 1)
        elif ch == "#" and (i == 0 or cmd[i - 1] in _COMMENT_MAY_FOLLOW):
            self._take(self._line_end(i))
        elif cmd.startswith("<<<", i):
            self._take(i + 3)               # a here-string: its word is ordinary shell
        elif cmd.startswith("<<", i):
            self._open(i)
        elif ch == "\n" and self.pending:
            self._skip_bodies()
        else:
            self._take(i + 1)

    def _step_quoted(self, ch: str) -> None:
        """Advance inside a quoted string, where no heredoc operator can open."""
        if ch == "\\" and self.quote == '"':
            self._take(self.i + 2)
            return
        if ch == self.quote:
            self.quote = ""
        self._take(self.i + 1)

    def _open(self, i: int) -> None:
        """Copy a heredoc operator and its delimiter word, and queue the delimiter."""
        j = i + 2
        dash = self.cmd.startswith("-", j)
        if dash:
            j += 1
        while j < len(self.cmd) and self.cmd[j] in " \t":
            j += 1
        end = self._word_end(j)
        delimiter = "".join(c for c in self.cmd[j:end] if c not in _DELIMITER_QUOTING)
        if delimiter:
            self.pending.append((delimiter, dash))
        self._take(end)

    def _word_end(self, start: int) -> int:
        """Return where the delimiter word starting at `start` ends, honouring its quoting.

        Returns:
            the index just past the delimiter word.

        """
        k = start
        while k < len(self.cmd) and self.cmd[k] not in _HEREDOC_WORD_END:
            if self.cmd[k] in _QUOTES:
                close = self.cmd.find(self.cmd[k], k + 1)
                k = len(self.cmd) if close < 0 else close + 1
            elif self.cmd[k] == "\\":
                k += 2
            else:
                k += 1
        return min(k, len(self.cmd))

    def _skip_bodies(self) -> None:
        """At the newline ending a heredoc line, skip every queued body and its terminator."""
        k = self.i + 1
        for delimiter, dash in self.pending:
            k = self._body_end(k, delimiter, dash=dash)
        self.pending = []
        self.out.append(_BODY_SEPARATOR)
        self.i = min(k, len(self.cmd))

    def _body_end(self, start: int, delimiter: str, *, dash: bool) -> int:
        """Return the index just past the line that terminates a body beginning at `start`.

        Returns:
            the index after the terminator line, or `len(cmd)` when the body is unterminated.

        """
        k = start
        while k < len(self.cmd):
            end = self._line_end(k)
            line = self.cmd[k:end]
            k = end + 1
            if (line.lstrip("\t") if dash else line) == delimiter:
                return k
        return len(self.cmd)


def strip_heredoc_bodies(cmd: str) -> str:
    """Remove every heredoc BODY from `cmd`, keeping the `<<TAG` redirection itself.

    Returns:
        `cmd` with each body and its terminator replaced by a command separator; a command with
        no heredoc is returned unchanged.

    """
    if "<<" not in cmd:
        return cmd
    return _HeredocStripper(cmd).run()


# ⚑⚑⚑ A NEWLINE ENDS A COMMAND, AND THE TOKENIZER READ IT AS A SPACE. MEASURED on HEAD: `echo a`
# on line one and `grep x notes.md` on line two PASSED the structural-query hook, because shlex
# treats a newline as whitespace and the grep became ARGUMENTS of `echo`. One newline bypassed the
# hook's core refusal.
#
# ⚑⚑ SO EVERY SEPARATING NEWLINE IS MARKED `;` BEFORE SHLEX SEES IT, on bash's own rules:
#   * inside single or double quotes a newline is data, never a separator;
#   * a backslash-newline outside single quotes is a CONTINUATION — both characters vanish, as
#     bash removes them, so `gr\<newline>ep` reads as `grep`;
#   * a `#` comment runs to the newline and no further — the newline after it still separates;
#   * a newline after `|`, `|&`, `&&` or `||` continues the pipeline or list;
#   * CRLF separates like LF: the `\r` is whitespace to shlex.
# ⚑ THE MARK KEEPS BOTH NEWLINES AROUND THE `;`. shlex reads a comment to the end of its line, so
# a mark without a leading newline would be swallowed by a comment on the line it ends; and
# `punctuation_chars` fuses ADJACENT punctuation, so a bare `;` next to a `;` would become `;;`.
# ⚑ HEREDOC BODIES MUST BE CUT FIRST (`commands` does so); a body's newlines are not shell.
LINE_MARK = "\n;\n"
_CONTINUED_BY = ("|", "|&", "&&", "||")
_LINE_BLANKS = " \t\r"


class _LineSeparator:
    """One left-to-right pass marking every newline that ends a command."""

    def __init__(self, cmd: str) -> None:
        """Hold the command, the pass's cursor, its output, and the open quote if any."""
        self.cmd = cmd
        self.i = 0
        self.out: list[str] = []
        self.quote = ""

    def run(self) -> str:
        """Copy the command through, marking separating newlines.

        Returns:
            the command with each separating newline replaced by `LINE_MARK`.

        """
        while self.i < len(self.cmd):
            self._step()
        return "".join(self.out)

    def _take(self, end: int) -> None:
        """Copy the text from the cursor up to `end`, and move the cursor there."""
        end = min(end, len(self.cmd))
        self.out.append(self.cmd[self.i:end])
        self.i = end

    def _escape(self) -> None:
        """Drop a backslash-newline continuation; copy any other escape whole."""
        if self.cmd.startswith("\\\n", self.i):
            self.i += len("\\\n")
        else:
            self._take(self.i + len("\\\n"))

    def _step(self) -> None:
        """Advance over one lexical unit: a character, an escape, a comment, or a newline."""
        cmd, i = self.cmd, self.i
        ch = cmd[i]
        if self.quote:
            self._step_quoted(ch)
        elif ch == "\\":
            self._escape()
        elif ch in _QUOTES:
            self.quote = ch
            self._take(i + 1)
        elif ch == "#" and (i == 0 or cmd[i - 1] in _COMMENT_MAY_FOLLOW):
            end = cmd.find("\n", i)
            self._take(len(cmd) if end < 0 else end)
        elif ch == "\n":
            tail = "".join(self.out).rstrip(_LINE_BLANKS)
            self.out.append("\n" if tail.endswith(_CONTINUED_BY) else LINE_MARK)
            self.i += 1
        else:
            self._take(i + 1)

    def _step_quoted(self, ch: str) -> None:
        """Advance inside a quoted string, where a newline is data."""
        if ch == "\\" and self.quote == '"':
            self._escape()
            return
        if ch == self.quote:
            self.quote = ""
        self._take(self.i + 1)


def separate_lines(cmd: str) -> str:
    """Mark each newline that ends a command as a `;`, so the tokenizer splits there.

    Returns:
        `cmd` with every separating newline replaced by a `;` between newlines; a command with no
        newline is returned unchanged.

    """
    if "\n" not in cmd:
        return cmd
    return _LineSeparator(cmd).run()


def commands(cmd: str) -> list[list[str]]:
    """Split the command string into its individual commands.

    Each element is one command's words, operators removed. `a | b && c` yields three lists. This
    is what lets a caller ask "is a textual tool in command position ANYWHERE in this line", which
    is the question `toks[0]` could not answer. Heredoc bodies are removed first — they are data.

    Returns:
        the the command string into its individual commands.

    """
    out: list[list[str]] = []
    cur: list[str] = []
    for tok in tokenize(strip_heredoc_bodies(cmd)):
        if tok in OPERATORS:
            if cur:
                out.append(cur)
            cur = []
            continue
        cur.append(tok)
    if cur:
        out.append(cur)
    return out


def _past_wrapper(words: list[str], i: int, wrapper: str) -> int:
    """Advance past a wrapper's own flags and operands to where its command begins.

    ⚑ CONSUME THE WRAPPER *AND ITS OPERANDS*. `timeout 180 grep` puts a DURATION between the
    wrapper and the real program; a first draft skipped only the wrapper and then reported `180`
    as the program. An operand that cannot name a program (a number, a duration like `1.5s`, a
    bare subcommand word for uv/poetry) is skipped; the first token that could be a program ends
    the skip.

    ⚑⚑ EXTRACTED FROM `programs` RATHER THAN REFORMATTED INSIDE IT. The loop reached six nested
    blocks, and the depth was not incidental — it is a WHILE over tokens inside a WHILE over
    tokens, each with its own advance. Flattening by early-continue would have kept one function
    answering two questions; this is the inner question named, and it has an answer a reader can
    check in isolation: *given a wrapper here, where does its command start?*

    Args:
        words: one command's tokens.
        i: the index just past the wrapper's own name.
        wrapper: the wrapper's bare name, which selects its flags-with-arguments.

    Returns:
        The index of the first token that could name a program — or `len(words)` when the wrapper
        is the whole command and nothing follows it.

    """
    takes_arg = _FLAGS_WITH_ARG.get(wrapper, frozenset())
    while i < len(words):
        raw = words[i]
        nxt = _debare(raw)
        if nxt is None:                 # a flag: still the wrapper's
            # ⚑ IF THIS FLAG TAKES A SEPARATE ARGUMENT, CONSUME THAT TOO — else the argument
            # (`KILL`, `nobody`, `/tmp`) is read as the program and the real program goes
            # invisible. That is the measured bypass this module was rewritten to close.
            bare = raw.lstrip("\\")
            attached = "=" in bare or (
                len(bare) > _SHORT_FLAG_LEN and bare[:_SHORT_FLAG_LEN] in takes_arg
            )
            i += 1
            if bare in takes_arg and not attached and i < len(words):
                i += 1                  # skip the flag's separate argument
            continue
        if _is_operand(nxt, wrapper):
            i += 1
            continue
        break
    return i


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
                i = _past_wrapper(words, i + 1, name)
                continue
            found.append((name, words[i + 1:]))
            break                                  # the rest of THIS command is args
    return found
