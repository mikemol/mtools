# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The capture tracer's snapshot refuses symlinks and never follows them (W193).

Operator ruling 2026-10-02: symlinks are inherently unsafe and unwanted, and the differential
harness never creates one. These tests make links only inside pytest's own temp directory, because
a refusal cannot be shown without something to refuse.
"""

from pathlib import Path

from differential.capture import REFUSED, snapshot


def test_a_symlink_in_a_snapshotted_tree_is_refused_not_followed(tmp_path: Path) -> None:
    """A link to a file or to a directory under a walked tree is recorded as REFUSED, unread.

    Before W193 a file link was read through (its target's text recorded as its own) and a
    directory link was dropped silently, so case 110's link vanished and the case passed vacuously.
    """
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "gen.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "bazel-proj").symlink_to(tmp_path / "out")
    (tmp_path / "alias.py").symlink_to(tmp_path / "a.py")
    got = snapshot(str(tmp_path))
    assert got[f"{tmp_path}//bazel-proj"] == REFUSED
    assert got[f"{tmp_path}//alias.py"] == REFUSED
    assert got[f"{tmp_path}//a.py"] == "y = 2\n"
    assert f"{tmp_path}//bazel-proj/gen.py" not in got, "the directory link was descended"


def test_a_symlink_named_as_an_operand_is_refused_not_read(tmp_path: Path) -> None:
    """A link passed directly as a file operand is recorded as REFUSED, not as its target's text."""
    (tmp_path / "secret.txt").write_text("not for the snapshot\n", encoding="utf-8")
    link = tmp_path / "link.py"
    link.symlink_to(tmp_path / "secret.txt")
    got = snapshot(str(link))
    assert got[str(link)] == REFUSED
    assert "not for the snapshot\n" not in got.values()
