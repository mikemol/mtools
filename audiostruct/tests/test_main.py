# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-audio`: parent and children, end to end, over fakes and real files.

The subprocess runner is a fake that runs each child as `main(...)` in this process, and the
pipeline factory is a fake. So the handoff files, the parsing and the rendering are all real, and
no model, GPU or membudget is touched.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.audiostruct.main import main, parse_sources
from mikemol.audiostruct.stages import Pipeline

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from mikemol.audiostruct.whisperx_site import Settings

_SEGMENT: dict[str, object] = {"start": 0.0, "end": 1.0, "text": " hello", "speaker": "SPEAKER_00"}
# membudget's exit code when admission refuses a lease.
_REFUSED = 3
# main's exit code for bad sources, argparse's usage code.
_USAGE = 2
_BATCH = 4
# Any executable stands in for membudget: the fake runner never runs it.
_MEMBUDGET = sys.executable


def _result(_clip: object, *_rest: object) -> dict[str, object]:
    return {"segments": [dict(_SEGMENT)]}


def _fake(settings: Settings) -> Pipeline:
    """Build a pipeline whose every stage answers one fixed segment, checking the settings arrived.

    Returns:
        the fake pipeline.

    """
    assert settings.batch_size == _BATCH
    return Pipeline(
        load_audio=lambda path: f"clip:{path}",
        transcriber=lambda: _result,
        aligner=lambda: _result,
        diarizer=lambda _token: _result,
        token=lambda: "hf_unused",
        release=lambda: None,
    )


def _argv(tmp_path: Path, *sources: str, membudget: str = _MEMBUDGET) -> list[str]:
    return [
        "--membudget",
        membudget,
        "--ledger",
        str(tmp_path / "gpu.ledger"),
        "--workdir",
        str(tmp_path / "work"),
        "--out",
        str(tmp_path / "out"),
        "--model",
        "large-v3",
        "--device",
        "cuda",
        "--compute-type",
        "float16",
        "--batch-size",
        "4",
        "--language",
        "en",
        "--token-file",
        str(tmp_path / "token"),
        *sources,
    ]


def test_the_parent_runs_three_children_and_writes_one_transcript_per_label(
    tmp_path: Path,
) -> None:
    """Each stage runs as a child under membudget; the handoffs chain; each label gets its .md."""
    (tmp_path / "work").mkdir()
    held: list[str] = []

    def run(argv: list[str], _env: Mapping[str, str]) -> int:
        assert argv[:3] == [_MEMBUDGET, "hold", "1"]
        held.append(argv[3])
        return main(argv[6:], make=_fake)

    assert main(_argv(tmp_path, "call a=a.wav", "call b=b.wav"), run=run, make=_fake) == 0
    assert held == ["audiostruct-transcribe", "audiostruct-align", "audiostruct-diarize"]
    assert sorted(p.name for p in (tmp_path / "work").iterdir()) == [
        "align.json",
        "diarize.json",
        "transcribe.json",
    ]
    for label in ("call a", "call b"):
        text = (tmp_path / "out" / f"{label}.md").read_text(encoding="utf-8")
        assert text.startswith(f"# Transcript: {label}\n")
        assert "SPEAKER_00" in text
        assert "hello" in text


def test_a_failing_stage_writes_no_transcript(tmp_path: Path) -> None:
    """A refused lease returns membudget's code, and the parent renders nothing."""
    (tmp_path / "work").mkdir()

    def run(argv: list[str], _env: Mapping[str, str]) -> int:
        return _REFUSED if argv[3] == "audiostruct-align" else main(argv[6:], make=_fake)

    assert main(_argv(tmp_path, "call a=a.wav"), run=run, make=_fake) == _REFUSED
    assert not (tmp_path / "out").exists()


def test_bad_sources_exit_2_before_any_stage(tmp_path: Path) -> None:
    """A source with no label, or a label given twice, stops the run before anything starts."""
    ran: list[list[str]] = []

    def run(argv: list[str], _env: Mapping[str, str]) -> int:
        ran.append(argv)
        return 0

    assert main(_argv(tmp_path, "a.wav"), run=run, make=_fake) == _USAGE
    assert main(_argv(tmp_path, "x=a.wav", "x=b.wav"), run=run, make=_fake) == _USAGE
    assert ran == []


def test_a_membudget_that_cannot_run_is_refused_before_any_stage(tmp_path: Path) -> None:
    """A missing or non-executable membudget exits 2 with no stage started.

    ⚑ Measured on the real GPU: a bare `mikemol-membudget` on no PATH died as exit 127 inside
    the first stage. The parent now refuses up front, naming the path it was given.
    """
    ran: list[list[str]] = []

    def run(argv: list[str], _env: Mapping[str, str]) -> int:
        ran.append(argv)
        return 0

    absent = str(tmp_path / "no-such-membudget")
    assert main(_argv(tmp_path, "a=a.wav", membudget=absent), run=run, make=_fake) == _USAGE
    assert ran == []


def test_sources_keep_their_order_and_their_labels() -> None:
    """LABEL=PATH pairs come back in order, a path's own '=' kept."""
    assert parse_sources(["b=2.wav", "a=x=y.wav"]) == [("b", "2.wav"), ("a", "x=y.wav")]
