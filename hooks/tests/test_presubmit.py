# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The presubmit plans the gate's own bazel test inside a snapshot, and runs nothing in a test."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import presubmit

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    import pytest

    type Call = tuple[Sequence[str], Mapping[str, str]]

_ROOT = "/cache"
_PASSED_THROUGH = 7


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
    assert presubmit.main(["mtools", "//x:y"], run) == _PASSED_THROUGH
    assert seen[0][0][-1] == "//x:y"
    assert seen[0][1] == {presubmit.NAMESPACE_ENV: "/cache/presubmit"}


def test_no_repo_is_a_usage_error_and_runs_nothing() -> None:
    """A bare call prints usage and never reaches the runner."""
    seen, run = _recording()
    assert presubmit.main([], run) == presubmit.EXIT_USAGE
    assert seen == []
