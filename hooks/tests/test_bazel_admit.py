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
    """The wait is membudget's: it is told the ceiling, and no clock bounds it unless named."""
    tool = _budget(tmp_path)
    env = {bazel_admit.MEMBUDGET_ENV: str(tool)}
    argv, gated, note = bazel_admit.plan(REAL, ["test", "//..."], BUILD_MB, env, _supports)
    assert argv == [str(tool), "hold", str(BUILD_MB), "bazel", "--", REAL, "test", "//..."]
    assert "run" not in argv[:3]
    assert gated[bazel_admit.ZRAM_MAX_ENV] == str(host_facts.REFUSE_FRACTION)
    assert bazel_admit.TIMEOUT_ENV not in gated
    assert note is None


def test_the_bound_follows_the_callers_setting_and_what_the_caller_set_is_kept(
    tmp_path: Path,
) -> None:
    """BAZEL_ADMIT_MAX_WAIT_S names a bound; an explicit MEMBUDGET_* value wins."""
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


def test_a_heavy_verb_runs_under_the_hold_and_its_exit_code_is_returned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`test` is executed as membudget's hold with the gated environment; its status comes back."""
    monkeypatch.chdir(tmp_path)
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
    assert 'PYTHONPATH="$here/hooks/src"' in text
    assert "-m mikemol.hooks.bazel_admit" in text
    assert text.rstrip().endswith('exec "$BAZEL_REAL" "$@"')


