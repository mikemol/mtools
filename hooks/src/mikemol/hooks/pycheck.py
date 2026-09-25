# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""PreToolUse(Edit|Write) — refuse a `.py` edit whose RESULT ruff or mypy flags.

⚑ THE PYTHON SIBLING OF `shellcheck`, and it reuses that hook's halves rather than copying them:
`shellcheck.post_edit_content` renders what the edit will leave on disk, `shellcheck.emit` delivers
the decision. Ported from substrate's `scripts/hook_pycheck.py` and its `pycheck_*` siblings
(letter 2026-09-22); the argv is `checkers.checker_argv`, the ambient directory `checker_context`,
the governing project `project_root` — all already here, and each consumed here for the first time.

⚑⚑ THE BAR IS THE EDITED FILE'S OWN. Config, staging directory, working directory and interpreter
are one decision (`project_root`): the tempfile is staged in the project that governs the file,
ruff is fed on stdin under `--stdin-filename <real path>` so path-keyed config reaches an in-flight
edit, and both checkers run from that project's `.venv`.

⚑⚑⚑ AN ARMED HOOK THAT CANNOT CHECK REFUSES — THE DECISION THIS PORT REVERSES, as `shellcheck`'s
did. The origin failed OPEN and announced once on stderr; stderr is not a decision, so armed and
inert ALLOWED. Here a `None` verdict is a deny naming the repair. That cannot deadlock: the repair
(`uv sync` in the governing project) is a Bash call, which this hook never sees, and a non-`.py`
edit — the harness settings among them — never reaches a checker.

⚑ FOUR STATES, NOT THREE. Unparseable content is decided by `ast.parse` BEFORE any checker runs and
lands on the REFUSING side: the checkers are fine, the file is broken, and the next write repairs
it. A truncated write under ENOSPC is exactly this shape. And the roster is FOLDED
(`compose`), never first-hit: a finding beside a could-not-run refuses AND states the blindness.

⚑⚑ AN ADDED SUPPRESSION IS A FINDING (`suppressions`). ruff honours `# noqa` and mypy honours
`# type: ignore`, so an edit carrying one used to pass while the refusal text promised "no
line-scoped suppression". The file before the edit is compared with the file after, and only a
directive the edit ADDS refuses — existing debt never blocks an unrelated edit.

⚑⚑ THE GRAIN IS ONE WRITE. Every write is judged whole, so an import and its first use split
across two edits are refused twice (F401, then F821). That is correct and is kept; the refusal
names it (`pycheck_message.grain_note`).

