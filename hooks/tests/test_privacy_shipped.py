# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for judging the files a built sdist and wheel ship (W1148).

⚑ THE ARTIFACTS ARE BUILT HERE from fragments, so this file does not match its own rules. ⚑ THE
JUDGE IS THE REAL opa over the real policy. ⚑ THE CONTROLS ARE A CLEAN ARTIFACT AND A TAR LINK:
a clean one must exit 0, and a link member is skipped, never followed.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import tarfile
import zipfile
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.hooks import privacy_shipped

if TYPE_CHECKING:
    from pathlib import Path

_OPA = os.environ.get("OPA_BIN") or shutil.which("opa") or ""
pytestmark = pytest.mark.skipif(not _OPA, reason="no opa to judge with")
Row = dict[str, object]
_USAGE = 2
_HOME = "see /ho" + "me/someone/x\n"
_KEY = "KEY = 'AKIA" + "ABCDEFGHIJKLMNOP'\n"


def _sdist(tmp_path: Path, members: dict[str, str]) -> Path:
    path = tmp_path / "demo-0.1.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        for name, text in members.items():
            raw = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
        link = tarfile.TarInfo("demo-0.1/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "pkg/mod.py"
        archive.addfile(link)
    return path


def _wheel(tmp_path: Path, members: dict[str, str]) -> Path:
    path = tmp_path / "demo-0.1-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        for name, text in members.items():
            archive.writestr(name, text)
    return path


def _run(
    paths: list[Path], capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> tuple[int, list[Row]]:
    monkeypatch.setenv("OPA_BIN", _OPA)
    status = privacy_shipped.run([str(p) for p in paths])
    out = capsys.readouterr().out
    return status, [cast("Row", json.loads(line)) for line in out.splitlines()]


def test_findings_in_an_sdist_and_a_wheel_are_named_by_artifact_member_and_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A key in the sdist and a home path in the wheel; the deny makes the exit 1."""
    sdist = _sdist(tmp_path, {"demo-0.1/pkg/mod.py": "x = 1\n" + _KEY})
    wheel = _wheel(tmp_path, {"pkg/doc.py": _HOME})
    status, rows = _run([sdist, wheel], capsys, monkeypatch)
    found = {(r["kind"], r["rule"], r["path"], r["line"]) for r in rows if "rule" in r}
    assert found == {
        ("deny", "aws-access-key", "demo-0.1.tar.gz/demo-0.1/pkg/mod.py", _USAGE),
        ("withheld", "home-path", "demo-0.1-py3-none-any.whl/pkg/doc.py", 1),
    }
    assert status == 1


def test_a_clean_artifact_exits_zero_and_a_tar_link_is_skipped_not_followed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: one clean member and a link, so one file is judged and one is skipped."""
    sdist = _sdist(tmp_path, {"demo-0.1/pkg/mod.py": "x = 1\n"})
    status, rows = _run([sdist], capsys, monkeypatch)
    assert status == 0
    assert rows == [
        {"artifact": "demo-0.1.tar.gz", "deny": 0, "files": 1, "skipped": 1, "withheld": 0}
    ]


def test_the_output_never_carries_the_matched_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Neither the key nor the home directory name reaches standard output."""
    wheel = _wheel(tmp_path, {"pkg/a.py": _KEY + _HOME})
    monkeypatch.setenv("OPA_BIN", _OPA)
    privacy_shipped.run([str(wheel)])
    out = capsys.readouterr().out
    assert "ABCDEFGHIJKLMNOP" not in out
    assert "someone" not in out


def test_no_artifacts_or_no_judge_is_a_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """No arguments and no `OPA_BIN` each exit 2."""
    monkeypatch.setenv("OPA_BIN", "opa")
    assert privacy_shipped.run([]) == _USAGE
    monkeypatch.delenv("OPA_BIN", raising=False)
    assert privacy_shipped.run(["x.whl"]) == _USAGE
