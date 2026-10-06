# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `bazel_admit`: heavy bazel commands go through membudget, light ones never do."""

from __future__ import annotations

import io
import stat
from typing import TYPE_CHECKING

from mikemol.hooks import bazel_admit, host_facts

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    import pytest

REAL = "/real/bazel"
BUILD_MB = bazel_admit.HEAVY_MB["build"]
BAZEL_FAILED = 7


class _Exec:
    """Record what would have been executed, and answer a fixed exit code."""

    def __init__(self, code: int = 0) -> None:
        self.code = code
        self.runs: list[tuple[list[str], dict[str, str]]] = []

    def __call__(self, argv: Sequence[str], env: Mapping[str, str]) -> int:
        """Record the command and its environment, and return the fixed code.

        Returns:
            the exit code.

        """
        self.runs.append((list(argv), dict(env)))
        return self.code


def _supports(argv: Sequence[str]) -> str | None:
    """Answer the capabilities query as a membudget with the zram gate does.

    Returns:
        the capability list.

    """
    assert argv[1] == "capabilities"
    return "zram-gate\n"


def _too_old(argv: Sequence[str]) -> str | None:
    """Answer the capabilities query as an older membudget does: with its usage and exit 2.

    Returns:
        None, the probe's word for a command that did not succeed.

    """
    del argv
    return None


def _other(argv: Sequence[str]) -> str | None:
    """Answer the query with capabilities that do not include the gate.

    Returns:
        an unrelated capability.

    """
    del argv
    return "something-else\n"


def _empty(argv: Sequence[str]) -> str | None:
    """Answer the query successfully with nothing.

    Returns:
        the empty string.

    """
    del argv
    return ""


def _budget(tmp_path: Path) -> Path:
    """Make a stand-in `mikemol-membudget` file named by MEMBUDGET_BIN.

    Returns:
        its path.

    """
    tool = tmp_path / "mikemol-membudget"
    tool.write_text("#!/bin/sh\n", encoding="utf-8")
    return tool


def _script(path: Path, body: str) -> Path:
    """Write an executable shell script.

    Returns:
        its path.

    """
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_the_verb_is_the_first_word_that_is_not_a_startup_option() -> None:
    """Startup options come first and are skipped; no verb at all is None."""
    assert bazel_admit.verb_of(["--output_base=/x", "test", "//..."]) == "test"
    assert bazel_admit.verb_of(["build", "--config=x"]) == "build"
    assert bazel_admit.verb_of([]) is None
    assert bazel_admit.verb_of(["--version"]) is None


def test_only_heavy_verbs_have_a_memory_estimate() -> None:
    """build, test, run, coverage and fetch are admitted; info, query and a bare bazel are not."""
    assert bazel_admit.estimate_mb("build") == BUILD_MB
    assert bazel_admit.estimate_mb("test") == BUILD_MB
    for light in ("info", "query", "version", "shutdown", None):
        assert bazel_admit.estimate_mb(light) is None


def test_a_hold_carries_the_zram_ceiling_and_the_wait_bound_to_membudget(tmp_path: Path) -> None:
    """The wait is membudget's: it is told the ceiling and the bound, and holds, not caps."""
    tool = _budget(tmp_path)
    env = {bazel_admit.MEMBUDGET_ENV: str(tool)}
    argv, gated, note = bazel_admit.plan(REAL, ["test", "//..."], BUILD_MB, env, _supports)
    assert argv == [str(tool), "hold", str(BUILD_MB), "bazel", "--", REAL, "test", "//..."]
    assert "run" not in argv[:3]
    assert gated[bazel_admit.ZRAM_MAX_ENV] == str(host_facts.REFUSE_FRACTION)
    assert gated[bazel_admit.TIMEOUT_ENV] == "3600"
    assert note is None


def test_the_bound_follows_the_callers_setting_and_what_the_caller_set_is_kept(
    tmp_path: Path,
) -> None:
    """BAZEL_ADMIT_MAX_WAIT_S sets the default bound; an explicit MEMBUDGET_* value wins."""
    tool = _budget(tmp_path)
    base = {bazel_admit.MEMBUDGET_ENV: str(tool), bazel_admit.MAX_WAIT_ENV: "60"}
    _argv, gated, _note = bazel_admit.plan(REAL, ["build"], BUILD_MB, base, _supports)
    assert gated[bazel_admit.TIMEOUT_ENV] == "60"
    own = {**base, bazel_admit.TIMEOUT_ENV: "5", bazel_admit.ZRAM_MAX_ENV: "0.5"}
    _argv, gated, _note = bazel_admit.plan(REAL, ["build"], BUILD_MB, own, _supports)
    assert gated[bazel_admit.TIMEOUT_ENV] == "5"
    assert gated[bazel_admit.ZRAM_MAX_ENV] == "0.5"


