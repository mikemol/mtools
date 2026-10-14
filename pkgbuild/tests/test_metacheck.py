# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the metadata check names what PyPI would refuse and passes what it would take.

W1187. ⚑ THE CLEAN ARTIFACT IS THE POSITIVE CONTROL: every refusal below is the same metadata with
ONE property changed, so each problem is shown to come from that property and not from the fixture.
⚑ THE ARTIFACTS ARE REAL ZIP AND TAR FILES written to `tmp_path`, so the reader that finds
`.dist-info/METADATA` and `PKG-INFO` is the one under test, not a stub of it.
"""

from __future__ import annotations

import io
import json
import tarfile
import zipfile
from typing import TYPE_CHECKING, cast

from mikemol.pkgbuild import metacheck, wheel

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_GOOD = {
    "Metadata-Version": "2.4",
    "Name": "mikemol-demo",
    "Version": "0.0.1187",
    "Summary": "a demonstration",
    "Description-Content-Type": "text/markdown",
    "Requires-Python": ">=3.13",
    "License-Expression": "Apache-2.0",
}
_BODY = "# demo\n\nreads well\n"
_TWO = 2


def _metadata(**changes: str | None) -> str:
    """Build core metadata text from the clean fields with some changed or removed (None).

    Returns:
        the metadata text, headers then a blank line then the body.

    """
    fields = {**_GOOD, **changes}
    head = "".join(f"{k}: {v}\n" for k, v in fields.items() if v is not None)
    return f"{head}\n{_BODY}"


def _wheel(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "mikemol_demo-0.0.1187-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mikemol_demo-0.0.1187.dist-info/METADATA", text)
    return path


def _sdist(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "mikemol_demo-0.0.1187.tar.gz"
    data = text.encode("utf-8")
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("mikemol_demo-0.0.1187/PKG-INFO")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    return path


def _problems(result: dict[str, object]) -> list[str]:
    """Read a verdict's problems as strings.

    Returns:
        the problems, empty when there are none.

    """
    value = result["problems"]
    return [str(item) for item in value] if isinstance(value, list) else []


def test_a_clean_wheel_and_a_clean_sdist_both_pass(tmp_path: Path) -> None:
    """The positive control: the same good metadata in each container has no problems."""
    for made in (_wheel(tmp_path, _metadata()), _sdist(tmp_path, _metadata())):
        result = metacheck.verdict(made)
        assert result["ok"] is True, result
        assert _problems(result) == []
        assert (result["name"], result["version"]) == ("mikemol-demo", "0.0.1187")


def test_each_single_change_is_refused_for_that_property_alone(tmp_path: Path) -> None:
    """One property changed per row: exactly one problem, and it names the property."""
    rows = {
        "local part": (_metadata(Version="0.0.1+g0acbc18"), "local part"),
        "not public": (_metadata(Version="v1"), "public PEP 440"),
        "bad name": (_metadata(Name="-nope"), "valid project name"),
        "no summary": (_metadata(Summary=None), "Summary is missing"),
        "no content type": (_metadata(**{"Description-Content-Type": None}), "Content-Type"),
        "wrong content type": (
            _metadata(**{"Description-Content-Type": "text/html"}),
            "Content-Type",
        ),
        "no python": (_metadata(**{"Requires-Python": None}), "Requires-Python is missing"),
        "no license": (_metadata(**{"License-Expression": None}), "no license"),
        "old metadata": (_metadata(**{"Metadata-Version": "2.0"}), "older than 2.1"),
    }
    for label, (text, wanted) in rows.items():
        result = metacheck.verdict(_wheel(tmp_path, text))
        problems = _problems(result)
        assert result["ok"] is False, label
        assert len(problems) == 1, (label, problems)
        assert wanted in problems[0], (label, problems)


def test_a_missing_long_description_is_refused(tmp_path: Path) -> None:
    """Headers only, no body: the description is missing even though the type is declared."""
    head = "".join(f"{k}: {v}\n" for k, v in _GOOD.items())
    result = metacheck.verdict(_wheel(tmp_path, head))
    assert result["ok"] is False
    assert "long description is missing" in " ".join(_problems(result))


def test_a_license_file_alone_satisfies_the_license_check(tmp_path: Path) -> None:
    """`License-File` stands in for the expression: the license rule is any of the three."""
    text = _metadata(**{"License-Expression": None, "License-File": "LICENSE"})
    assert metacheck.verdict(_wheel(tmp_path, text))["ok"] is True


def test_an_unreadable_artifact_is_one_problem_not_an_exception(tmp_path: Path) -> None:
    """A truncated zip, a wrong extension and a missing file each say why, and none raises."""
    broken = tmp_path / "broken-0.0.1-py3-none-any.whl"
    broken.write_bytes(b"not a zip")
    odd = tmp_path / "thing.txt"
    odd.write_text("x", encoding="utf-8")
    for path in (broken, odd, tmp_path / "absent.whl"):
        result = metacheck.verdict(path)
        assert result["ok"] is False
        assert len(_problems(result)) == 1


def test_the_command_prints_one_json_line_per_artifact_and_exits_by_the_worst(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two artifacts, one bad: two JSON lines in order and exit 1; the good one alone is 0."""
    good = _wheel(tmp_path, _metadata())
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    bad = _wheel(bad_dir, _metadata(Version="0.0.1+local"))
    assert wheel.main(["check", str(good), str(bad)]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == _TWO
    first = cast("dict[str, object]", json.loads(lines[0]))
    second = cast("dict[str, object]", json.loads(lines[1]))
    assert (first["ok"], second["ok"]) == (True, False)
    assert wheel.main(["check", str(good)]) == 0
