# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `cpuweight`: a planted cgroup-v2 and proc host is weighted, joined and verified."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from mikemol.memres import cpuweight

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_APP = "/user.slice/user-1.slice/app.slice"
_OWN = f"{_APP}/term.scope"
_SCOPE = f"{_APP}/paperkit-build.scope"
_STAT = "cpu  1 2 3\nprocs_running 8\nprocs_blocked 3\nctxt 99\n"
_RUNNING = 8
_BLOCKED = 3
_CORES = os.cpu_count() or 1
_NEW_WEIGHT = 70
_LAST_WEIGHT = 50
_SERVER_PID = "4242"
_CELL_PID = "5151"
_USAGE = 2
_FILE_RATIO = f"{_RUNNING / _CORES:.2f}"


def _host(
    tmp_path: Path,
    *,
    own: str | None = _OWN,
    scope: bool = True,
    weight: str | None = "100",
) -> cpuweight.Host:
    """Plant a fake host: our own cgroup, a proc tree, and (optionally) the build scope.

    Returns:
        The `Host` naming the planted cgroup root and proc root.

    """
    cgroup_root = tmp_path / "cgroup"
    proc = tmp_path / "proc"
    (proc / "self").mkdir(parents=True)
    (proc / "stat").write_text(_STAT, encoding="utf-8")
    cgroup_root.mkdir()
    if own is not None:
        (proc / "self" / "cgroup").write_text(f"12:cpu:/v1\n0::{own}\n", encoding="utf-8")
        (cgroup_root / own.lstrip("/")).mkdir(parents=True)
    if scope:
        node = cgroup_root / _SCOPE.lstrip("/")
        node.mkdir(parents=True, exist_ok=True)
        if weight is not None:
            (node / "cpu.weight").write_text(f"{weight}\n", encoding="utf-8")
    return cpuweight.Host(cgroup_root, proc)


def _process(
    host: cpuweight.Host,
    pid: str,
    *,
    comm: str | None = None,
    cmdline: bytes | None = None,
    cgroup: str | None = None,
) -> None:
    """Plant one fake process under the host's proc root."""
    (host.proc / pid).mkdir()
    if comm is not None:
        (host.proc / pid / "comm").write_text(f"{comm}\n", encoding="utf-8")
    if cmdline is not None:
        (host.proc / pid / "cmdline").write_bytes(cmdline)
    if cgroup is not None:
        (host.proc / pid / "cgroup").write_text(f"0::{cgroup}\n", encoding="utf-8")


def _weight_file(host: cpuweight.Host) -> Path:
    """Find the planted build scope's `cpu.weight`.

    Returns:
        Its path.

    """
    return host.cgroup_root / _SCOPE.lstrip("/") / "cpu.weight"


def test_build_cgroup_reuses_the_scope_under_our_app_slice_when_cpu_is_delegated(
    tmp_path: Path,
) -> None:
    """The scope is `<our app.slice>/paperkit-build.scope`; its path is both results."""
    host = _host(tmp_path)
    assert cpuweight.build_cgroup(host=host) == (_SCOPE, _SCOPE)
    other = host.cgroup_root / _APP.lstrip("/") / "other.scope"
    other.mkdir()
    (other / "cpu.weight").write_text("100\n", encoding="utf-8")
    assert cpuweight.build_cgroup("other.scope", host) == (f"{_APP}/other.scope",) * 2


def test_build_cgroup_without_a_cgroup_of_our_own_is_unweighted(tmp_path: Path) -> None:
    """A host with no unified cgroup line has no hierarchy to build under."""
    host = _host(tmp_path, own=None)
    assert cpuweight.build_cgroup(host=host) == (None, "no cgroup-v2 hierarchy - unweighted")


