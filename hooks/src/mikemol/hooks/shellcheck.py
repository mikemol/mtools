# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""PreToolUse(Bash|Edit|Write) — refuse shell that shellcheck flags, and refuse to be inert.

⚑ THE SIBLING THAT GATES CORRECTNESS RATHER THAN SHAPE. `no_chaining` refuses a COMPOSED command;
`structural_query` refuses a TEXTUAL question about a STRUCTURED artifact. Neither reads what the
shell MEANS, so `[ $x = y ]` with an empty `x` and an unquoted `$f` carrying a space pass both. A
defect that does not crash but returns a plausible transcript is the class this hook exists for.

⚑⚑ NO SUPPRESSION DIRECTIVE, AND `EXCLUDE` STARTS EMPTY. Ported from substrate's
`scripts/hook_shellcheck.py` (letter 2026-09-22), which shipped three waivers — SC2329, SC2016,
SC1091 — each measured against THAT tree's scripts. A waiver is a claim about a population, so
none is inherited: an adopting tree declares its own, with a dated warrant, in the pyproject that
governs the file (`exclude_for`). gcalculus measured its own need as SC2016 alone (4 sites, all in
`check.sh`); SC2329 and SC1091 had zero hits there.

⚑⚑⚑ AN ARMED HOOK WITH NO LINTER REFUSES — THE ONE DECISION THIS PORT REVERSES. The origin failed
OPEN and "announced once" on stderr; the once-guard lived in the hook's own process environment,
so it never held, and stderr is not a decision, so armed-and-inert ALLOWED silently (measured by
substrate). The origin's fear — a refusal that bricks the session — is answered the way this
package's launcher answered it: deny everything EXCEPT the command that repairs it (`is_repair`),
and never reach the linter for a file that is not shell, so the harness settings stay editable.

⚑ `None` IS UNKNOWN AND `[]` IS MEASURED-CLEAN, everywhere below. Collapsing them makes "could not
look" render as a clean bill — the success-state-identical-to-failure-state defect.

CONSUMED BY: the `mikemol-hook-shellcheck` console script.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from mikemol.hooks import cmdparse, payload, project_root
from mikemol.hooks.structural_query import deny_payload

SHELLCHECK = "shellcheck"

# The switch this hook answers to; `payload.armed` falls back to the shared one when it is unset.
OWN_SWITCH = "SHELLCHECK_HOOK_BLOCK"

# ⚑ PATH FIRST, THEN THE MISE SHIM — measured by the origin: mise tools are NOT on a
# non-interactive subprocess's bare PATH, so a PATH-only lookup concludes ABSENT with the linter
# installed. Under this port that would be a REFUSAL over a linter that is present.
MISE_SHIM = Path("~/.local/share/mise/shims/shellcheck").expanduser()

# ⚑⚑⚑ THE PACKAGE-LEVEL RELIEF SET, EMPTY: what applies when no project governs the path. A tree's
# waivers live in its own pyproject, in the `tool.mikemol-hooks.shellcheck.exclude` table, each
# key a rule code and each value its dated warrant — see `exclude_for`.
EXCLUDE: frozenset[str] = frozenset()

# A warrant must say what was measured, and when; shorter prose cannot do both.
_WARRANT_MIN = 40

# The shells shellcheck can read. zsh is MATCHED so a zsh shebang is an answer (not shell this
# hook lints) rather than a miss that lets the suffix vote.
_SHEBANG = re.compile(r"^#!\s*(?:/usr/bin/env\s+)?(?:\S*/)?(bash|sh|dash|ksh|zsh)\b")
SHELL_SUFFIXES = (".sh", ".bash", ".ksh", ".zsh")
_SC_DIALECTS = frozenset(("bash", "sh", "dash", "ksh"))

# How long the linter may run before its silence is treated as UNKNOWN.
_TIMEOUT_S = 15

# A finding: the rule code, the line in the operator's own coordinates, the message.
Finding = tuple[str, int, str]

