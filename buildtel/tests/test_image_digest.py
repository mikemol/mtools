# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `image_digest`: a digest is what the directory's query answered, else `absent`."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.buildtel import image_digest

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from mikemol.buildtel import proc

_DIGEST = "sha256:" + "ab" * 32


def _reply(**fields: object) -> str:
    """Render the query's JSON answer.

    Returns:
        the JSON text of `fields`.

    """
    return json.dumps(fields)


def _directory(root: Path) -> Path:
    """Plant the query script and interpreter file the way luthen-observability lays them out.

    Returns:
        the directory.

    """
    (root / "checks").mkdir(parents=True)
    (root / "checks" / "images_query.py").write_text("", encoding="utf-8")
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    return root


def _answering(status: int, out: str, calls: list[Sequence[str]]) -> proc.Runner:
    """Build a runner that records its argv and answers `(status, out, "")`.

    Returns:
        the fake runner.

    """

    def run(argv: Sequence[str]) -> tuple[int, str, str]:
        calls.append(list(argv))
        return status, out, ""

    return run


def test_digest_is_the_answered_digest_of_the_query_run_for_that_image(tmp_path: Path) -> None:
    """The query is `<directory .venv python> <directory query> <image>`, and its digest returns."""
    root = _directory(tmp_path)
    calls: list[Sequence[str]] = []
    reply = _reply(state="answered", digest=_DIGEST)
    got = image_digest.digest("buildbuddy-executor", _answering(0, reply, calls), root)
    assert got == _DIGEST
    assert calls == [
        [
            str(root / ".venv" / "bin" / "python"),
            str(root / "checks" / "images_query.py"),
            "buildbuddy-executor",
        ]
    ]


def test_digest_is_absent_without_the_directory_and_never_runs_anything(tmp_path: Path) -> None:
    """With no query script or no interpreter the answer is `absent` and no child is started."""
    calls: list[Sequence[str]] = []
    run = _answering(0, "{}", calls)
    assert image_digest.digest("paperkit-executor", run, tmp_path) == "absent"
    root = _directory(tmp_path / "half")
    (root / ".venv" / "bin" / "python").unlink()
    assert image_digest.digest("paperkit-executor", run, root) == "absent"
    (root / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    (root / "checks" / "images_query.py").unlink()
    assert image_digest.digest("paperkit-executor", run, root) == "absent"
    assert calls == []


@pytest.mark.parametrize(
    ("status", "out"),
    [
        (1, _reply(state="answered", digest=_DIGEST)),
        (0, "   \n"),
        (0, _reply(state="unknown", digest=_DIGEST)),
        (0, _reply(state="answered", digest="")),
        (0, _reply(state="answered")),
        (0, _reply(state="answered", digest=7)),
        (0, '["answered"]'),
    ],
)
def test_digest_is_absent_unless_the_query_succeeds_and_answers(
    tmp_path: Path, status: int, out: str
) -> None:
    """A failed query, silence, an unanswered state, or an empty/missing digest are `absent`."""
    root = _directory(tmp_path)
    run = _answering(status, out, [])
    assert image_digest.digest("paperkit-executor", run, root) == "absent"


def test_digest_refuses_an_image_it_does_not_know(tmp_path: Path) -> None:
    """An unknown name exits with a message naming it and the known ones, before any lookup."""
    calls: list[Sequence[str]] = []
    with pytest.raises(SystemExit) as caught:
        image_digest.digest("mystery", _answering(0, "{}", calls), _directory(tmp_path))
    message = str(caught.value)
    assert "'mystery'" in message
    assert "paperkit-executor, buildbuddy-executor" in message
    assert calls == []


def test_main_prints_the_digest_of_the_named_image(capsys: pytest.CaptureFixture[str]) -> None:
    """The first operand names the image; the digest is printed on its own line."""
    asked: list[str] = []

    def lookup(image: str) -> str:
        asked.append(image)
        return _DIGEST

    assert image_digest.main(["buildbuddy-executor"], lookup) == 0
    assert asked == ["buildbuddy-executor"]
    assert capsys.readouterr().out == _DIGEST + "\n"


def test_main_defaults_to_the_paperkit_executor(capsys: pytest.CaptureFixture[str]) -> None:
    """With no operand the image is `paperkit-executor`."""
    assert image_digest.main([], lambda image: image) == 0
    assert capsys.readouterr().out == "paperkit-executor\n"