def test_build_cgroup_names_a_scope_it_cannot_create(tmp_path: Path) -> None:
    """When the slice directory is absent the mkdir fails and the reason is returned."""
    host = _host(tmp_path, scope=False)
    (host.cgroup_root / _OWN.lstrip("/")).rmdir()
    (host.cgroup_root / _APP.lstrip("/")).rmdir()
    found, why = cpuweight.build_cgroup(host=host)
    assert found is None
    assert why.startswith("cannot create ")
    assert why.endswith(" - unweighted")


def test_build_cgroup_names_a_cpu_controller_that_is_not_delegated(tmp_path: Path) -> None:
    """A scope with no `cpu.weight` file means `cpu` was not delegated to the parent."""
    host = _host(tmp_path, weight=None)
    assert cpuweight.build_cgroup(host=host) == (
        None,
        (
            f"`cpu` not delegated to {_APP} - the weight file does not exist in a cgroup we own; "
            "unweighted"
        ),
    )


def test_build_cgroup_falls_back_to_the_whole_cgroup_when_there_is_no_app_slice(
    tmp_path: Path,
) -> None:
    """Our own cgroup path is the parent when it never passes through `app.slice`."""
    host = _host(tmp_path, own="/system.slice/ssh.service", scope=False)
    node = host.cgroup_root / "system.slice" / "ssh.service" / "paperkit-build.scope"
    node.mkdir()
    (node / "cpu.weight").write_text("100\n", encoding="utf-8")
    expected = "/system.slice/ssh.service/paperkit-build.scope"
    assert cpuweight.build_cgroup(host=host) == (expected, expected)


def test_apply_sets_the_weight_once_and_then_reports_it_already_set(tmp_path: Path) -> None:
    """The first apply rewrites `100 -> 20`; the second finds it already there."""
    host = _host(tmp_path)
    assert cpuweight.apply(host=host) == (True, f"100 -> {cpuweight.DEFAULT_WEIGHT} ({_SCOPE})")
    assert _weight_file(host).read_text(encoding="utf-8") == f"{cpuweight.DEFAULT_WEIGHT}\n"
    assert cpuweight.apply(host=host) == (
        False,
        f"already at {cpuweight.DEFAULT_WEIGHT} ({_SCOPE})",
    )


def test_apply_takes_an_explicit_weight_and_an_explicit_pid(tmp_path: Path) -> None:
    """With a pid, that process's own cgroup is weighted, not the build scope."""
    host = _host(tmp_path)
    _process(host, _SERVER_PID, cgroup="/elsewhere")
    elsewhere = host.cgroup_root / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "cpu.weight").write_text("100\n", encoding="utf-8")
    assert cpuweight.apply(_NEW_WEIGHT, _SERVER_PID, host) == (
        True,
        f"100 -> {_NEW_WEIGHT} (/elsewhere)",
    )
    assert (elsewhere / "cpu.weight").read_text(encoding="utf-8") == f"{_NEW_WEIGHT}\n"
    assert _weight_file(host).read_text(encoding="utf-8") == "100\n"


def test_apply_reports_a_pid_with_no_cgroup_and_a_cgroup_with_no_weight_file(
    tmp_path: Path,
) -> None:
    """No unified cgroup, or no writable `cpu.weight`, is unweighted rather than an error."""
    host = _host(tmp_path)
    _process(host, _SERVER_PID)
    assert cpuweight.apply(pid=_SERVER_PID, host=host) == (
        False,
        "no cgroup-v2 entry (not a cgroup-v2 machine?) - unweighted",
    )
    _process(host, _CELL_PID, cgroup="/bare")
    (host.cgroup_root / "bare").mkdir()
    assert cpuweight.apply(pid=_CELL_PID, host=host) == (
        False,
        "cpu.weight not writable for /bare (cpu not delegated?) - unweighted",
    )


def test_apply_returns_the_build_cgroup_reason_when_there_is_no_build_cgroup(
    tmp_path: Path,
) -> None:
    """Without an explicit pid, a failed `build_cgroup` is the answer."""
    host = _host(tmp_path, own=None)
    assert cpuweight.apply(host=host) == (False, "no cgroup-v2 hierarchy - unweighted")


