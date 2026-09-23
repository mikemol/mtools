# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-ratchet remap`: moving a baseline must not change its content.

⚑⚑ EVERY CASE DRIVES THE CLI AND ASSERTS BEHAVIOUR, AND IMPORTS NOTHING THE PATCH ADDS. Against
the pre-patch package each one therefore FAILS BY BEHAVIOUR — `remap` is an unknown argument, so
argparse exits with a usage error — rather than dying at collection on an ImportError. The exit
codes are the subcommand's external contract and are pinned here by name, not imported.

⚑ `git` IS A HOST TOOL taken from PATH: each case builds its own repository in `tmp_path` and
needs no workspace `.git`.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.ratchet import cli

if TYPE_CHECKING:
    from pathlib import Path

CLEAN = 0
REFUSED = 1
UNREADABLE = 2

_ENTRY: dict[str, object] = {"path": "src/a.py", "rule": "r1", "count": 2}
_OTHER: dict[str, object] = {"path": "src/b.py", "rule": "r2", "count": 5}
_BASE: dict[str, object] = {"version": 1, "entries": [_ENTRY]}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _commit(root: Path, **files: object) -> Path:
    """Commit each `name=body` (as `<name>.json`) in a fresh repository.

    Returns:
        The work tree root.

    """
    _git(root, "init", "-q")
    for name, body in files.items():
        (root / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")
        _git(root, "add", f"{name}.json")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    return root


def _repo(tmp_path: Path) -> Path:
    return _commit(tmp_path, b=_BASE)


def _put(root: Path, body: object, name: str = "b") -> None:
    (root / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")


def _edit(root: Path, **entry: object) -> None:
    _put(root, {"version": 1, "entries": [{**_ENTRY, **entry}]})


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    """Run the CLI in-process; a usage error (SystemExit) is an exit code like any other.

    Returns:
        (exit code, stdout + stderr).

    """
    try:
        code: int | str | None = cli.main(list(argv))
    except SystemExit as exc:
        code = exc.code
    out = capsys.readouterr()
    return (code if isinstance(code, int) else REFUSED), out.out + out.err


def test_an_unchanged_baseline_passes(tmp_path: Path,
                                      capsys: pytest.CaptureFixture[str]) -> None:
    """No diff is the trivial pass."""
    code, out = _run(capsys, "remap", str(_repo(tmp_path)), "b.json")
    assert (code, "b.json: no changes" in out) == (CLEAN, True)


def test_a_path_only_remap_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The move the guard exists to admit: only the `path` leaf changed."""
    root = _repo(tmp_path)
    _edit(root, path="src/a/leaf.py")
    code, out = _run(capsys, "remap", str(root), "b.json")
    assert (code, "non_path_leaf_diffs=0" in out) == (CLEAN, True)


def test_a_content_change_under_a_move_is_refused(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """⚑⚑ A remap that also edits a count is debt edited in under cover of a move."""
    root = _repo(tmp_path)
    _edit(root, path="src/a/leaf.py", count=3)
    code, out = _run(capsys, "remap", str(root), "b.json")
    assert (code, "! /entries/0/count" in out) == (REFUSED, True)


def test_an_added_key_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A new non-path field is growth, not relocation."""
    root = _repo(tmp_path)
    _edit(root, extra=True)
    code, out = _run(capsys, "remap", str(root), "b.json")
    assert (code, "! /entries/0/extra" in out) == (REFUSED, True)


def test_an_unreadable_side_exits_2_and_says_so(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A file absent at the revision is a fact about the reader, not a verdict.

    ⚑ Exit 2 is also argparse's usage error, so the number alone cannot tell "file unreadable"
    from "mode missing": the report line is asserted too.
    """
    root = _repo(tmp_path)
    (root / "new.json").write_text("{}", encoding="utf-8")
    code, out = _run(capsys, "remap", str(root), "new.json")
    assert (code, "new.json: error: unable to load HEAD:new.json" in out) == (UNREADABLE, True)


def test_write_keeps_the_remap_and_discards_the_rest(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`--write` projects onto the path-only remap, then the check passes."""
    root = _repo(tmp_path)
    _edit(root, path="src/a/leaf.py", count=3, extra=True)
    code, _ = _run(capsys, "remap", str(root), "b.json", "--write")
    landed: object = json.loads((root / "b.json").read_text(encoding="utf-8"))
    assert (code, landed) == (CLEAN, {"version": 1, "entries": [
        {"path": "src/a/leaf.py", "rule": "r1", "count": 2}]})


def test_the_bare_remap_does_not_mutate(tmp_path: Path,
                                        capsys: pytest.CaptureFixture[str]) -> None:
    """The cheap read is the default; a refusal leaves the file as the author left it."""
    root = _repo(tmp_path)
    _edit(root, count=3)
    before = (root / "b.json").read_bytes()
    code, _ = _run(capsys, "remap", str(root), "b.json")
    assert (code, (root / "b.json").read_bytes()) == (REFUSED, before)


def test_a_type_change_is_one_leaf(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A dict becoming a list differs at its own pointer, not below it."""
    root = _commit(tmp_path, b={"x": {"a": 1}})
    _put(root, {"x": [1]})
    code, out = _run(capsys, "remap", str(root), "b.json")
    assert (code, "non_path_leaf_diffs=1" in out, "! /x\n" in out) == (REFUSED, True, True)


def test_a_deleted_path_key_is_refused(tmp_path: Path,
                                       capsys: pytest.CaptureFixture[str]) -> None:
    """P2: a `path` that is now MISSING is not a path rewrite — the entry lost its identity."""
    root = _repo(tmp_path)
    _put(root, {"version": 1, "entries": [{"rule": "r1", "count": 2}]})
    code, out = _run(capsys, "remap", str(root), "b.json")
    assert (code, "! /entries/0/path" in out) == (REFUSED, True)


def test_a_payload_under_a_path_key_is_refused_and_not_written(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """P4: a path string that became a container carrying counts is a payload, not a path.

    ⚑⚑ AND `--write` MUST NOT LAUNDER IT: the projection keeps the revision's string.
    """
    root = _repo(tmp_path)
    _edit(root, path={"count": 999, "path": "src/z.py"})
    code, out = _run(capsys, "remap", str(root), "b.json")
    wcode, _ = _run(capsys, "remap", str(root), "b.json", "--write")
    landed: object = json.loads((root / "b.json").read_text(encoding="utf-8"))
    assert (code, "! /entries/0/path" in out, wcode, landed) == (REFUSED, True, CLEAN, _BASE)


def test_a_key_named_with_a_dotted_path_suffix_is_not_a_path_leaf(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """P5: pointers are segment tuples, so a key literally named `x.path` is not `path`."""
    root = _commit(tmp_path, b={"x.path": "a"})
    _put(root, {"x.path": "b"})
    code, out = _run(capsys, "remap", str(root), "b.json")
    assert (code, "! /x.path" in out) == (REFUSED, True)


def test_two_entries_collapsed_onto_one_path_are_refused(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """P7: two identities sharing one path is a duplicate, not a move — even under `--write`."""
    root = _commit(tmp_path, b={"entries": [_ENTRY, _OTHER]})
    body = {"entries": [_ENTRY, {**_OTHER, "path": "src/a.py"}]}
    _put(root, body)
    code, out = _run(capsys, "remap", str(root), "b.json")
    wcode, _ = _run(capsys, "remap", str(root), "b.json", "--write")
    landed: object = json.loads((root / "b.json").read_text(encoding="utf-8"))
    assert (code, "! /entries: path collision" in out, wcode, landed) == (
        REFUSED, True, REFUSED, body)


def test_two_entries_swapping_paths_pass_as_documented_residue(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """P1, RESIDUE: a swap moves each entry's counts to the other's path, and PASSES.

    ⚑⚑ This arm pins a known blind spot rather than a virtue; the module docstring records it.
    If it ever starts refusing, the docstring's residue claim is what must change with it.
    """
    root = _commit(tmp_path, b={"entries": [_ENTRY, _OTHER]})
    _put(root, {"entries": [{**_ENTRY, "path": "src/b.py"}, {**_OTHER, "path": "src/a.py"}]})
    code, _ = _run(capsys, "remap", str(root), "b.json")
    assert code == CLEAN


def test_a_rev_cannot_inject_a_git_option(tmp_path: Path,
                                          capsys: pytest.CaptureFixture[str]) -> None:
    """`--end-of-options`: a rev spelled like `--output=FILE` is a revision, not an option."""
    root = _repo(tmp_path)
    sink = tmp_path / "sink"
    code, out = _run(capsys, "remap", str(root), "b.json", f"--rev=--output={sink}")
    assert (code, "b.json: error:" in out, sink.exists()) == (UNREADABLE, True, False)


def test_write_is_all_or_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A second file failing to load must leave the first as the author left it."""
    root = _repo(tmp_path)
    _edit(root, path="src/a/leaf.py", count=3)
    (root / "c.json").write_text("{not json", encoding="utf-8")
    before = (root / "b.json").read_bytes()
    code, out = _run(capsys, "remap", str(root), "b.json", "c.json", "--write")
    assert (code, "c.json: error:" in out, (root / "b.json").read_bytes()) == (
        UNREADABLE, True, before)


def test_a_pure_reorder_is_refused_as_documented_residue(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """P6, RESIDUE: reordering entries changes no identity, yet is REFUSED (index comparison).

    ⚑⚑ Pins the module docstring's P6 claim: a false alarm, never a laundered change.
    """
    root = _commit(tmp_path, b={"entries": [_ENTRY, _OTHER]})
    _put(root, {"entries": [_OTHER, _ENTRY]})
    code, out = _run(capsys, "remap", str(root), "b.json")
    assert (code, "! /entries/0/count" in out) == (REFUSED, True)


def test_a_write_failure_on_the_second_file_leaves_the_first_untouched(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """R1: outputs are staged as temps and replaced only once all are written.

    ⚑ The second file lives in a READ-ONLY directory (and is itself read-only), so staging it
    fails. Skipped only where permissions do not bind (e.g. running as root). An escaping
    OSError is recorded as a code, so the pre-follow-up arm fails by assertion, not by error.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    sub = root / "sub"
    sub.mkdir()
    for rel in ("b.json", "sub/c.json"):
        (root / rel).write_text(json.dumps(_BASE), encoding="utf-8")
        _git(root, "add", rel)
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    edited = {"version": 1, "entries": [{**_ENTRY, "count": 3}]}
    for rel in ("b.json", "sub/c.json"):
        (root / rel).write_text(json.dumps(edited), encoding="utf-8")
    before = (root / "b.json").read_bytes()
    (sub / "c.json").chmod(0o444)
    sub.chmod(0o555)
    try:
        if os.access(sub, os.W_OK):
            pytest.skip("directory permissions do not bind for this user")
        try:
            code, out = _run(capsys, "remap", str(root), "b.json", "sub/c.json", "--write")
        except OSError as exc:
            code, out = -1, str(exc)
    finally:
        sub.chmod(0o755)
    assert (code, "sub/c.json: error:" in out, "nothing written" in out,
            (root / "b.json").read_bytes(), sorted(p.name for p in sub.iterdir())) == (
        UNREADABLE, True, True, before, ["c.json"])


def test_write_keeps_the_source_formatting(tmp_path: Path,
                                           capsys: pytest.CaptureFixture[str]) -> None:
    """A compact source stays compact and an indent-4 source keeps indent 4: no churn diff."""
    root = _commit(tmp_path, b=_BASE, d=_BASE)
    _put(root, {"version": 1, "entries": [{**_ENTRY, "count": 3}]})
    wide = {"version": 1, "entries": [{**_ENTRY, "count": 3}]}
    (root / "d.json").write_text(json.dumps(wide, indent=4) + "\n", encoding="utf-8")
    code, _ = _run(capsys, "remap", str(root), "b.json", "d.json", "--write")
    assert (code, (root / "b.json").read_text(encoding="utf-8"),
            (root / "d.json").read_text(encoding="utf-8")) == (
        CLEAN, json.dumps(_BASE), json.dumps(_BASE, indent=4) + "\n")
