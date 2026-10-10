# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-hooks-probe`: it fires each gate, and only a refusal passes (W898, W899).

⚑⚑ THE PROBE MUST FAIL WHERE A GUARD IS INERT, so every arm that passes has a control that fails: a
launcher that allows, one that prints nothing, one that is absent. The last arms run the REAL
`hooks/bin` launchers end to end through a stand-in venv whose entry scripts call the real hook
modules, from a foreign working directory, with no skip path.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from mikemol.hooks import probe

_BIN = Path(__file__).parent.parent / "bin"
_EXECUTABLE = 0o755
_TWO = 2
_DENY = '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny"}}'
_ALLOW = '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}'
_ENTRY_FUNCTIONS = {
    "mikemol-hook-no-verify": "no_verify_main",
    "mikemol-hook-no-chaining": "no_chaining_main",
    "mikemol-hook-structural-query": "structural_query_main",
}
_ROUTING = (
    "# struct-tools\n\n"
    "| artifact | tool | notes | claims |\n"
    "|----------|------|-------|--------|\n"
    "| markdown | `mdstruct/.venv/bin/mdstruct` | headings | `.md` |\n"
)
_SEE = (
    "cat >/dev/null\n"
    'printf \'%s %s %s\\n\' "$CLAUDE_PROJECT_DIR" "$PWD" "$STRUCT_HOOK_BLOCK" >> {log}\n'
    "printf '%s' '{decision}'"
)


def _stub(path: Path, body: str) -> Path:
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(_EXECUTABLE)
    return path


def _row(entry: str = "mikemol-hook-no-chaining") -> probe.Row:
    return next(r for r in probe.GATES if r.entry == entry)


def test_a_decision_is_read_from_the_hook_output() -> None:
    """Deny and allow are read; anything else is no decision."""
    assert probe.decision_of(_DENY) == "deny"
    assert probe.decision_of(_ALLOW) == "allow"
    assert probe.decision_of("") is None
    assert probe.decision_of("not json") is None
    assert probe.decision_of('{"hookSpecificOutput": 3}') is None


def test_a_launcher_that_denies_passes(tmp_path: Path) -> None:
    """The control that passes: a stub printing a deny decision, fired from the project root."""
    launcher = _stub(tmp_path / "gate", f"cat >/dev/null\nprintf '%s' '{_DENY}'")
    verdict = probe.fire(_row(), str(launcher), tmp_path, tmp_path, "root")
    assert verdict.ok
    assert verdict.line().startswith("OK   mikemol-hook-no-chaining@root")


def test_a_launcher_that_allows_fails_and_says_so(tmp_path: Path) -> None:
    """An inert guard: it answers allow, and the verdict names that."""
    launcher = _stub(tmp_path / "gate", f"cat >/dev/null\nprintf '%s' '{_ALLOW}'")
    verdict = probe.fire(_row(), str(launcher), tmp_path, tmp_path, "root")
    assert not verdict.ok
    assert "allow, not deny" in verdict.why


def test_a_launcher_that_prints_nothing_fails(tmp_path: Path) -> None:
    """The silent guard: exit 0 and no decision, which the harness reads as allow."""
    launcher = _stub(tmp_path / "gate", "cat >/dev/null")
    verdict = probe.fire(_row(), str(launcher), tmp_path, tmp_path, "root")
    assert not verdict.ok
    assert "no decision printed" in verdict.why


def test_an_absent_launcher_is_a_failure_not_a_skip(tmp_path: Path) -> None:
    """A launcher that does not exist fails with the reason; nothing is skipped."""
    verdict = probe.fire(_row(), str(tmp_path / "missing"), tmp_path, tmp_path, "root")
    assert not verdict.ok
    assert "could not run" in verdict.why


def test_each_gate_is_fired_from_the_root_and_from_a_foreign_directory(tmp_path: Path) -> None:
    """The launcher sees the project in CLAUDE_PROJECT_DIR and the two different working dirs."""
    log = tmp_path / "log"
    launcher = _stub(tmp_path / "gate", _SEE.format(log=log, decision=_DENY))
    foreign = tmp_path / "elsewhere"
    foreign.mkdir()
    probe.probe([_row()], str(launcher), tmp_path, foreign)
    seen = [line.split() for line in log.read_text(encoding="utf-8").splitlines()]
    assert seen == [
        [str(tmp_path), str(tmp_path), "1"],
        [str(tmp_path), str(foreign), "1"],
    ]


def test_the_entry_and_project_are_substituted_into_the_argv_template(tmp_path: Path) -> None:
    """The entry and project placeholders reach the launcher as words, never through a shell."""
    log = tmp_path / "log"
    launcher = _stub(tmp_path / "gate", f"cat >/dev/null\nprintf '%s\\n' \"$*\" >> {log}")
    template = f"{launcher} {{entry}} {{project}}"
    probe.fire(_row(), template, tmp_path, tmp_path, "root")
    assert log.read_text(encoding="utf-8").split() == ["mikemol-hook-no-chaining", str(tmp_path)]