# ⚑ A BASH-TOOL COMMAND IS A FRAGMENT; SHELLCHECK LINTS A SCRIPT. Without a shebang every command
# earns SC2148 — a finding about the WRAPPER. The preamble's line is subtracted back out of every
# reported line, or each finding points one line past what the operator wrote.
_PREAMBLE = "#!/usr/bin/env bash\n"
_PREAMBLE_LINES = _PREAMBLE.count("\n")

# ⚑⚑ QUOTE THE TAG; DO NOT DELETE THE BODY. Deleting a heredoc body removes its terminator and
# shellcheck reports SC1044/SC1072 — a false positive introduced by the fix for the first one
# (origin, measured 2026-08-28). A quoted tag means "this body is literal", which shellcheck
# honours, and the body stays so line numbers after it stay true. ⚑ This is why
# `structural_query`'s heredoc stripper is NOT reused: deletion is right for a token scan and
# wrong for a parser.
_HEREDOC_TAG = re.compile(r"(<<-?)(\s*)([A-Za-z_][A-Za-z0-9_]*)")

# ⚑⚑⚑ THE REPAIR EXEMPTION: installing the linter is the one command a missing linter must not
# refuse, or the refusal names a route it then blocks — the launcher's measured deadlock. It is a
# (program, mention) conjunction, not "allow the package manager": `apt install jq` stays refused.
_INSTALLERS = frozenset(("mise", "apt", "apt-get", "emerge", "brew", "dnf", "pacman", "nix-env"))

_INERT = (
    "shellcheck: this hook is ARMED and cannot render a verdict — {why}.\n"
    "  An armed gate that checks nothing must not read as a passing one, so this is a refusal.\n"
    "  Resolve it, in order of preference:\n"
    "    - install the linter (no root):  mise use -g shellcheck@latest\n"
    "      or system-wide:                your package manager's shellcheck (PATH is searched\n"
    "      first, then ~/.local/share/mise/shims/shellcheck). The install is ADMITTED here.\n"
    "    - or have the operator stand THIS hook down (SHELLCHECK_HOOK_BLOCK=0 on its command\n"
    "      line in the harness settings; a running session re-reads settings only on restart)\n"
    "  Edits to non-shell files are unaffected: they never reach the linter.\n"
)


def linter() -> str | None:
    """Return the shellcheck executable, or None when none can be found.

    Returns:
        the linter's path, or None.

    """
    found = shutil.which(SHELLCHECK)
    if found is not None:
        return found
    return str(MISE_SHIM) if os.access(MISE_SHIM, os.X_OK) else None


def exclude_for(path: str) -> frozenset[str]:
    """Return the tree-local waiver codes governing `path`, dropping an unwarranted entry.

    ⚑ AN ENTRY WITHOUT A DATED WARRANT IS NOT RELIEF, IT IS SUPPRESSION WEARING THE UNIFORM. The
    value must be prose naming a year and long enough to say what was measured; a list of bare
    codes waives nothing.

    Returns:
        the package set plus every warranted code in the governing pyproject.

    """
    cfg = project_root.config_for(path) if path else None
    if cfg is None:
        return EXCLUDE
    try:
        doc: object = tomllib.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return EXCLUDE
    tool = payload.as_record(payload.as_record(doc).get("tool"))
    ours = payload.as_record(payload.as_record(tool.get("mikemol-hooks")).get("shellcheck"))
    waived = payload.as_record(ours.get("exclude"))
    return EXCLUDE | frozenset(
        code
        for code, why in waived.items()
        if isinstance(why, str) and "20" in why and len(why) > _WARRANT_MIN
    )


def findings_of(raw: object, exclude: frozenset[str] = EXCLUDE) -> list[Finding]:
    """Convert shellcheck's `json1` output into findings, dropping waived codes.

    ⚑ EVERY LEVEL IS NARROWED THROUGH `payload.as_record`, so an output shape this code does not
    expect yields no findings rather than a wrong verdict.

    Returns:
        the non-waived findings.

    """
    comments = payload.as_record(raw).get("comments")
    if not isinstance(comments, list):
        return []
    out: list[Finding] = []
    for item in comments:
        entry = payload.as_record(item)
        code = f"SC{entry.get('code')}"
        if code in exclude:
            continue
        line = entry.get("line")
        message = payload.text_of(entry.get("message")).strip()
        out.append((code, line if isinstance(line, int) else 0, message))
    return out


