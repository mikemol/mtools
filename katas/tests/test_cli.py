# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `cli`: the host katas' subcommand names over the modules, driven by `main`."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from mikemol.procrun.proc import capture

from mikemol.katas import cli

if TYPE_CHECKING:
    from pathlib import Path

_EXECUTABLE = 0o755
_TODAY = "2026-10-09"
_USAGE = 2


def _script(path: Path, body: str) -> Path:
    """Write an executable shell script.

    Returns:
        its path.

    """
    path.write_text(f"#!/bin/sh\n{body}", encoding="utf-8")
    path.chmod(_EXECUTABLE)
    return path


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    """Write fake tools, a policy file pointing at them, and an empty host root.

    Returns:
        the policy file, and the file the fake tools append their calls to.

    """
    record = tmp_path / "calls.txt"
    commit_body = f'echo "commit $*" >> {record}\necho "COMMITTED x"\n'
    commit = _script(tmp_path / "commit-tool", commit_body)
    pf = _script(tmp_path / "pf-tool", f'echo "$*" >> {record}\necho "ok"\n')
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "bazelrc").write_text("# @REPO@\n", encoding="utf-8")
    (tmp_path / "templates" / "MODULE.bazel").write_text("m @REPO@\n", encoding="utf-8")
    (tmp_path / "hosts").mkdir()
    text = (
        f'root = "{tmp_path / "hosts"}"\nlogs = "{tmp_path / "logs"}"\n'
        f'commit_tool = "{commit}"\npathsforward = "{pf}"\n'
        f'host_state = "{tmp_path / "host.json"}"\nholder = "github-b3"\n'
        f'nemik = "{tmp_path / "nemik"}"\ntemplates = "{tmp_path / "templates"}"\n'
        'bazel_version = "9.9.9"\n'
    )
    policy_file = tmp_path / "katas.toml"
    policy_file.write_text(text, encoding="utf-8")
    return policy_file, record


def _repo(tmp_path: Path, name: str) -> Path:
    """Make a workstream under the host root.

    Returns:
        its directory.

    """
    path = tmp_path / "hosts" / name
    (path / ".claude").mkdir(parents=True)
    (path / ".claude" / "paths-forward.json").write_text("{}", encoding="utf-8")
    capture(("git", "init", "-q", str(path)))
    ident = ("git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(path))
    capture((*ident, "add", "-A"))
    capture((*ident, "commit", "-q", "-m", "first"))
    return path


def _run(policy_file: Path, *args: str) -> tuple[int, str]:
    """Run `main` with the policy file and capture what it wrote.

    Returns:
        the status, and the output.

    """
    out = io.StringIO()
    status = cli.main(["--policy", str(policy_file), *args], out, {}, _TODAY)
    return status, out.getvalue()


def test_a_delegated_subcommand_prints_the_mtools_command_and_exits_2(tmp_path: Path) -> None:
    """The old name leads to the new tool instead of a silent difference."""
    policy_file, _ = _setup(tmp_path)
    status, text = _run(policy_file, "gate")
    assert status == _USAGE
    assert "--gate-red" in text


def test_every_delegated_name_says_what_to_run(tmp_path: Path) -> None:
    """None of the six prints an empty hint."""
    policy_file, _ = _setup(tmp_path)
    for name in cli.DELEGATED:
        status, text = _run(policy_file, name)
        assert status == _USAGE
        assert len(text.split(": ", 2)[-1]) > len(name)


def test_an_unknown_subcommand_lists_the_usage(tmp_path: Path) -> None:
    """The usage line names the real subcommands and the delegated ones."""
    policy_file, _ = _setup(tmp_path)
    status, text = _run(policy_file, "frobnicate")
    assert status == _USAGE
    assert "status" in text
    assert "typing" in text


def test_a_missing_policy_file_is_named_not_a_traceback(tmp_path: Path) -> None:
    """The operator is told which file and why."""
    out = io.StringIO()
    status = cli.main(["--policy", str(tmp_path / "absent.toml"), "status"], out, {}, _TODAY)
    assert status == _USAGE
    assert out.getvalue().startswith("policy: ")


def test_status_prints_a_row_per_workstream(tmp_path: Path) -> None:
    """The row carries the repo's name."""
    policy_file, _ = _setup(tmp_path)
    _repo(tmp_path, "alpha")
    status, text = _run(policy_file, "status")
    assert status == 0
    assert text.startswith("alpha")


def test_pulse_runs_the_nemik_tools_the_policy_names(tmp_path: Path) -> None:
    """Status rows, then nemik-check's warnings, then the ranking, from the policy's nemik dir."""
    policy_file, _ = _setup(tmp_path)
    _repo(tmp_path, "alpha")
    nemik = tmp_path / "nemik"
    nemik.mkdir()
    _script(nemik / "nemik-check", "echo '  Warning   W1   something'\n")
    _script(nemik / "nemik-rank", "echo 'top ranked'\n")
    status, text = _run(policy_file, "pulse")
    assert status == 0
    assert text.startswith("alpha")
    assert "Warning   W1   something" in text
    assert "top ranked" in text


def test_flush_with_nothing_pending_says_so(tmp_path: Path) -> None:
    """No repo has a changed queue, so nothing starts."""
    policy_file, _ = _setup(tmp_path)
    _repo(tmp_path, "alpha")
    status, text = _run(policy_file, "flush")
    assert status == 0
    assert "nothing to start" in text


def test_flush_skip_keeps_the_named_repo_out(tmp_path: Path) -> None:
    """A repo with a changed queue is not started when `--skip` names it."""
    policy_file, _ = _setup(tmp_path)
    repo = _repo(tmp_path, "alpha")
    (repo / ".claude" / "paths-forward.json").write_text('{"x": 1}\n', encoding="utf-8")
    status, text = _run(policy_file, "flush", "--skip", "alpha")
    assert status == 0
    assert "nothing to start" in text


def test_archive_moves_letters_and_reports_the_count(tmp_path: Path) -> None:
    """Under the policy's root, the repo's inbox is archived."""
    policy_file, _ = _setup(tmp_path)
    inbox = tmp_path / "hosts" / "alpha" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "a.md").write_text("hi\n", encoding="utf-8")
    status, text = _run(policy_file, "archive", "alpha", "a.md", "gone.md")
    assert status == 0
    assert "not found: gone.md" in text
    assert "archived 1 of 2" in text
    assert (inbox / "archive" / "a.md").exists()


