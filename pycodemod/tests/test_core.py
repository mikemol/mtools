# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.core`: the origin's selftest arms, ported as pytest cases.

⚑⚑ EVERY NEGATIVE HAS ITS POSITIVE: an unread file is asserted beside a found escape, an UNKNOWN
beside a value, so no case passes by an instrument that sees nothing.
"""

from __future__ import annotations

import io
import tarfile
from typing import TYPE_CHECKING

import libcst as cst
import pytest

from mikemol.pycodemod import core

if TYPE_CHECKING:
    from pathlib import Path


def _expr(src: str) -> cst.BaseExpression:
    return cst.parse_expression(src)


def _rows(path: str) -> list[str]:
    """Stand in for a query: module-level, so a process pool can carry it.

    Returns:
        two rows per file, so order and completeness are both visible.

    """
    return [path, path.upper()]


def _add(archive: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def _raise_inside(tar: Path, seen: list[Path]) -> None:
    with core.corpus(str(tar)) as tree:
        seen.append(tree)
        raise LookupError


def test_double_dash_ends_flag_recognition() -> None:
    """⚑⚑ `--literal -- --selftest` must NOT see `--selftest` as a flag: THE ORIGIN'S DEFECT."""
    argv = ["prog", "--literal", "--", "--selftest", "x"]
    assert core.flagged_argv(argv) == ["--literal"]
    assert core.operand_tail(argv) == ["--selftest", "x"]


def test_without_double_dash_every_token_is_flag_side() -> None:
    """With no `--`, the whole tail is flag-side and there are no operands after it."""
    argv = ["prog", "--calls", "f"]
    assert core.flagged_argv(argv) == ["--calls", "f"]
    assert core.operand_tail(argv) == []


def test_an_invalid_escape_is_found_and_an_unreadable_file_is_reported(tmp_path: Path) -> None:
    """⚑ The found escape and the unread files are returned TOGETHER: an empty `found` is a fact."""
    good = tmp_path / "esc.py"
    good.write_text('ok = 1\nx = "a\\ b"\n', encoding="utf-8")
    latin = tmp_path / "latin.py"
    latin.write_bytes(b'x = "\xe9"\n')
    broken = tmp_path / "broken.py"
    broken.write_text("def (:\n", encoding="utf-8")
    missing = str(tmp_path / "absent.py")
    got = core.escapes([str(good), str(latin), str(broken), missing])
    assert got.found == [core.Escape(str(good), 2, 'x = "a\\ b"', "\\ ")]
    assert got.unread == [str(latin), str(broken), missing]


def test_a_clean_file_yields_nothing_and_is_read(tmp_path: Path) -> None:
    """A file with valid escapes only is neither found nor unread."""
    clean = tmp_path / "clean.py"
    clean.write_text('x = "a\\n"\n', encoding="utf-8")
    assert core.escapes([str(clean)]) == core.Escapes()


def test_escape_seq_names_the_sequence_or_a_question_mark() -> None:
    """The escape is read out of the warning text; a text naming none reads "?"."""
    assert core.escape_seq('invalid escape sequence "\\d"') == "\\d"
    assert core.escape_seq("invalid escape sequence '\\d'") == "\\d"
    assert core.escape_seq("no sequence here") == "?"


def test_a_package_resolves_to_its_directory() -> None:
    """⚑ A package is its DIRECTORY, not its `__init__.py`."""
    where, detail = core.package_root("libcst")
    assert where is not None
    assert where.endswith("libcst")
    assert where in detail


def test_a_plain_module_resolves_to_its_file() -> None:
    """A single-file module resolves to its own source file."""
    where, detail = core.package_root("tarfile")
    assert where is not None
    assert where.endswith("tarfile.py")
    assert detail == where


def test_an_absent_or_sourceless_module_says_why() -> None:
    """No such module, a malformed name and a built-in each return None WITH a reason."""
    assert core.package_root("no_such_module_anywhere") == (
        None,
        "not importable here: no such module",
    )
    where, why = core.package_root(".relative")
    assert where is None
    assert why.startswith("not importable here: ")
    assert core.package_root("sys") == (
        None,
        "importable but has no source on disk (built-in or frozen)",
    )


def test_roundtrip_reports_identity_and_each_failure(tmp_path: Path) -> None:
    """Identical source round-trips; unreadable and unparseable files say which they were."""
    ok = tmp_path / "ok.py"
    ok.write_text("x  =  1  # spacing kept\n", encoding="utf-8")
    assert core.roundtrip(str(ok)) == (True, "identical")
    bad = tmp_path / "bad.py"
    bad.write_text("def (:\n", encoding="utf-8")
    assert core.roundtrip(str(bad)) == (False, "parse failed: ParserSyntaxError")
    ok_flag, why = core.roundtrip(str(tmp_path / "absent.py"))
    assert not ok_flag
    assert why.startswith("unreadable: ")


