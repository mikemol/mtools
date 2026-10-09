# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the prune cross-check: `--prune` and `--dry-run` against the pairing check."""

from __future__ import annotations

import shutil
import subprocess
import sys
from itertools import starmap
from pathlib import Path

import pytest

from mikemol.hooks import gen_warrants, warrant_crosscheck

_SCRIPT = Path(__file__).parent.parent.parent / warrant_crosscheck.SCRIPT
_DIST = "dist"
_MODULE = "tests/test_m.py"


def _entry(name: str, module: str) -> str:
    """Write one warrant entry whose check names `name` in `module`.

    Returns:
        the bib entry text.

    """
    return (
        f"\n@misc{{dist-{name},\n  title = {{t {name}}},\n"
        f"  check = {{python -m pytest {module} -k {name}}},\n}}\n"
    )


def _repo(root: Path, tests: list[str], warranted: list[tuple[str, str]]) -> Path:
    """Build `<root>/dist` with a test module defining `tests` and a bib warranting `warranted`.

    The real pairing script is copied in, since it is the independent derivation under test, and
    a one-row rubric stands in for the section the operands name.

    Returns:
        the bib's path.

    """
    shutil.copy(_SCRIPT, root / warrant_crosscheck.SCRIPT)
    dist = root / _DIST
    (dist / "tests").mkdir(parents=True)
    body = "".join(f"def {name}() -> None:\n    pass\n\n" for name in tests)
    (dist / _MODULE).write_text(body, encoding="utf-8")
    (dist / "rubric.tsv").write_text("sec\tA section\n", encoding="utf-8")
    bib = dist / "warrants.bib"
    bib.write_text("".join(starmap(_entry, warranted)), encoding="utf-8")
    return bib


