# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for a card's manifest: exact repo-relative files only, set whole, or refused (W1426).

⚑ THE CONTROLS ARE THE SIX WAYS A MANIFEST STOPS BEING A SET OF NAMED FILES: a directory, a glob, an
absolute path, a `..` step, a link and a duplicate. Each is refused at write time naming the path,
and a refused write leaves the stored manifest as it was. The positive checks go through the real
command (`--update W2 --manifest ... --size ...`), so the flag plumbing is exercised too.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import cli, manifest
from mikemol.pathsforward.ops import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

Doc = dict[str, object]


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    # A project root with one card W1 minted into its queue; returns (state file, project root).
    root = tmp_path / "myrepo"
    state = root / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    doc: Doc = {"counter": 1, "waypoints": [], "project_root": str(root)}
    state.write_text(json.dumps(doc), encoding="utf-8")
    assert cli.main(["--state", str(state), "--add", "a card"]) == cli.EXIT_OK
    return state, root


def _card(state: Path) -> Doc:
    doc = cast("Doc", json.loads(state.read_text(encoding="utf-8")))
    return cast("list[Doc]", doc["waypoints"])[0]


def test_exact_new_and_existing_files_pass_and_the_list_is_set_whole(tmp_path: Path) -> None:
    """A file that exists and one that will be created are both fine; the order is kept."""
    state, root = _repo(tmp_path)
    (root / "old.py").write_text("x", encoding="utf-8")
    base = ["--state", str(state), "--update", "W2"]
    assert cli.main([*base, "--manifest", "old.py", "new/mod.py", "--size", "small"]) == 0
    assert _card(state)["manifest"] == ["old.py", "new/mod.py"]
    assert _card(state)["size_class"] == "small"
    assert cli.main([*base, "--manifest", "other.py"]) == 0
    assert _card(state)["manifest"] == ["other.py"]


def test_a_bare_manifest_and_an_empty_size_clear_them(tmp_path: Path) -> None:
    """The way to withdraw a claim: bare --manifest empties the list, --size '' drops the class."""
    state, _ = _repo(tmp_path)
    base = ["--state", str(state), "--update", "W2"]
    assert cli.main([*base, "--manifest", "a.py", "--size", "medium"]) == 0
    assert cli.main([*base, "--manifest", "--size", ""]) == 0
    assert _card(state)["manifest"] is None
    assert _card(state)["size_class"] is None


def test_a_directory_through_the_command_is_refused_and_the_old_manifest_stays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: `--manifest src` where src is a directory exits 2 naming it; nothing changes."""
    state, root = _repo(tmp_path)
    (root / "src").mkdir()
    base = ["--state", str(state), "--update", "W2"]
    assert cli.main([*base, "--manifest", "kept.py"]) == 0
    assert cli.main([*base, "--manifest", "src"]) == cli.EXIT_REFUSED
    assert "'src' is a directory" in capsys.readouterr().err
    assert _card(state)["manifest"] == ["kept.py"]


@pytest.mark.parametrize(
    ("bad", "why"),
    [
        ("pkg/", "ends in '/'"),
        ("src/*.py", "glob character"),
        ("a/[ab].py", "glob character"),
        ("/etc/passwd", "absolute"),
        ("../outside.py", "'..'"),
        ("", "empty"),
        (" padded.py", "surrounding spaces"),
    ],
)
def test_each_way_to_stop_naming_a_file_is_refused_with_its_reason(
    tmp_path: Path, bad: str, why: str
) -> None:
    """Directory-ish, glob, absolute, parent-step, empty and padded entries each name the fault."""
    with pytest.raises(RefusedError, match=why):
        manifest.check([bad], tmp_path)


def test_a_link_and_a_duplicate_are_refused(tmp_path: Path) -> None:
    """A symlink is never followed (the standing rule); a path listed twice is a mistake."""
    (tmp_path / "real.py").write_text("x", encoding="utf-8")
    (tmp_path / "link.py").symlink_to("real.py")
    with pytest.raises(RefusedError, match="is a link"):
        manifest.check(["link.py"], tmp_path)
    with pytest.raises(RefusedError, match="listed twice"):
        manifest.check(["real.py", "real.py"], tmp_path)


def test_a_size_outside_the_enum_is_a_usage_refusal(tmp_path: Path) -> None:
    """Only small, medium and large (or '' to clear) are accepted by the parser."""
    state, _ = _repo(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(["--state", str(state), "--update", "W2", "--size", "huge"])
