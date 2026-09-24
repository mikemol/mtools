# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The Python edit gate: which edits it judges, what the checkers say, what an absent one does.

⚑ PORTED FROM substrate's in-file selftest (letter 2026-09-22), one case per function. Arms that
need a checker build a fixture project whose `.venv` is THIS distribution's venv, which carries
ruff and mypy as runtime dependencies — so they skip only when that venv is absent, and say so.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from mikemol.hooks import pycheck, pycheck_message

_HOST_VENV = Path(sys.executable).absolute().parent.parent
_needs_checkers = pytest.mark.skipif(
    not (_HOST_VENV / "bin" / "ruff").exists(), reason="no ruff beside this interpreter"
)

_CLEAN = '"""A clean probe."""\n\nimport os\n\nSEP: str = os.sep\n'
_IMPORT_ONLY = '"""A probe."""\n\nimport os\n'
_USE_ONLY = '"""A probe."""\n\nSEP: str = os.sep\n'

# One more than the threshold, so the routing arm crosses it by construction.
_OVER = pycheck_message.PAYABLE_IN_ONE_EDIT + 1


def _project(tmp_path: Path, *, venv: bool = True, select: str = '["F"]') -> Path:
    """Write a fixture project (ruff rules `select`, strict mypy, one excluded dir).

    Returns:
        the project root.

    """
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fx"\n\n[tool.ruff]\nextend-exclude = ["gen"]\n\n'
        f"[tool.ruff.lint]\nselect = {select}\n\n[tool.mypy]\nstrict = true\n",
        encoding="utf-8",
    )
    if venv:
        (tmp_path / ".venv").symlink_to(_HOST_VENV)
    return tmp_path


def _main(
    monkeypatch: pytest.MonkeyPatch, record: dict[str, object], *, own: str
) -> None:
    """Run `main()` over one payload with this hook's switch set as given."""
    monkeypatch.setenv(pycheck.OWN_SWITCH, own)
    monkeypatch.setenv("STRUCT_HOOK_BLOCK", "0")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(record)))
    assert pycheck.main() == 0


def _write(path: Path, content: str) -> dict[str, object]:
    """Build a Write payload.

    Returns:
        the payload record.

    """
    tool_input: dict[str, object] = {"file_path": str(path), "content": content}
    return {"tool_name": "Write", "tool_input": tool_input}


# --- the fold, pure ---

def test_a_finding_beside_a_could_not_run_refuses_and_states_the_blindness() -> None:
    """Mixed roster: the finding survives, and the coverage note names what did not run."""
    ok, report = pycheck.compose([("ruff", (False, "F401")), ("mypy", (None, "mypy absent"))])
    assert ok is False
    assert "mypy absent" in report


def test_roster_order_does_not_change_the_verdict() -> None:
    """Permuting the mixed roster still refuses — the first-hit defect cannot return."""
    assert pycheck.compose([("mypy", (None, "x")), ("ruff", (False, "F401"))])[0] is False


def test_clean_under_partial_coverage_is_unknown() -> None:
    """One clean, one absent is UNKNOWN; the positive control is full coverage reading clean."""
    assert pycheck.compose([("ruff", (True, "")), ("mypy", (None, "x"))])[0] is None
    assert pycheck.compose([("ruff", (True, "")), ("mypy", (True, ""))])[0] is True


def test_an_empty_roster_is_unknown() -> None:
    """Zero checkers is never a green."""
    assert pycheck.compose([])[0] is None


# --- syntax, pure ---

def test_unparseable_content_names_its_error() -> None:
    """A truncated def is a reason; parseable source is the empty string."""
    assert pycheck.syntax_error("def broken(\n", "a.py")
    assert not pycheck.syntax_error(_CLEAN, "a.py")


def test_a_nul_byte_refuses() -> None:
    """The ValueError path (no position) still yields a reason."""
    assert pycheck.syntax_error("x = 1\x00\n", "a.py")


# --- the message, pure ---

def test_an_unused_import_names_the_one_write_grain() -> None:
    """Both ruff spellings trip the grain note; an unrelated rule is the control."""
    assert "ONE Edit" in pycheck_message.render("F401 [*] `os` imported but unused", "a.py")
    assert "ONE Edit" in pycheck_message.render("unused-import: [*] `os` imported", "a.py")
    assert "ONE Edit" not in pycheck_message.render("line-too-long: E501", "a.py")


def test_mypy_name_defined_names_the_grain() -> None:
    """The mypy undefined-name code trips the note too."""
    msg = pycheck_message.render('a.py:1: error: Name "os" is not defined  [name-defined]', "a.py")
    assert "ONE Edit" in msg


def test_a_large_debt_routes_to_splitting() -> None:
    """Over the threshold the advice changes; under it, it does not."""
    over = "\n".join(f"a.py:{i}: error: x" for i in range(_OVER))
    assert f"{_OVER} FINDINGS" in pycheck_message.render(over, "a.py")
    assert "FINDINGS —" not in pycheck_message.render("a.py:1: error: x", "a.py")


