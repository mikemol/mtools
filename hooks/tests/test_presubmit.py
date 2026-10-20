# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The presubmit plans the gate's own bazel test inside a snapshot, and runs nothing in a test."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import presubmit

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    import pytest

    type Call = tuple[Sequence[str], Mapping[str, str]]

_ROOT = "/cache"
_PASSED_THROUGH = 7
_SNAPSHOT_PATH = "/bazel-bin/hooks/.venv/bin/mikemol-snapshot"


def _found(_repo: str) -> Path | None:
    return Path(_SNAPSHOT_PATH)


def _missing(_repo: str) -> Path | None:
    return None


def _recording(code: int = 0) -> tuple[list[Call], presubmit.Runner]:
    seen: list[Call] = []

    def run(argv: Sequence[str], env: Mapping[str, str]) -> int:
        seen.append((argv, env))
        return code

    return seen, run


def test_the_plan_wraps_bazel_test_in_a_working_tree_snapshot() -> None:
    """The snapshot of the working tree is the command's parent and bazel is its child."""
    planned = presubmit.plan("mtools", ["//hooks:mypy"], _ROOT)
    split = planned.argv.index("--")
    assert planned.argv[:split] == ("mikemol-snapshot", "mtools", "--working")
    assert planned.argv[split + 1 :][:2] == ("bazel", "test")
    assert planned.argv[-1] == "//hooks:mypy"
    assert "--keep_going" in planned.argv


def test_no_target_means_every_target_and_the_gate_s_job_limits_apply() -> None:
    """The default is `//...` and both job limits are the declared constant."""
    planned = presubmit.plan("mtools", [], _ROOT)
    assert planned.argv[-1] == "//..."
    assert f"--jobs={presubmit.JOBS}" in planned.argv
    assert f"--local_test_jobs={presubmit.JOBS}" in planned.argv


def test_the_snapshot_namespace_is_its_own_and_never_the_gate_s() -> None:
    """The snapshot root is `<root>/presubmit`, apart from the gate's namespace."""
    planned = presubmit.plan("mtools", [], _ROOT)
    assert planned.env == {presubmit.NAMESPACE_ENV: "/cache/presubmit"}


