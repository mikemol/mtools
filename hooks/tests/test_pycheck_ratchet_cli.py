# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-pycheck --ratchet ROOT` is not checked when a tool crashes, and says which."""

from pathlib import Path

import pytest

from mikemol.hooks import pycheck_cli, pycheck_ratchet, pycheck_ratchet_run


def test_a_crashed_tool_judges_nothing_names_it_and_cannot_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tool that exits neither clean nor with findings is named, and the stage is not checked."""
    (tmp_path / pycheck_ratchet.RUFF_BASELINE).write_text("{}", encoding="utf-8")
    (tmp_path / pycheck_ratchet.MYPY_BASELINE).write_text("{}", encoding="utf-8")

    def crashed(_root: Path) -> str:
        message = "ruff exited 2"
        raise pycheck_ratchet_run.ToolFailedError(message)

    tools = pycheck_ratchet.Tools(crashed, crashed, pycheck_ratchet_run.disk)
    monkeypatch.setattr(pycheck_ratchet_run, "real", lambda: tools)
    assert pycheck_cli.main(["--ratchet", str(tmp_path)]) == pycheck_ratchet.EXIT_NOT_CHECKED
    assert "ruff exited 2; nothing judged" in capsys.readouterr().err


def test_init_then_write_through_the_flags_make_and_keep_the_baselines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--init` writes both files once, a second `--init` refuses, and `--write` keeps them."""
    tools = pycheck_ratchet.Tools(lambda _root: "[]", lambda _root: "", pycheck_ratchet_run.disk)
    monkeypatch.setattr(pycheck_ratchet_run, "real", lambda: tools)
    root = str(tmp_path)
    assert pycheck_cli.main(["--ratchet", root, "--init"]) == 0
    assert (tmp_path / pycheck_ratchet.RUFF_BASELINE).read_text(encoding="utf-8") == "{}\n"
    assert pycheck_cli.main(["--ratchet", root, "--init"]) == 1
    assert pycheck_cli.main(["--ratchet", root, "--write"]) == 0
    assert pycheck_cli.main(["--ratchet", root]) == 0