def test_main_installs_a_wrapper_and_refuses_a_bad_command_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--install DIR` prints the wrapper's path; anything else is a usage error, exit 2."""
    assert bazel_admit.main(["--install", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == str(tmp_path / "tools" / "bazel")
    assert bazel_admit.main([]) == bazel_admit.EXIT_USAGE
    assert "usage: mikemol-bazel-admit" in capsys.readouterr().err


PORT = 1985
RC = "build --remote_cache=grpc://svc.example:1985\nbuild --bes_backend=grpc://svc.example:1985\n"


def _workspace(tmp_path: Path, text: str = RC) -> Path:
    """Make a workspace whose `.bazelrc` is `text`, with a subdirectory to run from.

    Returns:
        the subdirectory.

    """
    (tmp_path / ".bazelrc").write_text(text, encoding="utf-8")
    inner = tmp_path / "pkg"
    inner.mkdir()
    return inner


def _down(_host: str, _port: int) -> bool:
    return False


def _up(_host: str, _port: int) -> bool:
    return True


def _never_asked(_host: str, _port: int) -> bool:
    msg = "the endpoint must not be probed"
    raise AssertionError(msg)


def test_the_endpoint_is_read_from_the_nearest_bazelrc_and_absent_when_none_names_one(
    tmp_path: Path,
) -> None:
    """W2124: nothing is written into this module; a workspace with no BES line has no endpoint."""
    inner = _workspace(tmp_path)
    assert bazel_admit.service_address(inner) == ("svc.example", PORT)
    bare = tmp_path / "other"
    bare.mkdir()
    (bare / ".bazelrc").write_text("build --jobs=2\n", encoding="utf-8")
    assert bazel_admit.service_address(bare) is None


def test_a_refused_endpoint_turns_the_cache_and_the_upload_off_right_after_the_verb(
    tmp_path: Path,
) -> None:
    """The flags go after the verb, so a later caller flag wins; the note names the endpoint."""
    inner = _workspace(tmp_path)
    args, note = bazel_admit.degrade(["test", "//hooks:t", "--jobs=2"], inner, _down)
    assert args == ["test", *bazel_admit.OFF_FLAGS, "//hooks:t", "--jobs=2"]
    assert note is not None
    assert f"svc.example:{PORT} refuses connections" in note


def test_an_endpoint_that_accepts_changes_nothing(tmp_path: Path) -> None:
    """The control: with the service up the cache and the stream stay on, no flag is added."""
    inner = _workspace(tmp_path)
    assert bazel_admit.degrade(["test", "//hooks:t"], inner, _up) == (["test", "//hooks:t"], None)


def test_a_light_verb_or_a_workspace_without_an_endpoint_is_never_probed(tmp_path: Path) -> None:
    """`info` does not use the services, and no named endpoint means nothing to probe."""
    inner = _workspace(tmp_path)
    assert bazel_admit.degrade(["info"], inner, _never_asked) == (["info"], None)
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / ".bazelrc").write_text("build --jobs=2\n", encoding="utf-8")
    assert bazel_admit.degrade(["build"], plain, _never_asked) == (["build"], None)


def test_can_connect_is_true_for_an_accepted_connection_and_false_for_a_socket_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The probe answers from the connection attempt alone: accepted is True, any OSError False."""
    asked: list[tuple[tuple[str, int], float]] = []

    def accept(address: tuple[str, int], timeout: float) -> io.StringIO:
        asked.append((address, timeout))
        return io.StringIO()

    def refuse(_address: tuple[str, int], timeout: float) -> io.StringIO:
        raise ConnectionRefusedError(timeout)

    monkeypatch.setattr("socket.create_connection", accept)
    assert bazel_admit.can_connect("svc.example", PORT) is True
    assert asked == [(("svc.example", PORT), bazel_admit.CONNECT_TIMEOUT_S)]
    monkeypatch.setattr("socket.create_connection", refuse)
    assert bazel_admit.can_connect("svc.example", PORT) is False


NOT_RUNNABLE = 127


def test_main_execs_the_real_bazel_and_answers_127_when_it_cannot_be_started(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Through `main`, a light verb is handed to execve unchanged; a failed exec is said."""
    seen: list[tuple[str, list[str]]] = []

    def record(program: str, argv: list[str], _env: dict[str, str]) -> None:
        seen.append((program, argv))

    monkeypatch.setattr("os.execve", record)
    bazel_admit.main(["--", REAL, "info"])
    assert seen == [(REAL, [REAL, "info"])]

    def refuse(_program: str, _argv: list[str], _env: dict[str, str]) -> None:
        raise OSError

    monkeypatch.setattr("os.execve", refuse)
    assert bazel_admit.main(["--", REAL, "info"]) == NOT_RUNNABLE
    assert f"cannot run {REAL}" in capsys.readouterr().err


def test_the_wrapper_finds_the_tool_in_the_real_checkouts_venv_and_not_without_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2145: a gate snapshot has no venv; the wrapper reaches the installed tool by REAL_ROOT."""
    repo, real = tmp_path / "repo", tmp_path / "real"
    wrapper = bazel_admit.install(repo)
    tool = real / ".venv" / "bin" / "mikemol-bazel-admit"
    tool.parent.mkdir(parents=True)
    tool.write_text('#!/bin/sh\necho "admit $*"\n', encoding="utf-8")
    tool.chmod(stat.S_IRWXU)
    monkeypatch.setenv("BAZEL_REAL", "/real/bazel")
    monkeypatch.setenv("MIKEMOL_REAL_ROOT", str(real))
    assert bazel_admit.run_probe(["/bin/sh", str(wrapper), "test", "//t"]) == (
        "admit -- /real/bazel test //t\n"
    )
    monkeypatch.delenv("MIKEMOL_REAL_ROOT")
    assert bazel_admit.run_probe(["/bin/sh", str(wrapper), "test", "//t"]) is None


def test_admit_runs_a_heavy_verb_with_the_services_off_when_the_endpoint_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End to end: the executed command carries the off-flags and stderr says why."""
    inner = _workspace(tmp_path)
    monkeypatch.chdir(inner)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(bazel_admit, "can_connect", _down)
    run, err = _Exec(), io.StringIO()
    assert bazel_admit.admit([REAL, "test", "//t"], {}, run, err, _supports) == 0
    assert run.runs[0][0] == [REAL, "test", *bazel_admit.OFF_FLAGS, "//t"]
    assert "refuses connections" in err.getvalue()
    monkeypatch.setattr(bazel_admit, "can_connect", _up)
    again, quiet = _Exec(), io.StringIO()
    assert bazel_admit.admit([REAL, "test", "//t"], {}, again, quiet, _supports) == 0
    assert again.runs[0][0] == [REAL, "test", "//t"]
    assert "refuses connections" not in quiet.getvalue()