def test_join_writes_the_pid_to_cgroup_procs_and_self_means_this_process(tmp_path: Path) -> None:
    """A pid, or `self` for our own, is written to the scope's `cgroup.procs`."""
    host = _host(tmp_path)
    procs = host.cgroup_root / _SCOPE.lstrip("/") / "cgroup.procs"
    assert cpuweight.join(_SCOPE, _SERVER_PID, host) == (True, _SCOPE)
    assert procs.read_text(encoding="utf-8") == f"{_SERVER_PID}\n"
    assert cpuweight.join(_SCOPE, host=host) == (True, _SCOPE)
    assert procs.read_text(encoding="utf-8") == f"{os.getpid()}\n"


def test_join_names_a_cgroup_it_cannot_write(tmp_path: Path) -> None:
    """A cgroup directory that does not exist cannot be joined, and the reason says so."""
    ok, why = cpuweight.join("/absent", host=_host(tmp_path))
    assert not ok
    assert why.startswith("cannot join /absent (")


def test_build_servers_lists_only_processes_that_announce_a_bazel_server(tmp_path: Path) -> None:
    """The server's command line has `bazel(<workspace>)`; the client's and strangers' do not."""
    host = _host(tmp_path)
    _process(host, _SERVER_PID, cmdline=b"java\0-jar\0bazel(/work/space)\0")
    _process(host, _CELL_PID, cmdline=b"bazel\0build\0//:hook\0")
    _process(host, "77")
    (host.proc / "not-a-pid").mkdir()
    assert cpuweight.build_servers(host) == [_SERVER_PID]


def test_is_cell_matches_the_executable_names_of_a_sandbox_and_its_wrapper() -> None:
    """Only `linux-sandbox` and `process-wrapper` are cells; a shell running pgrep is not."""
    assert cpuweight.is_cell("linux-sandbox")
    assert cpuweight.is_cell("process-wrapper")
    assert not cpuweight.is_cell("bash")
    assert not cpuweight.is_cell("linux-sandbox-extra")


def test_verify_with_no_cells_has_nothing_to_verify(tmp_path: Path) -> None:
    """No cell processes at all is vacuously fine, and says so."""
    host = _host(tmp_path)
    _process(host, _SERVER_PID, comm="bash", cgroup="/elsewhere")
    assert cpuweight.verify(_SCOPE, host) == (True, "no cells running yet - nothing to verify")


def test_verify_passes_when_every_cell_is_inside_the_scope(tmp_path: Path) -> None:
    """All cells in `cg` is true, counted by COMM."""
    host = _host(tmp_path)
    _process(host, _SERVER_PID, comm="linux-sandbox", cgroup=_SCOPE)
    _process(host, _CELL_PID, comm="process-wrapper", cgroup=_SCOPE)
    assert cpuweight.verify(_SCOPE, host) == (True, f"all 2 cell(s) inside {_SCOPE}")


def test_verify_fails_naming_the_cells_outside_the_scope(tmp_path: Path) -> None:
    """A cell outside means the weight is inert, with the inside and outside counts."""
    host = _host(tmp_path)
    _process(host, _SERVER_PID, comm="linux-sandbox", cgroup=_SCOPE)
    _process(host, _CELL_PID, comm="linux-sandbox", cgroup="/elsewhere")
    assert cpuweight.verify(_SCOPE, host) == (
        False,
        f"1 cell(s) OUTSIDE {_SCOPE} (1 inside) - the weight is inert",
    )


def test_runnable_ratio_is_procs_running_per_core_and_procs_blocked(tmp_path: Path) -> None:
    """Both counters are read from the host's `stat`; the ratio divides by the core count."""
    assert cpuweight.runnable_ratio(_host(tmp_path)) == (_RUNNING / _CORES, _BLOCKED)