def test_unknown_renders_as_a_word() -> None:
    """The sentinel prints as UNKNOWN, never as data."""
    assert repr(core.UNKNOWN) == "UNKNOWN"


@pytest.mark.parametrize(
    ("src", "want"),
    [
        ("3", 3),
        ("-3", -3),
        ("+3", 3),
        ("~3", -4),
        ("-1.5", -1.5),
        ("2j", 2j),
        ("'s'", "s"),
        ("'a' 'b'", "ab"),
        ("f'plain'", "plain"),
        ("True", True),
        ("None", None),
        ("not True", False),
        ("not 0", True),
    ],
)
def test_value_of_a_constant(src: str, want: core.Value) -> None:
    """A constant expression returns its value, and its shape is "literal"."""
    node = _expr(src)
    assert core.value_of(node) == want
    assert core.shape_of(node) == "literal"


@pytest.mark.parametrize(
    "src",
    [
        "flag",
        "a.b",
        "f()",
        "[1]",
        "b'x'",
        "f'{x}'",
        "-'abc'",
        "~1.5",
        "not flag",
        "'a' f'{x}'",
        "-flag",
    ],
)
def test_value_of_a_computed_expression_is_unknown(src: str) -> None:
    """⚑ Anything that is not a scalar constant is UNKNOWN — including `-"abc"`, which parses."""
    node = _expr(src)
    assert core.value_of(node) is core.UNKNOWN
    assert core.shape_of(node) == "computed"


def test_src_of_collapses_whitespace_and_marks_truncation() -> None:
    """⚑ The grouping key is bounded, and a clipped key says it was clipped."""
    node = _expr("f(a,\n    b)")
    assert core.src_of(node) == "f(a, b)"
    assert core.src_of(node, limit=7) == "f(a, b)"
    assert core.src_of(node, limit=6) == "f(a, b…"
    assert core.src_of(_expr("x" * (core.SRC_LIMIT + 1))) == "x" * core.SRC_LIMIT + "…"
    assert core.src_of(_expr("x" * core.SRC_LIMIT)) == "x" * core.SRC_LIMIT


def test_src_of_empty_text_is_unknown() -> None:
    """A node that renders to no text is UNKNOWN, not an empty key."""
    assert core.src_of(cst.Module(body=[])) is core.UNKNOWN


def test_corpus_yields_a_directory_itself(tmp_path: Path) -> None:
    """A directory is its own tree: yielded absolute, and left in place afterwards."""
    with core.corpus(str(tmp_path)) as tree:
        assert tree == tmp_path.absolute()
    assert tmp_path.is_dir()


def test_corpus_extracts_an_archive_safely_and_removes_it(tmp_path: Path) -> None:
    """⚑ `..` and absolute members are dropped; the temp tree is gone after the scope."""
    tar = tmp_path / "t.tar"
    with tarfile.open(tar, "w") as archive:
        _add(archive, "pkg/mod.py", b"x = 1\n")
        _add(archive, "pkg/../../escaped.py", b"y = 2\n")
        _add(archive, "/abs.py", b"z = 3\n")
    with core.corpus(str(tar)) as tree:
        assert (tree / "pkg" / "mod.py").read_text(encoding="utf-8") == "x = 1\n"
        assert sorted(p.name for p in tree.rglob("*.py")) == ["mod.py"]
        assert tree.name.startswith("pycodemod-corpus-")
    assert not tree.exists()
    assert not (tmp_path / "escaped.py").exists()


def test_corpus_removes_the_tree_on_the_error_path(tmp_path: Path) -> None:
    """The temp tree is removed when the body fails, too."""
    tar = tmp_path / "t.tar"
    with tarfile.open(tar, "w") as archive:
        _add(archive, "m.py", b"")
    seen: list[Path] = []
    with pytest.raises(LookupError):
        _raise_inside(tar, seen)
    assert seen
    assert not seen[0].exists()


def test_per_file_keeps_file_order_serially_and_pooled() -> None:
    """Below and above the pool threshold, every row arrives in file order."""
    few = [f"f{i}" for i in range(core.POOL_THRESHOLD - 1)]
    many = [f"f{i}" for i in range(core.POOL_THRESHOLD * 2)]
    for files in (few, many):
        want = [row for path in files for row in _rows(path)]
        assert core.per_file(_rows, files, workers=2) == want
