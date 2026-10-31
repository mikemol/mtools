# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The commit gate refuses committed mutation sites that lag the graph (W1989).

⚑ THE CONTROLS: the step runs only where `hooks/sites` exists, names the generator's own `--check`
(never `--write`, which would repair silently), and runs it through the gate's captured runner so
the stale files it names are in the refusal and not a hundred lines above it.
"""

from pathlib import Path

_GATE = Path(__file__).parents[2] / ".githooks" / "pre-commit"
_STEP = 'run_checked "hooks/sites follow the graph (mutants_gen --check)"'


def _step() -> list[str]:
    lines = _GATE.read_text(encoding="utf-8").splitlines()
    at = [i for i, line in enumerate(lines) if _STEP in line]
    assert len(at) == 1
    return lines[at[0] - 1 : at[0] + 4]


def test_the_step_is_guarded_by_the_sites_directory_and_checks_never_writes() -> None:
    """Guarded by `[ -d hooks/sites ]`, and the generator is asked to `--check` only."""
    step = _step()
    assert step[0].strip() == "if [ -d hooks/sites ]; then"
    joined = " ".join(step)
    assert "check_mutants/mutants_gen.py --dist hooks --check" in joined
    assert "--write" not in joined


def test_the_step_runs_before_the_suite_and_ends_the_run_when_it_fails() -> None:
    """W2185: the check comes before `phase bazel_test`, and its failure exits before it."""
    lines = _GATE.read_text(encoding="utf-8").splitlines()
    step = next(i for i, line in enumerate(lines) if _STEP in line)
    suite = next(i for i, line in enumerate(lines) if line.strip() == "phase bazel_test")
    assert step < suite
    between = "\n".join(lines[step:suite])
    assert 'if [ "$failed_checks" != "$_sites_before" ]; then' in between
    assert "exit 1" in between


def test_the_step_runs_through_the_captured_runner_from_the_tools_root() -> None:
    """The generator needs fence and mutation on the path and the hooks interpreter of the tools."""
    joined = " ".join(_step())
    assert 'PYTHONPATH="$tools/fence/src:$tools/mutation/src"' in joined
    assert '"$tools/hooks/.venv/bin/python3"' in joined
    assert "git_scrubbed" in joined