def test_main_report_prints_the_box_reading_and_touches_no_cgroup(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--report` is one stdout line and leaves the weight untouched."""
    host = _host(tmp_path)
    assert cpuweight.main(["--report"], host) == 0
    assert capsys.readouterr().out == (
        f"runnable/core={_FILE_RATIO} blocked={_BLOCKED} cores={os.cpu_count()}\n"
    )
    assert _weight_file(host).read_text(encoding="utf-8") == "100\n"


def test_main_weights_the_scope_joins_it_and_moves_the_servers_in(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Bare invocation sets the weight, joins, moves the server and reports on stderr."""
    host = _host(tmp_path)
    _process(host, _SERVER_PID, cmdline=b"bazel(/work/space)\0")
    assert cpuweight.main([], host) == 0
    assert capsys.readouterr().err == (
        f"cpu.weight: 100 -> {cpuweight.DEFAULT_WEIGHT} ({_SCOPE}); joined=True; "
        f"servers_moved=1; box runnable/core={_FILE_RATIO} blocked={_BLOCKED}\n"
    )
    procs = host.cgroup_root / _SCOPE.lstrip("/") / "cgroup.procs"
    assert procs.read_text(encoding="utf-8") == f"{_SERVER_PID}\n"


def test_main_takes_the_last_weight_given_in_either_spelling(tmp_path: Path) -> None:
    """`--weight N` and `--weight=N` both set it, and the later wins."""
    host = _host(tmp_path)
    assert cpuweight.main(["--weight", str(_NEW_WEIGHT)], host) == 0
    assert _weight_file(host).read_text(encoding="utf-8") == f"{_NEW_WEIGHT}\n"
    assert cpuweight.main(["--weight", str(_NEW_WEIGHT), f"--weight={_LAST_WEIGHT}"], host) == 0
    assert _weight_file(host).read_text(encoding="utf-8") == f"{_LAST_WEIGHT}\n"


def test_main_is_a_quiet_no_op_without_a_cgroup_and_never_fails_the_build(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With no cgroup-v2 the reason goes to stderr and the exit is still 0."""
    assert cpuweight.main([], _host(tmp_path, own=None)) == 0
    assert capsys.readouterr().err == "cpu.weight: no cgroup-v2 hierarchy - unweighted\n"


def test_main_verify_exits_by_whether_the_cells_are_inside_the_scope(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--verify` is 0 with the cells inside and 1 with one outside, and 1 with no scope."""
    host = _host(tmp_path)
    _process(host, _SERVER_PID, comm="linux-sandbox", cgroup=_SCOPE)
    assert cpuweight.main(["--verify"], host) == 0
    assert capsys.readouterr().err.endswith(f"cpuweight verify: all 1 cell(s) inside {_SCOPE}\n")
    _process(host, _CELL_PID, comm="linux-sandbox", cgroup="/elsewhere")
    assert cpuweight.main(["--verify"], host) == 1
    assert capsys.readouterr().err.endswith("(1 inside) - the weight is inert\n")
    assert cpuweight.main(["--verify"], _host(tmp_path / "bare", own=None)) == 1
    assert capsys.readouterr().err.endswith("cpuweight verify: no build cgroup\n")


def test_main_exec_runs_the_command_after_joining_and_refuses_an_empty_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--exec CMD...` hands CMD to execvp; `--exec` alone is exit 2."""
    host = _host(tmp_path)
    calls: list[tuple[str, list[str]]] = []

    def fake_execvp(file: str, args: list[str]) -> object:
        calls.append((file, args))
        return None

    assert cpuweight.main(["--exec", "bazel", "build", "//:x"], host, fake_execvp) == 0
    assert calls == [("bazel", ["bazel", "build", "//:x"])]
    assert cpuweight.main(["--exec"], host, fake_execvp) == _USAGE
    assert capsys.readouterr().err.endswith("cpuweight: --exec needs a command\n")
    assert len(calls) == 1