def test_the_refusal_is_bounded_and_says_so() -> None:
    """A long report is clipped with the withheld count."""
    long = "\n".join(f"line {i}" for i in range(_OVER * 2))
    assert "withheld" in pycheck_message.clip(long, pycheck_message.MAX_LINES)


# --- the hook, through main() ---

def test_a_non_python_write_is_not_judged(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A `.json` write never reaches a checker, even armed with no venv."""
    root = _project(tmp_path, venv=False)
    _main(monkeypatch, _write(root / "settings.json", "{}"), own="1")
    assert not capsys.readouterr().out


def test_an_armed_hook_with_no_venv_refuses_and_names_the_repair(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Armed, a project without checkers is a deny naming `uv sync` — never a silent allow."""
    root = _project(tmp_path, venv=False)
    _main(monkeypatch, _write(root / "src" / "a.py", _CLEAN), own="1")
    out = capsys.readouterr().out
    assert '"deny"' in out
    assert "uv sync" in out


def test_an_unarmed_hook_with_no_venv_advises_on_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Unarmed: nothing on stdout, the advisory on stderr."""
    root = _project(tmp_path, venv=False)
    _main(monkeypatch, _write(root / "src" / "a.py", _CLEAN), own="0")
    got = capsys.readouterr()
    assert not got.out
    assert "cannot render a verdict" in got.err


def test_an_unparseable_write_refuses_without_any_checker(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Syntax is decided before the roster — but only once a venv exists to run it."""
    root = _project(tmp_path)
    _main(monkeypatch, _write(root / "src" / "a.py", "def broken(\n"), own="1")
    assert "[syntax]" in capsys.readouterr().out


@_needs_checkers
def test_an_import_alone_is_refused_with_the_grain(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The first half of a split edit is refused, and the refusal names the grain."""
    root = _project(tmp_path)
    _main(monkeypatch, _write(root / "src" / "a.py", _IMPORT_ONLY), own="1")
    out = capsys.readouterr().out
    assert "F401" in out
    assert "ONE Edit" in out


@_needs_checkers
def test_a_use_alone_is_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The second half alone is refused too (F821)."""
    root = _project(tmp_path)
    _main(monkeypatch, _write(root / "src" / "a.py", _USE_ONLY), own="1")
    assert "F821" in capsys.readouterr().out


@_needs_checkers
def test_import_and_use_in_one_write_is_admitted(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The not-deny arm: both halves in one write pass the same fixture."""
    root = _project(tmp_path)
    _main(monkeypatch, _write(root / "src" / "a.py", _CLEAN), own="1")
    assert not capsys.readouterr().out


@_needs_checkers
def test_extend_exclude_reaches_an_in_flight_edit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """`--force-exclude`: the same F401 content is admitted under `gen/`, refused under `src/`."""
    root = _project(tmp_path)
    _main(monkeypatch, _write(root / "gen" / "a.py", _IMPORT_ONLY), own="1")
    assert not capsys.readouterr().out
    _main(monkeypatch, _write(root / "src" / "a.py", _IMPORT_ONLY), own="1")
    assert "F401" in capsys.readouterr().out


@_needs_checkers
def test_a_format_dirty_write_is_refused_though_ruff_check_passes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Content that `ruff check` and mypy pass but `ruff format --check` fails is refused.

    ⚑⚑ Measured by linux-sources (its parity run against this hook, 2026-09-24): without the
    format bar the edit gate ADMITS a file the commit gate then refuses, the gap a per-edit gate
    exists to close. The control is the clean write above, which is already formatted.
    """
    root = _project(tmp_path)
    _main(monkeypatch, _write(root / "src" / "a.py", '"""A probe."""\n\nX: int=1\n'), own="1")
    assert "format" in capsys.readouterr().out


@_needs_checkers
def test_writing_a_missing_package_marker_is_admitted(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A new `__init__.py` in a markerless directory is admitted; a module beside it is not.

    ⚑⚑ Measured by linux-sources: the write that SUPPLIES the marker was refused with INP001
    ("add an __init__.py"), because pre-write the marker is not on disk yet. Only a file named
    exactly `__init__.py` is exempt from INP001, so a plain module in the same directory is still
    refused, the arm that keeps the exemption from widening.
    """
    root = _project(tmp_path, select='["INP"]')
    _main(monkeypatch, _write(root / "zz_nopkg" / "__init__.py", '"""A package."""\n'), own="1")
    assert not capsys.readouterr().out
    _main(monkeypatch, _write(root / "zz_nopkg" / "mod.py", '"""A module."""\n'), own="1")
    assert "INP001" in capsys.readouterr().out


def test_a_malformed_payload_denies_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Garbage on stdin exits 0 and denies nothing."""
    monkeypatch.setenv(pycheck.OWN_SWITCH, "1")
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert pycheck.main() == 0
    assert not capsys.readouterr().out
