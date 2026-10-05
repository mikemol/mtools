# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The warrant transcriber: which test functions it emits, which it skips, and when it refuses.

⚑ EVERY CASE BUILDS ITS OWN DISTRIBUTION UNDER `tmp_path` and passes it as the root, so no case
reads this repository: the root comes from the caller, never from where the module lives.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import gen_warrants

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_REFUSED = 2


def _dist(root: Path, bib: str, modules: dict[str, str]) -> None:
    """Write a distribution `d` under root: its warrants.bib and one test file per module."""
    tests = root / "d" / "tests"
    tests.mkdir(parents=True)
    (root / "d" / "warrants.bib").write_text(bib, encoding="utf-8")
    for module, body in modules.items():
        (tests / f"test_{module}.py").write_text(body, encoding="utf-8")


def _fn(name: str, doc: str = "Holds.") -> str:
    """Render one test function with a docstring.

    Returns:
        the function's source.

    """
    return f'def {name}():\n    """{doc}"""\n\n'


def test_a_new_function_is_emitted(tmp_path: Path) -> None:
    """A test with no warrant yields one entry carrying its section, title and check."""
    _dist(tmp_path, "", {"m": _fn("test_works", "It works.")})
    (entry,) = gen_warrants.emit(tmp_path, "d", [("m", "S")])
    assert entry.startswith("@misc{d-m-works,\n")
    assert "section = {S}" in entry
    assert "title  = {It works}" in entry
    assert "tests/test_m.py -k test_works}" in entry


def test_a_function_already_checked_by_file_and_name_is_skipped(tmp_path: Path) -> None:
    """A check line naming this file and this function suppresses the entry."""
    bib = "@misc{x,\n  check = {cmd:p -m pytest tests/test_m.py -k test_works},\n}\n"
    _dist(tmp_path, bib, {"m": _fn("test_works")})
    assert gen_warrants.emit(tmp_path, "d", [("m", "S")]) == []


def test_a_same_named_test_in_another_module_is_not_skipped(tmp_path: Path) -> None:
    """A check naming the function in a DIFFERENT file does not suppress this one."""
    bib = "@misc{x,\n  check = {cmd:p -m pytest tests/test_other.py -k test_works},\n}\n"
    _dist(tmp_path, bib, {"m": _fn("test_works")})
    assert len(gen_warrants.emit(tmp_path, "d", [("m", "S")])) == 1


def test_an_article_keyed_legacy_entry_is_skipped(tmp_path: Path) -> None:
    """An older entry keyed with the leading article and no check still counts as present."""
    _dist(tmp_path, "@misc{d-m-a-thing-holds,\n}\n", {"m": _fn("test_a_thing_holds")})
    assert gen_warrants.emit(tmp_path, "d", [("m", "S")]) == []


def test_a_leading_article_is_stripped_from_the_key(tmp_path: Path) -> None:
    """`test_the_thing_holds` is keyed `d-m-thing-holds`, without the article."""
    _dist(tmp_path, "", {"m": _fn("test_the_thing_holds")})
    (entry,) = gen_warrants.emit(tmp_path, "d", [("m", "S")])
    assert entry.startswith("@misc{d-m-thing-holds,\n")


def test_a_brace_in_a_docstring_is_refused_with_exit_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A docstring with a brace would corrupt the bib entry, so main exits 2 and writes nothing."""
    _dist(tmp_path, "", {"m": _fn("test_works", "Uses {x}.")})
    monkeypatch.chdir(tmp_path)
    assert gen_warrants.main(["d", "m=S"]) == _REFUSED
    assert not capsys.readouterr().out


def test_several_pairs_emit_in_the_order_given(tmp_path: Path) -> None:
    """Pairs emit in argument order, not module-name order."""
    _dist(tmp_path, "", {"a": _fn("test_one"), "b": _fn("test_two")})
    entries = gen_warrants.emit(tmp_path, "d", [("b", "S"), ("a", "T")])
    assert [e.split(",")[0] for e in entries] == ["@misc{d-b-two", "@misc{d-a-one"]


def test_nothing_but_the_count_is_printed_when_all_are_present(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With every function warranted, stdout is empty and stderr carries only the count."""
    bib = "@misc{x,\n  check = {cmd:p -m pytest tests/test_m.py -k test_works},\n}\n"
    _dist(tmp_path, bib, {"m": _fn("test_works")})
    assert gen_warrants.main(["--root", str(tmp_path), "d", "m=S"]) == 0
    captured = capsys.readouterr()
    assert not captured.out
    assert captured.err == "0 warrants\n"


def _atom(root: Path, bib: str, modules: dict[str, str]) -> None:
    """Write the repository root's layout under `a`: a bib and test modules BESIDE the script."""
    (root / "a").mkdir()
    (root / "a" / "warrants.bib").write_text(bib, encoding="utf-8")
    for module, body in modules.items():
        (root / "a" / f"test_{module}.py").write_text(body, encoding="utf-8")


def test_the_atom_layout_keys_by_root_and_checks_beside_the_script(tmp_path: Path) -> None:
    """W669: a module beside its script is keyed `root-<module>-...` and run by the hooks venv."""
    _atom(tmp_path, "", {"mutate_runner": _fn("test_a_site_is_addressed", "It is addressed.")})
    (entry,) = gen_warrants.emit(tmp_path, "a", [("mutate_runner", "S")], gen_warrants.ATOM)
    assert entry.startswith("@misc{root-mutate-runner-site-is-addressed,\n")
    assert "cmd:hooks/.venv/bin/python3 -m pytest test_mutate_runner.py -k" in entry
    assert "tests/test_mutate_runner.py" not in entry


def test_the_atom_layout_skips_a_function_its_hand_written_bib_already_checks(
    tmp_path: Path,
) -> None:
    """W669: the bib the root wrote by hand counts, so regenerating it adds only the new tests."""
    bib = "@misc{x,\n  check = {cmd:hooks/.venv/bin/python3 -m pytest test_m.py -k test_one},\n}\n"
    _atom(tmp_path, bib, {"m": _fn("test_one") + _fn("test_two")})
    got = gen_warrants.emit(tmp_path, "a", [("m", "S")], gen_warrants.ATOM)
    assert [e.split(",")[0] for e in got] == ["@misc{root-m-two"]


def test_the_layout_flag_selects_the_atom_layout_and_the_default_stays_dist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W669: `--layout atom` emits the root form; without it the same call reads `tests/`."""
    _atom(tmp_path, "", {"m": _fn("test_works")})
    assert gen_warrants.main(["--root", str(tmp_path), "--layout", "atom", "a", "m=S"]) == 0
    assert "@misc{root-m-works," in capsys.readouterr().out
    missed = False
    try:
        gen_warrants.main(["--root", str(tmp_path), "a", "m=S"])
    except FileNotFoundError:
        missed = True
    assert missed
