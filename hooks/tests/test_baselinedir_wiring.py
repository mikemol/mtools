# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ratchet reads a split mypy baseline through `disk` (W2190).

⚑ THE CONTROLS (github:R212): the directory wins over a single file beside it, and a path that is
not the mypy baseline is read as before. The writer for this layout is `test_baselinedir_write`.
"""

from pathlib import Path

from mikemol.hooks import baselinedir, pycheck_ratchet_run
from mikemol.hooks.pycheck_ratchet import MYPY_BASELINE, RUFF_BASELINE

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