def run(
    script: str, shell: str = "bash", exclude: frozenset[str] = EXCLUDE
) -> list[Finding] | None:
    """Return shellcheck's findings over one script body, or None for UNKNOWN.

    ⚑ THE BODY TRAVELS ON STDIN, so a sourced file is never followed (SC1091) — the price of
    judging content that does not exist on disk yet, which is the point of a PreToolUse gate.

    Returns:
        findings (`[]` is measured-clean), or None when the linter could not render a verdict.

    """
    binary = linter()
    if binary is None:
        return None
    try:
        proc = subprocess.run(
            [binary, f"--shell={shell}", "--format=json1", "-"],
            input=script,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        parsed: object = json.loads(proc.stdout)
    except ValueError:
        return None
    return findings_of(parsed, exclude)


def _quote_tag(m: re.Match[str]) -> str:
    """Return one heredoc redirection with its tag quoted.

    Returns:
        the redirection with a quoted tag.

    """
    return f"{m.group(1)}{m.group(2)}'{m.group(3)}'"


def neutralize_heredoc_bodies(cmd: str) -> str:
    """Quote every unquoted heredoc tag, so its body reads as DATA to the parser.

    Returns:
        the command with each unquoted tag quoted.

    """
    return _HEREDOC_TAG.sub(_quote_tag, cmd)


def analyze_command(cmd: str, exclude: frozenset[str] = EXCLUDE) -> list[Finding] | None:
    """Return findings over a Bash-tool command, in the operator's line numbers, or None.

    ⚑ A HEREDOC BODY IS DATA. Every multi-line commit message goes through one, and a `$word` or
    backtick in English prose earns SC2154/SC2006. Not a waiver: both rules are right about real
    shell, so the cut narrows what counts as shell rather than weakening the rule set.

    Returns:
        findings, `[]` for clean, or None for UNKNOWN.

    """
    if not cmd.strip():
        return []
    found = run(_PREAMBLE + neutralize_heredoc_bodies(cmd), exclude=exclude)
    if found is None:
        return None
    return [(code, max(1, line - _PREAMBLE_LINES), msg) for code, line, msg in found]


def shell_dialect(path: str, content: str) -> str | None:
    """Return the dialect shellcheck can read for this file, else None.

    ⚑ THE SHEBANG IS THE AUTHORITY AND ANY SHEBANG SETTLES IT. A python shebang fails the shell
    pattern exactly as no shebang does; falling through to the suffix then lints `x.sh` (really
    python) as bash. The suffix votes only when the file declares nothing.

    Returns:
        the dialect, or None when the file is not lintable shell.

    """
    text = content.lstrip("﻿")
    m = _SHEBANG.match(text)
    if m:
        dialect = m.group(1)
        return dialect if dialect in _SC_DIALECTS else None
    if text.startswith("#!"):
        return None
    if path.endswith(SHELL_SUFFIXES):
        return None if path.endswith(".zsh") else "bash"
    return None


def analyze_file(
    path: str, content: str, exclude: frozenset[str] = EXCLUDE
) -> list[Finding] | None:
    """Return findings over post-edit content; `[]` when it is not shell; None for UNKNOWN.

    ⚑ THE DIALECT IS DECIDED BEFORE THE LINTER IS LOOKED FOR, which is what keeps a non-shell edit
    — the harness settings among them — out of reach of the absent-linter refusal.

    Returns:
        findings, `[]`, or None.

    """
    dialect = shell_dialect(path, content)
    if dialect is None:
        return []
    return run(content, shell=dialect, exclude=exclude)


def post_edit_content(tool: str, tool_input: dict[str, object]) -> tuple[str, str | None]:
    """Return the (path, content) the tool is about to put on disk, or (path, None).

    ⚑ LINT WHAT WILL EXIST, NOT WHAT WAS ASKED FOR. An Edit fragment alone is shell torn from its
    context (a `fi` with no `if`), so the edit is APPLIED to the on-disk file in memory. An
    unreadable target is UNKNOWN, and the caller must not guess.

    Returns:
        the target path and its post-edit content, or None for the content when unknowable.

    """
    path = payload.text_of(tool_input.get("file_path"))
    if tool == "Write":
        return path, payload.text_of(tool_input.get("content"))
    if tool == "Edit":
        old = payload.text_of(tool_input.get("old_string"))
        new = payload.text_of(tool_input.get("new_string"))
        try:
            current = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return path, None
        count = -1 if tool_input.get("replace_all") is True else 1
        return path, current.replace(old, new, count)
    return path, None


def is_repair(cmd: str) -> bool:
    """Report whether `cmd` installs the linter — the one command an absent linter must admit.

    Returns:
        True when an installer program is invoked with an argument naming shellcheck.

    """
    return any(
        prog in _INSTALLERS and any(SHELLCHECK in arg for arg in args)
        for prog, args in cmdparse.programs(cmd)
    )


def render(findings: list[Finding], subject: str) -> str:
    """Build the refusal text for a set of findings.

    Returns:
        the refusal text.

    """
    lines = [f"shellcheck: this {subject} has findings the gate refuses."]
    lines.extend(f"  {code} (line {line})  {msg}" for code, line, msg in findings)
    lines.extend((
        "  ⚑ there is NO suppression path here, by design — a per-line disable directive",
        "     does not make the shell correct, it makes it READ as reviewed.",
        "  fix the shell. If the rule is genuinely wrong for this tree, declare it under",
        "     [tool.mikemol-hooks.shellcheck.exclude] in the governing pyproject.toml,",
        "     with a dated warrant saying what was measured.",
        f"  see https://www.shellcheck.net/wiki/{findings[0][0]}",
    ))
    return "\n".join(lines)


def verdict(
    tool: str, tool_input: dict[str, object], exclude: frozenset[str] = EXCLUDE
) -> tuple[str, list[Finding] | None]:
    """Return (subject, findings) for one tool call; ("", []) when out of scope.

    Returns:
        the subject word and its findings, `[]`, or None for UNKNOWN.

    """
    if tool == "Bash":
        return "command", analyze_command(payload.text_of(tool_input.get("command")), exclude)
    if tool in {"Write", "Edit"}:
        path, content = post_edit_content(tool, tool_input)
        if content is None:
            return "", []
        return "shell file", analyze_file(path, content, exclude)
    return "", []


def emit(msg: str, *, armed: bool) -> int:
    """Deliver a refusal — a deny payload when armed, an advisory on stderr otherwise.

    Returns:
        0, always — the decision travels in stdout, never the status.

    """
    if armed:
        sys.stdout.write(deny_payload(msg) + "\n")
        return 0
    sys.stderr.write(msg + "\n")
    return 0


def main() -> int:
    """Read the PreToolUse payload from stdin and refuse or allow.

    Returns:
        0 always — the decision travels in the payload, never the status.

    """
    try:
        raw: object = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError, OSError):
        return 0
    record = payload.as_record(raw)
    tool = payload.text_of(record.get("tool_name"))
    tool_input = payload.as_record(record.get("tool_input"))
    # ⚑ THE WAIVERS ARE THOSE OF THE TREE BEING TOUCHED: the edited file's project, or for a Bash
    # command the session's working directory.
    anchor = payload.text_of(tool_input.get("file_path")) or payload.text_of(record.get("cwd"))
    subject, findings = verdict(tool, tool_input, exclude_for(anchor))
    armed = payload.armed(OWN_SWITCH)
    if findings is None:
        # ⚑⚑ THE REPAIR IS ADMITTED AND ANNOUNCED — a hook that quietly permits one shape is a hole
        # nobody can audit; this says why it allowed, where the transcript keeps it.
        if tool == "Bash" and is_repair(payload.text_of(tool_input.get("command"))):
            sys.stderr.write("shellcheck: linter absent, ADMITTING the install that repairs it\n")
            return 0
        why = (
            "no shellcheck on PATH or at the mise shim"
            if linter() is None
            else "shellcheck ran but returned no parseable verdict (crash, timeout, or an "
            "output shape this hook does not read)"
        )
        return emit(_INERT.format(why=why), armed=armed)
    if not findings:
        return 0
    return emit(render(findings, subject), armed=armed)