def test_main_hands_the_plan_to_the_runner_and_passes_its_exit_code_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runner's exit code is the presubmit's, unchanged."""
    monkeypatch.setenv(presubmit.ROOT_ENV, _ROOT)
    seen, run = _recording(_PASSED_THROUGH)
    assert presubmit.main(["mtools", "//x:y"], run, _found) == _PASSED_THROUGH
    assert seen[0][0][0] == _SNAPSHOT_PATH
    assert seen[0][0][-1] == "//x:y"
    assert seen[0][1] == {presubmit.NAMESPACE_ENV: "/cache/presubmit"}


def test_a_changed_path_names_its_whole_dist_and_a_root_file_names_none() -> None:
    """W1766: two files of one dist are one dist; a root file and a dot-directory are no dist."""
    paths = ["hooks/a.py", "hooks/tests/b.py", "otlp/c.py", "README.md", ".claude/d.json"]
    assert presubmit.dists_of(paths) == ("hooks", "otlp")
    assert presubmit.dists_of([]) == ()


def test_a_snapshot_tool_that_cannot_be_found_refuses_and_runs_nothing() -> None:
    """W1749: a bare name died with FileNotFoundError; now the refusal is exit 4."""
    seen, run = _recording()
    assert presubmit.main(["mtools"], run, _missing) == presubmit.EXIT_REFUSED
    assert seen == []


def test_no_repo_is_a_usage_error_and_runs_nothing() -> None:
    """A bare call prints usage and never reaches the runner."""
    seen, run = _recording()
    assert presubmit.main([], run) == presubmit.EXIT_USAGE
    assert seen == []


_REPO = "/work/mtools"
_BEHIND = 3
_FAILED_PYTEST = 5


def _has(*present: str) -> presubmit.Exists:
    held = set(present)

    def exists(path: str) -> bool:
        return path in held

    return exists


def test_each_touched_dist_with_a_venv_gets_its_whole_pytest_and_others_get_none() -> None:
    """W1767: tests/ where the dist has one, the dist directory otherwise; no venv, no step."""
    exists = _has(
        f"{_REPO}/hooks/.venv/bin/python",
        f"{_REPO}/hooks/tests",
        f"{_REPO}/rules_py/.venv/bin/python",
    )
    steps = presubmit.pytest_steps(
        _REPO, ["hooks/a.py", "rules_py/b.py", "otlp/c.py", "README.md"], exists
    )
    assert steps == [
        (
            "env",
            "-C",
            f"{_REPO}/hooks",
            f"{_REPO}/hooks/.venv/bin/python",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests",
        ),
        (
            "env",
            "-C",
            f"{_REPO}/rules_py",
            f"{_REPO}/rules_py/.venv/bin/python",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            ".",
        ),
    ]


def test_a_stack_file_gives_every_path_of_every_entry_or_none_when_malformed() -> None:
    """The reader of the stack JSON: all paths in order; anything else is None."""
    stack = '[{"paths": ["a/x.py", "b/y.py"]}, {"paths": ["c/z.py"]}]'
    assert presubmit.paths_of(stack) == ["a/x.py", "b/y.py", "c/z.py"]
    assert presubmit.paths_of("not json") is None
    assert presubmit.paths_of('{"paths": []}') is None
    assert presubmit.paths_of('[{"subject": "no paths"}]') is None


def _stack(tmp_path: Path) -> str:
    path = tmp_path / "stack.json"
    path.write_text('[{"paths": ["hooks/a.py"]}]', encoding="utf-8")
    return str(path)


def test_a_failing_pytest_ends_the_presubmit_with_its_code_before_bazel_starts(
    tmp_path: Path,
) -> None:
    """The point of it: the refusal comes from the dist's own tests, and nothing else runs."""
    ran: list[Sequence[str]] = []

    def run(argv: Sequence[str], env: Mapping[str, str]) -> int:
        del env
        ran.append(argv)
        return _FAILED_PYTEST if argv[0] == "env" else 0

    exists = _has(f"{_REPO}/hooks/.venv/bin/python", f"{_REPO}/hooks/tests")
    code = presubmit.main([_REPO, "--stack", _stack(tmp_path)], run, _found, exists)
    assert code == _FAILED_PYTEST
    assert [argv[0] for argv in ran] == ["env"]


def test_a_passing_pytest_is_followed_by_the_bazel_test(tmp_path: Path) -> None:
    """Green steps change nothing about the bazel phase: it runs, targets after the flag."""
    ran: list[Sequence[str]] = []

    def run(argv: Sequence[str], env: Mapping[str, str]) -> int:
        del env
        ran.append(argv)
        return 0

    exists = _has(f"{_REPO}/hooks/.venv/bin/python", f"{_REPO}/hooks/tests")
    code = presubmit.main([_REPO, "--stack", _stack(tmp_path), "//x:y"], run, _found, exists)
    assert code == 0
    assert [argv[0] for argv in ran] == ["env", _SNAPSHOT_PATH]
    assert ran[1][-1] == "//x:y"


def test_a_stack_flag_without_a_readable_stack_is_a_usage_error(tmp_path: Path) -> None:
    """No file after --stack, or a file that is not a stack, runs nothing."""
    seen, run = _recording()
    assert presubmit.main([_REPO, "--stack"], run, _found) == presubmit.EXIT_USAGE
    bad = tmp_path / "bad.json"
    bad.write_text("[1]", encoding="utf-8")
    assert presubmit.main([_REPO, "--stack", str(bad)], run, _found) == presubmit.EXIT_USAGE
    assert seen == []
