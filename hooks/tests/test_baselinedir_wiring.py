# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ratchet reads a split mypy baseline through `disk`, and `--write` refuses it for now (W2190).

⚑ THE CONTROLS (github:R212): the directory wins over a single file beside it, a path that is not
the mypy baseline is read as before, and `--write` writes nothing while the per-module writer
(W2191) is unbuilt, because the reader takes the directory first and a rewritten single file would
lower a baseline nobody reads.
"""

import io
from pathlib import Path

from mikemol.hooks import baselinedir, pycheck_ratchet_run, pycheck_ratchet_write
from mikemol.hooks.pycheck_ratchet import EXIT_NOT_CHECKED, MYPY_BASELINE, RUFF_BASELINE, Tools

_A = '{"src/a.py": {"E1": 2}}'
_B = '{"src/b.py": {"E2": 1}}'
_BOTH = '{"src/a.py": {"E1": 2}, "src/b.py": {"E2": 1}}'


def test_the_directory_wins_over_the_single_file_beside_it_and_other_paths_read_as_before(
    tmp_path: Path,
) -> None:
    """`disk` on the mypy baseline's path answers the merged directory when one exists."""
    single = tmp_path / MYPY_BASELINE
    single.write_text('{"src/old.py": {"E9": 9}}', encoding="utf-8")
    assert pycheck_ratchet_run.disk(single) == single.read_text(encoding="utf-8")
    folder = tmp_path / baselinedir.DIR
    folder.mkdir()
    (folder / "b.json").write_text(_B, encoding="utf-8")
    (folder / "a.json").write_text(_A, encoding="utf-8")
    assert pycheck_ratchet_run.disk(single) == _BOTH
    assert pycheck_ratchet_run.disk(tmp_path / RUFF_BASELINE) is None


def _read(_path: Path) -> str | None:
    return "{}"


def _nothing(_root: Path) -> str:
    return ""


def test_write_refuses_a_split_baseline_and_writes_nothing_while_its_writer_is_unbuilt(
    tmp_path: Path,
) -> None:
    """With `mypy-baseline.d` present `--write` exits not-checked and touches no file."""
    (tmp_path / baselinedir.DIR).mkdir()
    written: list[Path] = []

    def write(path: Path, _text: str) -> None:
        written.append(path)

    err = io.StringIO()
    tools = Tools(_nothing, _nothing, _read)
    code = pycheck_ratchet_write.lower(tmp_path, tools, write, io.StringIO(), err)
    assert code == EXIT_NOT_CHECKED
    assert pycheck_ratchet_write.SPLIT_WRITE in err.getvalue()
    assert not written
