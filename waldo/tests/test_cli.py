# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the waldo command line and the standard invocation shape it prints.

W1059. ⚑ THE SHAPE TEST IS THE POINT OF HALF THIS MODULE: every command the mode builds or prints
must match `env -C <abs repo> <abs interpreter> -m <module> --set <name> [--dry]` with no pipe,
chaining or inline script, so the near-misses (a relative path, a pipe, `-c`, a chained command) are
each refused, and the positive control is a command that does match.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.waldo.cli import invocation, main, matches_shape
from mikemol.waldo.pipeline import EXIT_CANNOT, EXIT_REFUSED, Seams

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.waldo.contract import Contract

_REPO = Path("/home/someone/github/luthen")
_PYTHON = Path("/home/someone/github/luthen/.venv/bin/python3")
_GOOD = f"env -C {_REPO} {_PYTHON} -m checks.apply_set --set main"
_NS = 'module.w45.kubernetes_namespace_v1.throwaway["amr-skills"]'
_JOB = 'module.forgejo.kubernetes_job_v1.forgejo_admin["forgejo"]'
_SET = {"allowed": [{"address": _NS, "actions": ["create"]}]}
_REFUSED = EXIT_REFUSED
_CANNOT = EXIT_CANNOT


def _parsed(text: str) -> dict[str, object]:
    return cast("dict[str, object]", json.loads(text))


def _seams(rows: list[dict[str, object]]) -> Seams:
    def plan(_contract: Contract) -> tuple[str | None, str]:
        return "plan-1", ""

    def summarize(_artifact: str, _contract: Contract) -> object:
        return rows

    def apply(_artifact: str, _contract: Contract) -> tuple[int, str]:
        return 0, "applied"

    def run(_argv: Sequence[str]) -> tuple[int, str]:
        return 0, ""

    return Seams(plan, summarize, apply, run, lambda: 0.0)


def _contracts(tmp_path: Path) -> Path:
    (tmp_path / "main.json").write_text(json.dumps(_SET), encoding="utf-8")
    return tmp_path


def test_the_standard_invocation_is_built_and_matches_its_shape() -> None:
    """The positive control: the built command is the documented one, with and without --dry."""
    assert invocation(_REPO, _PYTHON, "checks.apply_set", "main") == _GOOD
    assert invocation(_REPO, _PYTHON, "checks.apply_set", "main", dry=True) == _GOOD + " --dry"
    assert matches_shape(_GOOD)
    assert matches_shape(_GOOD + " --dry")


@pytest.mark.parametrize(
    "command",
    [
        "env -C luthen /usr/bin/python3 -m checks.apply_set --set main",
        "env -C /r python3 -m checks.apply_set --set main",
        "env -C /r /usr/bin/python3 -m checks.apply_set --set main | tee out",
        "env -C /r /usr/bin/python3 -m checks.apply_set --set main; id",
        "env -C /r /usr/bin/python3 -m checks.apply_set --set main && id",
        "env -C /r /usr/bin/python3 -c 'print(1)'",
        "env -C /r /usr/bin/python3 -m checks.apply_set --set 'a b'",
        "cd /r && /usr/bin/python3 -m checks.apply_set --set main",
        "env -C /r /usr/bin/python3 -m checks.apply_set",
        "env -C /r /usr/bin/python3 -m checks.apply_set --set main --extra",
    ],
)
def test_a_command_off_the_standard_shape_does_not_match(command: str) -> None:
    """Relative paths, pipes, chaining, inline scripts, spaces and extra flags are all refused."""
    assert not matches_shape(command)


def test_invocation_refuses_what_it_cannot_make_standard() -> None:
    """A relative path and a name with a space or a shell character raise instead of building."""
    with pytest.raises(ValueError, match="absolute"):
        invocation(Path("luthen"), _PYTHON, "checks.apply_set", "main")
    with pytest.raises(ValueError, match="absolute"):
        invocation(_REPO, Path("python3"), "checks.apply_set", "main")
    for name in ("a b", "a;b", "$(id)"):
        with pytest.raises(ValueError, match="standard invocation shape"):
            invocation(_REPO, _PYTHON, "checks.apply_set", name)


def test_main_runs_a_set_and_prints_one_json_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The positive control: an allowed plan is applied, one line on stdout, nothing on stderr."""
    rows: list[dict[str, object]] = [{"address": _NS, "actions": ["create"]}]
    code = main(["--set", "main"], _seams(rows), _contracts(tmp_path))
    shown = capsys.readouterr()
    assert code == 0
    assert _parsed(shown.out)["state"] == "applied"
    assert shown.out.count("\n") == 1
    assert not shown.err


def test_a_refusal_prints_the_diff_to_stderr_and_the_command_to_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A plan outside the set: exit 1, the plus line on stderr, `run` on the verdict."""
    rows: list[dict[str, object]] = [{"address": _JOB, "actions": ["update"]}]
    code = main(["--set", "main"], _seams(rows), _contracts(tmp_path), command=_GOOD)
    shown = capsys.readouterr()
    assert code == _REFUSED
    assert shown.err == f"+ {_JOB} update\n"
    verdict = _parsed(shown.out)
    assert verdict["state"] == "refused"
    assert verdict["run"] == _GOOD


def test_a_dry_flag_stops_at_matches(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--dry plans and compares only."""
    rows: list[dict[str, object]] = [{"address": _NS, "actions": ["create"]}]
    code = main(["--set", "main", "--dry"], _seams(rows), _contracts(tmp_path))
    assert code == 0
    assert _parsed(capsys.readouterr().out)["state"] == "matches"


def test_a_missing_set_is_cannot_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """No such file is exit 2 with the reason, not a traceback."""
    code = main(["--set", "nope"], _seams([]), tmp_path)
    verdict = _parsed(capsys.readouterr().out)
    assert code == _CANNOT
    assert verdict["state"] == "cannot-run"
    assert "nope" in str(verdict["why"])


def test_a_set_that_is_not_json_or_not_a_contract_is_cannot_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Broken JSON and a typo'd key are both exit 2."""
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    (tmp_path / "typo.json").write_text('{"alowed": []}', encoding="utf-8")
    assert main(["--set", "broken"], _seams([]), tmp_path) == _CANNOT
    assert main(["--set", "typo"], _seams([]), tmp_path) == _CANNOT
    assert "alowed" in capsys.readouterr().out


def test_a_command_off_the_standard_shape_is_refused_before_anything_runs(tmp_path: Path) -> None:
    """The mode will not print a command it would not itself build."""
    with pytest.raises(ValueError, match="standard invocation shape"):
        main(["--set", "main"], _seams([]), _contracts(tmp_path), command="cd /r && python3 -m x")
