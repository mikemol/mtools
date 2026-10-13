# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-pycheck --install SRC DEST`: DEST is written last and only when clean.

W1087. ⚑ THE ADMITTED DRAFT IS THE POSITIVE CONTROL: a clean draft is formatted, judged and placed,
so the refusal that leaves DEST byte-for-byte untouched, the unreadable draft, the missing formatter
and the link are refusals of those draft states and not of every draft. The edit gate and the
formatter are injected; no link is created (the guard is told of one).
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import pycheck_cli
from mikemol.hooks.pycheck_install import (
    EXIT_INSTALLED,
    EXIT_NOT_CHECKED,
    EXIT_REFUSED,
    Gate,
    install,
)

if TYPE_CHECKING:
    import pytest

_DRAFT = "x=1\n"
_FORMATTED = "x = 1\n"
_REPORT = "ruff: F401 unused import"


class _World:
    """A stand-in gate and formatter that record what they were asked and answer as told."""

    def __init__(
        self, *, ok: bool | None = True, formats: bool = True, report: str = _REPORT
    ) -> None:
        self.ok = ok
        self.formats = formats
        self.report = report
        self.judged: list[tuple[str, str]] = []
        self.formatted_for: list[Path] = []

    def gate(self) -> Gate:
        return Gate(self._analyze, self._format)

    def _analyze(self, content: str, path: str) -> tuple[bool | None, str]:
        self.judged.append((content, path))
        return self.ok, self.report

    def _format(self, path: Path, text: str, _err: object) -> str | None:
        self.formatted_for.append(path)
        return text.replace("x=1", "x = 1") if self.formats else None


def _run(src: Path, dest: Path, world: _World) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = install(src, dest, world.gate(), out, err)
    return code, out.getvalue(), err.getvalue()


def _draft(tmp_path: Path, text: str = _DRAFT, name: str = "draft.txt") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_a_clean_draft_is_formatted_judged_as_dest_and_placed(tmp_path: Path) -> None:
    """The positive control: the formatted text is judged under DEST's name, then written."""
    world = _World()
    dest = tmp_path / "pkg" / "mod.py"
    code, out, _err = _run(_draft(tmp_path), dest, world)
    assert code == EXIT_INSTALLED
    assert dest.read_text(encoding="utf-8") == _FORMATTED
    assert world.judged == [(_FORMATTED, str(dest))]
    assert world.formatted_for == [dest]
    assert "installed" in out


def test_a_refused_draft_prints_the_whole_report_and_leaves_dest_untouched(tmp_path: Path) -> None:
    """Exit 1 and the report; an existing DEST keeps its bytes and no temporary file is left."""
    dest = tmp_path / "mod.py"
    dest.write_text("original = 1\n", encoding="utf-8")
    code, out, _err = _run(_draft(tmp_path), dest, _World(ok=False))
    assert code == EXIT_REFUSED
    assert _REPORT in out
    assert dest.read_text(encoding="utf-8") == "original = 1\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["draft.txt", "mod.py"]


def test_a_refused_draft_does_not_create_dest(tmp_path: Path) -> None:
    """A new DEST that would be dirty is never created, not even its directory."""
    dest = tmp_path / "newpkg" / "mod.py"
    code, _out, _err = _run(_draft(tmp_path), dest, _World(ok=False))
    assert code == EXIT_REFUSED
    assert not dest.parent.exists()


def test_no_verdict_is_not_checked_and_writes_nothing(tmp_path: Path) -> None:
    """The gate could not judge: exit 3, the reason on stderr, DEST absent."""
    dest = tmp_path / "mod.py"
    code, _out, err = _run(_draft(tmp_path), dest, _World(ok=None, report="no checker"))
    assert code == EXIT_NOT_CHECKED
    assert "no verdict could be rendered: no checker" in err
    assert not dest.exists()


def test_no_formatter_is_not_checked_and_the_gate_is_never_asked(tmp_path: Path) -> None:
    """A draft that cannot be formatted for its place is not judged unformatted."""
    world = _World(formats=False)
    dest = tmp_path / "mod.py"
    code, _out, _err = _run(_draft(tmp_path), dest, world)
    assert code == EXIT_NOT_CHECKED
    assert not world.judged
    assert not dest.exists()


def test_an_unreadable_draft_is_not_checked(tmp_path: Path) -> None:
    """A missing SRC: exit 3 naming it, nothing written."""
    dest = tmp_path / "mod.py"
    code, _out, err = _run(tmp_path / "absent.txt", dest, _World())
    assert code == EXIT_NOT_CHECKED
    assert "cannot be read" in err
    assert not dest.exists()


def test_a_non_python_file_is_placed_without_the_gate_and_says_so(tmp_path: Path) -> None:
    """The edit gate judges Python only: a .toml is copied, the gate and formatter never run."""
    world = _World(ok=False)
    dest = tmp_path / "conf" / "settings.toml"
    code, out, _err = _run(_draft(tmp_path, "a = 1\n"), dest, world)
    assert code == EXIT_INSTALLED
    assert dest.read_text(encoding="utf-8") == "a = 1\n"
    assert "not Python, so not gated" in out
    assert not world.judged
    assert not world.formatted_for


def test_a_link_is_refused_for_the_draft_the_file_and_its_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard refuses a path it is told is a link; none is created to test it."""

    def only_linked(self: Path) -> bool:
        return self.name == "linked"

    monkeypatch.setattr(Path, "is_symlink", only_linked)
    src = _draft(tmp_path)
    for dest in (tmp_path / "linked", tmp_path / "linked" / "mod.py"):
        code, _out, err = _run(src, dest, _World())
        assert code == EXIT_NOT_CHECKED
        assert "is a link" in err
    code, _out, err = _run(_draft(tmp_path, name="linked"), tmp_path / "mod.py", _World())
    assert (code, "is a link" in err) == (EXIT_NOT_CHECKED, True)


def test_the_flag_takes_exactly_two_paths(capsys: pytest.CaptureFixture[str]) -> None:
    """--install with one path, or three, is the usage message, not an install."""
    assert pycheck_cli.main(["--install", "only-one"]) == pycheck_cli.EXIT_USAGE
    assert pycheck_cli.main(["--install", "a", "b", "c"]) == pycheck_cli.EXIT_USAGE
    assert "--install SRC DEST" in capsys.readouterr().err