⚑⚑ KNOWN BOUND: THE GATE'S REACH STOPS AT THE EDIT TOOLS. A file that arrives by any other route —
`mv x.staged x.py`, `cp`, `git checkout`, a codemod run through Bash — is never seen. This is
deliberate, not pending: build-under-another-suffix-then-move is the documented escape when the
guard itself is unrepairable (summit's `ask-a-move-reaches-the-edit-gate`, ranked last by
substrate's triage). The commit-time ruff/mypy gate is what covers the moved file.

CONSUMED BY: the `mikemol-hook-pycheck` console script.
"""

from __future__ import annotations

import ast
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path

from mikemol.hooks import (
    checker_context,
    checkers,
    payload,
    project_root,
    shellcheck,
    suppressions,
)
from mikemol.hooks.pycheck_message import render
from mikemol.hooks.verdict import Verdict, run_checker

# The switch this hook answers to; `payload.armed` falls back to the shared one when it is unset.
OWN_SWITCH = "PYCHECK_HOOK_BLOCK"

# The tools this hook gates. Anything else is out of scope and allowed.
_EDIT_TOOLS = frozenset(("Write", "Edit"))

# File modes staged by content: a shebang is an executable (EXE001/EXE002 read true).
_MODE_SCRIPT = 0o755
_MODE_MODULE = 0o644

_INERT = (
    "pycheck: this hook is ARMED and cannot render a verdict for {path} — {why}.\n"
    "  An armed gate that checks nothing must not read as a passing one, so this is a refusal.\n"
    "  Resolve it, in order of preference:\n"
    "    - give the governing project its checkers:  uv sync   (in {root}; ruff and mypy must\n"
    "      be in its dev group). Bash is not gated by this hook, so the repair is reachable.\n"
    "    - or have the operator stand THIS hook down (PYCHECK_HOOK_BLOCK=0 on its command line\n"
    "      in the harness settings; a running session re-reads settings only on restart).\n"
    "  Edits to non-.py files are unaffected: they never reach a checker.\n"
)


def syntax_error(content: str, path: str) -> str:
    """Return a one-line description of `content`'s syntax error, or "" when it parses.

    Returns:
        the reason, or the empty string for parseable source.

    """
    try:
        ast.parse(content, filename=path or "<the edited file>")
    except SyntaxError as err:
        where = f"line {err.lineno}" if err.lineno is not None else "an unknown line"
        return f"{err.msg} ({where})"
    except ValueError as err:
        return f"source cannot be parsed: {err}"
    return ""


def compose(outcomes: list[tuple[str, Verdict]]) -> Verdict:
    """Fold per-checker outcomes into one verdict, independent of roster order.

    Returns:
        False with every finding (and the blindness) when any checker objected; None when none
        objected and any could not run, or the roster is empty; True only on full coverage.

    """
    findings = [report for _name, (ok, report) in outcomes if ok is False]
    unknown = [report for _name, (ok, report) in outcomes if ok is None]
    if findings:
        blind = "".join(f"\n    - {u}" for u in unknown)
        note = f"\n--- coverage ---\n  ⚑ PARTIAL — these did not run:{blind}" if unknown else ""
        return False, "\n".join(findings) + note
    if unknown:
        return None, "; ".join(unknown)
    if not outcomes:
        return None, "no checker was configured to run"
    return True, ""


def before_edit(path: str) -> str:
    """Return the file's text as it stands before the edit, or "" for a file that does not exist.

    ⚑ AN UNREADABLE FILE COUNTS AS EMPTY, so every directive in the edit reads as added — the
    conservative side for a gate whose failure mode is letting a suppression through.

    Returns:
        the pre-edit text.

    """
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def analyze(content: str, path: str) -> Verdict:
    """Return the verdict for post-edit `.py` content at `path`, under ITS project's bar.

    Returns:
        the composed verdict; None names why no verdict could be rendered.

    """
    root = project_root.project_for(path)
    if root is None:
        return True, ""
    venv_py = project_root.venv_python_for(path)
    if venv_py is None:
        return None, f"{root} has no .venv/bin/python3 to run ruff and mypy from"
    broken = syntax_error(content, path)
    if broken:
        return False, f"--- syntax ---\n{path}: error: {broken}  [syntax]"
    fd, tmp_name = tempfile.mkstemp(suffix=".py", dir=root)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        tmp.chmod(_MODE_SCRIPT if content.startswith("#!") else _MODE_MODULE)
        outcomes: list[tuple[str, Verdict]] = []
        cfg = root / project_root.MARKER
        for name, argv, reads_stdin in checkers.checker_argv(tmp, path, venv_py, cfg):
            with checker_context.in_project(root):
                ok, report = run_checker(name, argv, content if reads_stdin else None)
            if ok is False:
                report = report.replace(str(tmp), path).replace(tmp.name, path)
            outcomes.append((name, (ok, report)))
        new = suppressions.added(before_edit(path), content)
        if new:
            outcomes.append(("suppression", (False, suppressions.report(path, new))))
        return compose(outcomes)
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink()


def main() -> int:
    """Read the PreToolUse payload from stdin and refuse or allow the edit.

    Returns:
        0 always — the decision travels in the payload, never the status.

    """
    try:
        raw: object = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError, OSError):
        return 0
    record = payload.as_record(raw)
    tool = payload.text_of(record.get("tool_name"))
    if tool not in _EDIT_TOOLS:
        return 0
    path, content = shellcheck.post_edit_content(tool, payload.as_record(record.get("tool_input")))
    if content is None or not path.endswith(".py"):
        return 0
    ok, report = analyze(content, path)
    armed = payload.armed(OWN_SWITCH)
    if ok is None:
        root = project_root.project_for(path)
        return shellcheck.emit(_INERT.format(path=path, why=report, root=root), armed=armed)
    if ok:
        return 0
    return shellcheck.emit(render(report, path), armed=armed)