def test_main_exits_zero_only_when_every_row_denied(tmp_path: Path) -> None:
    """0 for all-deny, 1 for any allow, over the same launcher."""
    deny = _stub(tmp_path / "deny", f"cat >/dev/null\nprintf '%s' '{_DENY}'")
    allow = _stub(tmp_path / "allow", f"cat >/dev/null\nprintf '%s' '{_ALLOW}'")
    assert probe.main(["--project", str(tmp_path), "--launcher", str(deny)]) == 0
    assert probe.main(["--project", str(tmp_path), "--launcher", str(allow)]) == probe.EXIT_FAILED


def test_main_refuses_an_unknown_gate_and_an_unknown_flag(tmp_path: Path) -> None:
    """A typo is a usage error (2), never a pass over zero rows."""
    assert probe.main(["--bogus"]) == probe.EXIT_USAGE
    assert probe.main(["--project"]) == probe.EXIT_USAGE
    assert probe.main(["mikemol-hook-nonesuch", "--project", str(tmp_path)]) == probe.EXIT_USAGE


def test_main_fires_only_the_gates_it_is_given(tmp_path: Path) -> None:
    """Naming one gate fires two rows (root and foreign), not eight."""
    log = tmp_path / "log"
    launcher = _stub(tmp_path / "gate", f"cat >/dev/null\necho x >> {log}\nprintf '%s' '{_DENY}'")
    args = ["--project", str(tmp_path), "--launcher", str(launcher), "mikemol-hook-no-verify"]
    probe.main(args)
    assert len(log.read_text(encoding="utf-8").splitlines()) == _TWO


def _standin_checkout(tmp_path: Path) -> Path:
    """Build a fake checkout whose hooks venv runs the real hook modules.

    The venv's `python3` is this interpreter (with this process's import path), and each entry
    script calls the real `mikemol.hooks.entry` function, so the `hooks/bin` launcher is the REAL
    one and the decision comes from the REAL hook.

    Returns:
        the fake checkout root.

    """
    root = tmp_path / "project"
    (root / "hooks" / "bin").mkdir(parents=True)
    for launcher in _BIN.glob("mikemol-hook-*"):
        target = root / "hooks" / "bin" / launcher.name
        target.write_text(launcher.read_text(encoding="utf-8"), encoding="utf-8")
        target.chmod(_EXECUTABLE)
    table = root / ".claude" / "skills" / "struct-tools" / "SKILL.md"
    table.parent.mkdir(parents=True)
    table.write_text(_ROUTING, encoding="utf-8")
    venv_bin = root / "bazel-bin" / "hooks" / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    path = os.pathsep.join(sys.path)
    _stub(venv_bin / "python3", f'export PYTHONPATH="{path}"\nexec "{sys.executable}" "$@"')
    for entry, function in _ENTRY_FUNCTIONS.items():
        script = venv_bin / entry
        script.write_text(
            f"from mikemol.hooks.entry import {function}\nraise SystemExit({function}())\n",
            encoding="utf-8",
        )
    return root


def test_the_real_launchers_deny_from_a_foreign_directory(tmp_path: Path) -> None:
    """End to end, no skip: each real `hooks/bin` launcher denies at the root and elsewhere."""
    root = _standin_checkout(tmp_path)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    rows = [r for r in probe.GATES if r.entry in _ENTRY_FUNCTIONS]
    verdicts = probe.probe(rows, probe.DEFAULT_LAUNCHER, root, foreign)
    assert [v.line() for v in verdicts if not v.ok] == []
    assert len(verdicts) == _TWO * len(_ENTRY_FUNCTIONS)


def test_an_absent_hook_venv_still_denies_because_the_gate_fails_shut(tmp_path: Path) -> None:
    """A gate launcher with no venv denies explicitly rather than failing open."""
    root = _standin_checkout(tmp_path)
    (root / "bazel-bin" / "hooks" / ".venv" / "bin" / "python3").unlink()
    verdicts = probe.probe([_row()], probe.DEFAULT_LAUNCHER, root, tmp_path)
    assert all(v.ok for v in verdicts)


def test_a_repo_with_no_routing_table_fails_the_structural_query_row(tmp_path: Path) -> None:
    """The adopter's silent failure: no table, so the gate allows everything and says nothing."""
    root = _standin_checkout(tmp_path)
    (root / ".claude" / "skills" / "struct-tools" / "SKILL.md").unlink()
    row = _row("mikemol-hook-structural-query")
    verdicts = probe.probe([row], probe.DEFAULT_LAUNCHER, root, tmp_path)
    assert not any(v.ok for v in verdicts)


@pytest.mark.parametrize("entry", sorted(_ENTRY_FUNCTIONS))
def test_every_gate_in_the_table_has_a_command_that_must_be_denied(entry: str) -> None:
    """The table names the gates and a non-empty command for each."""
    assert _row(entry).command.strip()
