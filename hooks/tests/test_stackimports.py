# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A stack is refused at submit when a file imports a module only a later entry adds (W1527)."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from mikemol.hooks import isolated, stackimports, stacksnap
from mikemol.hooks.stacksnap import Frozen

_CLI = "d/src/pkg/cli.py"
_NEW = "d/src/pkg/watchdogcmd.py"
_MODE = "100644"


def _frozen(path: str, blob: str) -> Frozen:
    return Frozen(path, _MODE, blob)


def _blobs(**texts: str) -> stackimports.ReadBlob:
    return texts.get


def _never(_path: str) -> bool:
    return False


def _in(*paths: str) -> stackimports.InHead:
    return lambda path: path in paths


def test_a_file_that_imports_a_module_only_a_later_entry_adds_is_a_finding() -> None:
    """The W1520 shape: cli.py frozen first, watchdogcmd.py added last."""
    entries = [("W1", [_frozen(_CLI, "b1")]), ("W2", [_frozen(_NEW, "b2")])]
    got = stackimports.findings(entries, _blobs(b1="from pkg import watchdogcmd\n"), _never)
    assert got == [
        f"W1: {_CLI} imports {_NEW}, which no earlier entry or HEAD carries (entry 2 adds it)"
    ]


def test_modules_first_is_sound() -> None:
    """The same two files in the other order land in order."""
    entries = [("W1", [_frozen(_NEW, "b2")]), ("W2", [_frozen(_CLI, "b1")])]
    assert stackimports.findings(entries, _blobs(b1="from pkg import watchdogcmd\n"), _never) == []


def test_a_module_in_head_is_not_a_finding() -> None:
    """HEAD already carries it, so the later entry only changes it."""
    entries = [("W1", [_frozen(_CLI, "b1")]), ("W2", [_frozen(_NEW, "b2")])]
    got = stackimports.findings(entries, _blobs(b1="from pkg import watchdogcmd\n"), _in(_NEW))
    assert got == []


def test_the_same_entry_may_add_both() -> None:
    """One commit carries the importer and the module together."""
    entries = [("W1", [_frozen(_CLI, "b1"), _frozen(_NEW, "b2")])]
    assert stackimports.findings(entries, _blobs(b1="from pkg import watchdogcmd\n"), _never) == []


def test_a_name_that_is_not_a_file_is_never_a_finding() -> None:
    """A class imported from the package is not a module the stack adds."""
    entries = [("W1", [_frozen(_CLI, "b1")]), ("W2", [_frozen(_NEW, "b2")])]
    assert stackimports.findings(entries, _blobs(b1="from pkg import Thing\n"), _never) == []


def test_the_from_module_and_plain_import_spellings_are_read() -> None:
    """Both a from-module import and a plain dotted import name the file."""
    entries = [("W1", [_frozen(_CLI, "b1")]), ("W2", [_frozen(_NEW, "b2")])]
    for text in ("from pkg.watchdogcmd import tick_line\n", "import pkg.watchdogcmd\n"):
        assert len(stackimports.findings(entries, _blobs(b1=text), _never)) == 1


def test_an_import_from_another_package_is_ignored() -> None:
    """Only the file's own top-level package is judged."""
    entries = [("W1", [_frozen(_CLI, "b1")]), ("W2", [_frozen(_NEW, "b2")])]
    assert (
        stackimports.findings(
            entries, _blobs(b1="import os\nfrom other import watchdogcmd\n"), _never
        )
        == []
    )


def test_a_file_outside_src_a_deletion_and_unparsable_text_are_skipped() -> None:
    """None of these can be judged, so none is refused."""
    entries = [
        ("W1", [_frozen("d/tests/t.py", "b1"), _frozen(_CLI, ""), _frozen("d/src/pkg/x.py", "b3")]),
        ("W2", [_frozen(_NEW, "b2")]),
    ]
    blobs = _blobs(b1="from pkg import watchdogcmd\n", b3="def (\n")
    assert stackimports.findings(entries, blobs, _never) == []


def test_a_blob_that_cannot_be_read_is_skipped() -> None:
    """A missing object is the gate's to report."""
    entries = [("W1", [_frozen(_CLI, "gone")]), ("W2", [_frozen(_NEW, "b2")])]
    assert stackimports.findings(entries, _blobs(), _never) == []


class _Done:
    def __init__(self, returncode: int, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


def _git(texts: dict[str, str], head: set[str]) -> isolated.EnvRunner:
    def run(argv: Sequence[str], _env: Mapping[str, str], _cwd: Path) -> _Done:
        if argv[:2] == ["cat-file", "blob"]:
            text = texts.get(argv[2])
            return _Done(0, text) if text is not None else _Done(128)
        return _Done(0 if argv[-1].removeprefix("HEAD:") in head else 128)

    return run


def _submitted(tmp_path: Path, order: list[tuple[str, str]]) -> tuple[Path, str]:
    entries = [{"waypoint": w, "subject": "s", "paths": [p]} for w, p in order]
    stack = tmp_path / "stack.json"
    stack.write_text(json.dumps(entries), encoding="utf-8")
    snap = tmp_path / "stack.snap"
    stacksnap.dump(snap, [[_frozen(p, f"b-{p}")] for _w, p in order])
    return stack, str(snap)


def test_refusal_reads_the_snapshot_and_names_the_findings(tmp_path: Path) -> None:
    """The whole submit-time path: the stack file, the frozen snapshot, git for the blobs."""
    stack, snap = _submitted(tmp_path, [("W1", _CLI), ("W2", _NEW)])
    run = _git({f"b-{_CLI}": "from pkg import watchdogcmd\n", f"b-{_NEW}": "x = 1\n"}, set())
    got = stackimports.refusal(tmp_path, stack, snap, run)
    assert got is not None
    assert "W1:" in got
    assert _NEW in got


def test_refusal_is_none_for_a_sound_order_or_no_snapshot(tmp_path: Path) -> None:
    """Modules first passes, and a stack with no snapshot is left to the gate."""
    stack, snap = _submitted(tmp_path, [("W1", _NEW), ("W2", _CLI)])
    run = _git({f"b-{_CLI}": "from pkg import watchdogcmd\n", f"b-{_NEW}": "x = 1\n"}, set())
    assert stackimports.refusal(tmp_path, stack, snap, run) is None
    assert stackimports.refusal(tmp_path, stack, "", run) is None