def test_without_membudget_bazel_runs_untouched_and_a_note_says_there_is_no_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What cannot be found blocks nothing: the command is as given, with no gate variables."""
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.chdir(tmp_path)
    argv, gated, note = bazel_admit.plan(REAL, ["test"], BUILD_MB, {}, _supports)
    assert argv == [REAL, "test"]
    assert bazel_admit.ZRAM_MAX_ENV not in gated
    assert note is not None
    assert "without admission or a zram gate" in note


def test_a_membudget_without_the_zram_gate_is_treated_as_absent_and_said(tmp_path: Path) -> None:
    """An older one ignores the ceiling and runs ungated, silently, so it is not relied on."""
    tool = _budget(tmp_path)
    env = {bazel_admit.MEMBUDGET_ENV: str(tool)}
    for probe in (_too_old, _other, _empty):
        argv, gated, note = bazel_admit.plan(REAL, ["test"], BUILD_MB, env, probe)
        assert argv == [REAL, "test"]
        assert bazel_admit.ZRAM_MAX_ENV not in gated
        assert note is not None
        assert "too old" in note
        assert str(tool) in note


def test_the_capability_probe_gives_stdout_on_success_and_none_otherwise(tmp_path: Path) -> None:
    """Exit 0 gives the text; a non-zero exit and a missing program give None."""
    good = _script(tmp_path / "good", "echo zram-gate")
    bad = _script(tmp_path / "bad", "echo usage; exit 2")
    assert bazel_admit.run_probe([str(good)]) == "zram-gate\n"
    assert bazel_admit.run_probe([str(bad)]) is None
    assert bazel_admit.run_probe([str(tmp_path / "absent")]) is None


def test_a_light_verb_is_executed_as_given() -> None:
    """`bazel info` goes straight through, with the environment it came with."""
    run, err = _Exec(), io.StringIO()
    code = bazel_admit.admit([REAL, "info", "workspace"], {"X": "1"}, run, err)
    assert code == 0
    assert run.runs == [([REAL, "info", "workspace"], {"X": "1"})]
    assert not err.getvalue()


def test_a_heavy_verb_runs_under_the_hold_and_its_exit_code_is_returned(tmp_path: Path) -> None:
    """`test` is executed as membudget's hold with the gated environment; its status comes back."""
    tool = _budget(tmp_path)
    run, err = _Exec(code=BAZEL_FAILED), io.StringIO()
    env = {bazel_admit.MEMBUDGET_ENV: str(tool), bazel_admit.TRACE_ENV: "1"}
    code = bazel_admit.admit([REAL, "test", "//..."], env, run, err, _supports)
    assert code == BAZEL_FAILED
    argv, gated = run.runs[0]
    assert argv == [str(tool), "hold", str(BUILD_MB), "bazel", "--", REAL, "test", "//..."]
    assert gated[bazel_admit.ZRAM_MAX_ENV] == str(host_facts.REFUSE_FRACTION)
    assert "admitting `test`" in err.getvalue()


def test_the_bypass_runs_bazel_untouched_and_says_it_did() -> None:
    """BAZEL_ADMIT=0 is an explicit, stated override."""
    run, err = _Exec(), io.StringIO()
    code = bazel_admit.admit([REAL, "build", "//..."], {bazel_admit.BYPASS_ENV: "0"}, run, err)
    assert code == 0
    assert run.runs[0][0] == [REAL, "build", "//..."]
    assert "running without admission" in err.getvalue()


def test_a_heavy_verb_without_a_usable_membudget_still_runs_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gate guards a known failure; a missing guard must not also stop all work."""
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.chdir(tmp_path)
    run, err = _Exec(), io.StringIO()
    code = bazel_admit.admit([REAL, "build"], {}, run, err, _supports)
    assert code == 0
    assert run.runs[0][0] == [REAL, "build"]
    assert "not found" in err.getvalue()


def test_install_writes_an_executable_wrapper_that_fails_open(tmp_path: Path) -> None:
    """tools/bazel runs the admit tool from the repo venv or mtools' build, else bazel untouched."""
    wrapper = bazel_admit.install(tmp_path)
    assert wrapper == tmp_path / "tools" / "bazel"
    assert wrapper.stat().st_mode & stat.S_IXUSR
    text = wrapper.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh")
    assert ".venv/bin/mikemol-bazel-admit" in text
    assert "bazel-bin/hooks/.venv/bin/mikemol-bazel-admit" in text
    assert 'exec "$admit" -- "$BAZEL_REAL" "$@"' in text
    assert text.rstrip().endswith('exec "$BAZEL_REAL" "$@"')


def test_main_installs_a_wrapper_and_refuses_a_bad_command_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--install DIR` prints the wrapper's path; anything else is a usage error, exit 2."""
    assert bazel_admit.main(["--install", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == str(tmp_path / "tools" / "bazel")
    assert bazel_admit.main([]) == bazel_admit.EXIT_USAGE
    assert "usage: mikemol-bazel-admit" in capsys.readouterr().err