def test_archive_without_a_letter_is_a_usage_error(tmp_path: Path) -> None:
    """A repo alone is not enough."""
    policy_file, _ = _setup(tmp_path)
    status, _text = _run(policy_file, "archive", "alpha")
    assert status == _USAGE


def test_probe_refuses_a_repo_with_no_hook_and_exits_1(tmp_path: Path) -> None:
    """The reason is printed."""
    policy_file, _ = _setup(tmp_path)
    _repo(tmp_path, "alpha")
    status, text = _run(policy_file, "probe", "alpha")
    assert status == 1
    assert "no .githooks/pre-commit" in text


def test_precommit_lists_the_hook_of_each_repo(tmp_path: Path) -> None:
    """A repo with no hook reads NO HOOK."""
    policy_file, _ = _setup(tmp_path)
    _repo(tmp_path, "alpha")
    status, text = _run(policy_file, "precommit")
    assert status == 0
    assert "NO HOOK" in text


def test_bazelize_writes_the_scaffold_from_the_policys_templates(tmp_path: Path) -> None:
    """The version comes from the policy file, the templates from its directory."""
    policy_file, _ = _setup(tmp_path)
    (tmp_path / "hosts" / "proj").mkdir()
    status, text = _run(policy_file, "bazelize", "proj")
    assert status == 0
    assert "wrote" in text
    version = tmp_path / "hosts" / "proj" / ".bazelversion"
    assert version.read_text(encoding="utf-8") == "9.9.9\n"


def test_tick_begin_takes_the_lock_under_the_policys_holder(tmp_path: Path) -> None:
    """The fake pathsforward tool sees `--lock github-b3`."""
    policy_file, record = _setup(tmp_path)
    status, _text = _run(policy_file, "tick", "begin")
    assert status == 0
    assert "--lock github-b3" in record.read_text(encoding="utf-8")


def test_tick_end_records_the_note_and_unlocks(tmp_path: Path) -> None:
    """The ledger, the evidence with today's date, and the unlock all reach the tool."""
    policy_file, record = _setup(tmp_path)
    status, _text = _run(policy_file, "tick", "end", "--note", "did it", "--next", "then that")
    calls = record.read_text(encoding="utf-8")
    assert status == 0
    assert "--ledger W2 advanced sweep did it" in calls
    assert f"--evidence-append {_TODAY} did it --next then that" in calls
    assert "--unlock github-b3" in calls


def test_tick_without_begin_or_end_is_a_usage_error(tmp_path: Path) -> None:
    """Neither word is not a default."""
    policy_file, _ = _setup(tmp_path)
    status, _text = _run(policy_file, "tick")
    assert status == _USAGE


def test_commit_passes_its_arguments_to_mikemol_commit_unchanged(tmp_path: Path) -> None:
    """The commit tool gets the repo and the flags as typed, and its status is returned."""
    policy_file, record = _setup(tmp_path)
    status, text = _run(policy_file, "commit", "alpha", "--waypoint", "W9", "--subject", "s")
    assert status == 0
    assert "COMMITTED" in text
    assert "commit alpha --waypoint W9 --subject s" in record.read_text(encoding="utf-8")