def _run(root: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    """Run gen_warrants as a program from `root`.

    Returns:
        the completed process.

    """
    return subprocess.run(
        [sys.executable, "-m", "mikemol.hooks.gen_warrants", "--root", str(root), *flags],
        capture_output=True,
        text=True,
        check=False,
        cwd=root,
    )


def test_independent_orphans_name_the_warrants_whose_test_is_gone(tmp_path: Path) -> None:
    """The pairing check calls a warrant an orphan when no test defines the name it runs."""
    _repo(tmp_path, ["test_a"], [("test_a", _MODULE), ("test_gone", _MODULE)])
    assert warrant_crosscheck.independent_orphans(tmp_path, _DIST) == {(_MODULE, "test_gone")}


def test_a_missing_checker_is_unverifiable_never_a_pass(tmp_path: Path) -> None:
    """With no independent derivation there is nothing to compare, so the prune is refused."""
    (tmp_path / _DIST).mkdir()
    with pytest.raises(warrant_crosscheck.UnverifiableError, match=warrant_crosscheck.SCRIPT):
        warrant_crosscheck.independent_orphans(tmp_path, _DIST)


def test_a_checker_that_refuses_its_population_is_unverifiable(tmp_path: Path) -> None:
    """The checker exits 2 on a distribution with no tests; that is not an empty orphan set."""
    shutil.copy(_SCRIPT, tmp_path / warrant_crosscheck.SCRIPT)
    (tmp_path / _DIST).mkdir()
    (tmp_path / _DIST / "warrants.bib").write_text("", encoding="utf-8")
    with pytest.raises(warrant_crosscheck.UnverifiableError, match="exit 2"):
        warrant_crosscheck.independent_orphans(tmp_path, _DIST)


def test_the_difference_names_every_pair_on_which_the_two_disagree() -> None:
    """Both directions are named: only the prune, and only the pairing check."""
    prune = {(_MODULE, "test_a"), (_MODULE, "test_b")}
    pairing = {(_MODULE, "test_b"), (_MODULE, "test_c")}
    assert warrant_crosscheck.difference(prune, pairing) == [
        f"ONLY --prune WOULD DROP {_MODULE}::test_a",
        f"ONLY THE PAIRING CHECK CALLS ORPHAN {_MODULE}::test_c",
    ]
    assert not warrant_crosscheck.difference(prune, prune)


def test_would_drop_lists_each_stale_entry_with_its_key(tmp_path: Path) -> None:
    """Dry-run's list is the prune's own rule: (key, module, name) for each stale check."""
    bib = _repo(tmp_path, ["test_a"], [("test_a", _MODULE), ("test_gone", _MODULE)])
    found = gen_warrants.would_drop(tmp_path / _DIST, bib.read_text(encoding="utf-8"))
    assert found == [("dist-test_gone", _MODULE, "test_gone")]


def test_dry_run_lists_what_would_drop_changes_nothing_and_agrees(tmp_path: Path) -> None:
    """Prune and pairing agree on the stale warrant: listed, exit 0, the bib untouched."""
    bib = _repo(tmp_path, ["test_a"], [("test_a", _MODULE), ("test_gone", _MODULE)])
    before = bib.read_text(encoding="utf-8")
    done = _run(tmp_path, "--dry-run", _DIST, "m=sec")
    assert done.returncode == 0
    assert f"WOULD DROP dist-test_gone  {_MODULE}::test_gone" in done.stdout
    assert "1 would drop; equal to the pairing check's orphan set" in done.stdout
    assert bib.read_text(encoding="utf-8") == before


def test_prune_drops_the_stale_warrant_when_the_two_derivations_agree(tmp_path: Path) -> None:
    """The ordinary rename case: the stale warrant is removed and the live one kept."""
    bib = _repo(tmp_path, ["test_a"], [("test_a", _MODULE), ("test_gone", _MODULE)])
    done = _run(tmp_path, "--write", "--prune", _DIST, "m=sec")
    assert done.returncode == 0
    kept = bib.read_text(encoding="utf-8")
    assert "dist-test_a" in kept
    assert "test_gone" not in kept


def _disagreement(root: Path) -> Path:
    """Make a LIVE warrant whose note text quotes a stale selector before its real check.

    The prune reads the first selector anywhere in the entry and would drop a warrant whose test
    exists; the pairing check reads only the `check` field. That is the dangerous disagreement: a
    live warrant dropped, with a plausible count.

    Returns:
        the bib's path.

    """
    bib = _repo(root, ["test_a"], [])
    bib.write_text(
        "\n@misc{dist-test_a,\n  title = {t},\n"
        f"  note = {{see -m pytest {_MODULE} -k test_gone}},\n"
        f"  check = {{python -m pytest {_MODULE} -k test_a}},\n}}\n",
        encoding="utf-8",
    )
    return bib


def test_prune_refuses_when_the_pairing_check_disagrees_and_writes_nothing(tmp_path: Path) -> None:
    """The set the prune would drop must equal the orphan set; if not, exit 2 and no write."""
    bib = _disagreement(tmp_path)
    before = bib.read_text(encoding="utf-8")
    done = _run(tmp_path, "--write", "--prune", _DIST, "m=sec")
    assert done.returncode == gen_warrants.EXIT_UNTRANSCRIBABLE
    assert f"ONLY --prune WOULD DROP {_MODULE}::test_gone" in done.stderr
    assert bib.read_text(encoding="utf-8") == before


def test_dry_run_reports_the_disagreement_and_exits_two(tmp_path: Path) -> None:
    """A dry run shows the same verdict a prune would get, so it can be read before it is run."""
    bib = _disagreement(tmp_path)
    before = bib.read_text(encoding="utf-8")
    done = _run(tmp_path, "--dry-run", _DIST, "m=sec")
    assert done.returncode == gen_warrants.EXIT_UNTRANSCRIBABLE
    assert "DISAGREES WITH the pairing check's orphan set" in done.stdout
    assert bib.read_text(encoding="utf-8") == before


def test_prune_without_the_checker_is_refused(tmp_path: Path) -> None:
    """No count_test_functions.py at the root: the prune has nothing to be checked against."""
    bib = _repo(tmp_path, ["test_a"], [("test_a", _MODULE), ("test_gone", _MODULE)])
    (tmp_path / warrant_crosscheck.SCRIPT).unlink()
    before = bib.read_text(encoding="utf-8")
    done = _run(tmp_path, "--write", "--prune", _DIST, "m=sec")
    assert done.returncode == gen_warrants.EXIT_UNTRANSCRIBABLE
    assert warrant_crosscheck.SCRIPT in done.stderr
    assert bib.read_text(encoding="utf-8") == before
