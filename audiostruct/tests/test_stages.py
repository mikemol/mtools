# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the stage runner: one model resident at a time, and the token never escapes.

Every model is a fake that logs what it is asked to do. No torch, no whisperx, no audio.
"""

from __future__ import annotations

import gc
import json
import traceback
import weakref
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.audiostruct.records import Segment, Unplaced
from mikemol.audiostruct.stages import STAGES, Pipeline, StageError, records, run, run_stage

if TYPE_CHECKING:
    from collections.abc import Callable

_PLANTED = "hf_planted_value_that_must_not_escape"


class _Model:
    """A fake model: every call is logged, and its result is a segments list per clip."""

    def __init__(self, name: str, log: list[str], fail: str | None = None) -> None:
        self.name, self.log, self.fail = name, log, fail

    def _step(self, verb: str, clip: object) -> object:
        """Log one call and answer it.

        Returns:
            a result with one good and one untimed segment.

        Raises:
            ValueError: if this clip is the one set to fail.

        """
        self.log.append(f"{verb} {clip}")
        if clip == self.fail:
            msg = f"{verb} failed on {clip} with {_PLANTED}"
            raise ValueError(msg)
        return {"segments": [{"start": 0.0, "end": 1.0, "text": f"{clip}"}, {"text": "late"}]}

    def transcribe(self, audio: object) -> object:
        """Fake transcription.

        Returns:
            the fake result.

        """
        return self._step("transcribe", audio)

    def align(self, segments: list[object], audio: object) -> object:
        """Fake alignment; it sees the segments the previous stage produced.

        Returns:
            the fake result.

        """
        assert len(segments) == len(("good", "untimed"))
        return self._step("align", audio)

    def diarize(self, audio: object, aligned: object) -> object:
        """Fake diarization.

        Returns:
            the fake result.

        """
        assert isinstance(aligned, dict)
        return self._step("diarize", audio)


class _Harness:
    """A Pipeline of fakes, with a log and a check at every release that the last model is gone."""

    def __init__(self, fail_stage: str = "", fail_clip: str | None = None) -> None:
        self.log: list[str] = []
        self.alive_at_release: list[bool] = []
        self._models: list[weakref.ref[_Model]] = []
        self._fail_stage, self._fail_clip = fail_stage, fail_clip

    def _load(self, name: str) -> _Model:
        """Load one stage's model, keeping only a weak reference to it.

        Returns:
            the model.

        """
        self.log.append(f"load {name}")
        fail = self._fail_clip if name == self._fail_stage else None
        model = _Model(name, self.log, fail)
        self._models.append(weakref.ref(model))
        return model

    def _diarizer(self, token: str) -> Callable[[object, object], object]:
        """Build the diarizer; the token is checked, never logged.

        Returns:
            the model's bound `diarize`.

        """
        assert token == _PLANTED
        return self._load("diarizer").diarize

    def _token(self) -> str:
        """Read the planted token.

        Returns:
            it.

        """
        self.log.append("token")
        return _PLANTED

    def _release(self) -> None:
        """Record the release, and whether any model loaded so far is still referenced."""
        gc.collect()
        self.log.append("release")
        self.alive_at_release.append(any(ref() is not None for ref in self._models))

    def pipeline(self) -> Pipeline:
        """Assemble the fakes.

        Returns:
            the Pipeline.

        """
        return Pipeline(
            load_audio=lambda path: f"clip:{path}",
            transcriber=lambda: self._load("transcriber").transcribe,
            aligner=lambda: self._load("aligner").align,
            diarizer=self._diarizer,
            token=self._token,
            release=self._release,
        )


_SOURCES = [("call a", "a.wav"), ("call b", "b.wav")]


def test_stages_run_in_order_one_model_at_a_time() -> None:
    """Each stage loads, runs over every file, and is released before the next stage loads.

    ⚑ The baseline's measured shape: holding all three models at once ran out of GPU memory.
    The token is read only once the diarize stage begins.
    """
    harness = _Harness()
    run(harness.pipeline(), _SOURCES)
    assert harness.log == [
        "load transcriber",
        "transcribe clip:a.wav",
        "transcribe clip:b.wav",
        "release",
        "load aligner",
        "align clip:a.wav",
        "align clip:b.wav",
        "release",
        "token",
        "load diarizer",
        "diarize clip:a.wav",
        "diarize clip:b.wav",
        "release",
    ]


def test_release_follows_the_drop_of_the_last_reference() -> None:
    """At every release no model is still referenced, so the memory release frees something.

    ⚑ A release called while the runner still holds its model frees nothing on the GPU.
    """
    harness = _Harness()
    run(harness.pipeline(), _SOURCES)
    assert harness.alive_at_release == [False, False, False]


def test_every_source_comes_back_as_records_in_order() -> None:
    """Each label returns with one record per diarized segment, the untimed one Unplaced."""
    labelled = run(_Harness().pipeline(), _SOURCES)
    assert [label for label, _ in labelled] == ["call a", "call b"]
    for label, found in labelled:
        assert [type(r) for r in found] == [Segment, Unplaced]
        assert {r.source for r in found} == {label}


@pytest.mark.parametrize(
    ("stage", "clip", "message", "last"),
    [
        ("transcriber", "clip:b.wav", "transcribe: call b: ValueError", "transcribe clip:b.wav"),
        ("aligner", "clip:a.wav", "align: call a: ValueError", "align clip:a.wav"),
        ("diarizer", "clip:b.wav", "diarize: call b: ValueError", "diarize clip:b.wav"),
    ],
)
def test_failing_step_names_stage_and_label_and_stops(
    stage: str, clip: str, message: str, last: str
) -> None:
    """A failing step is a StageError naming stage, label and type; nothing runs after it."""
    harness = _Harness(stage, clip)
    with pytest.raises(StageError) as caught:
        run(harness.pipeline(), _SOURCES)
    assert str(caught.value) == message
    assert harness.log[-1] == last


def test_planted_token_reaches_no_error_text() -> None:
    """A step whose message embeds the token raises a StageError that prints nothing of it.

    ⚑ Raised `from None`: the original is neither `__cause__` nor printed context, so a traceback
    of the StageError cannot show the library's message.
    """
    harness = _Harness("diarizer", "clip:a.wav")
    with pytest.raises(StageError) as caught:
        run(harness.pipeline(), _SOURCES)
    printed = "".join(traceback.format_exception(caught.value))
    assert _PLANTED not in printed
    assert _PLANTED not in repr(caught.value)
    assert caught.value.__cause__ is None


def test_model_that_fails_to_load_is_named_for_every_source() -> None:
    """A factory that fails is a StageError for every source, and the token is not in it."""

    def refuse(token: str) -> Callable[[object, object], object]:
        msg = f"401 for {token}"
        raise PermissionError(msg)

    pipeline = _Harness().pipeline()
    broken = Pipeline(
        pipeline.load_audio,
        pipeline.transcriber,
        pipeline.aligner,
        refuse,
        pipeline.token,
        pipeline.release,
    )
    with pytest.raises(StageError) as caught:
        run(broken, _SOURCES)
    assert str(caught.value) == "diarize: every source: PermissionError"
    assert _PLANTED not in "".join(traceback.format_exception(caught.value))


def test_result_without_segments_is_a_stage_error() -> None:
    """A stage result that is not an object with a segments list fails the next reader by label."""
    pipeline = _Harness().pipeline()

    class _Empty:
        def __init__(self) -> None:
            self.key = "text"

        def transcribe(self, audio: object) -> object:
            """Return no segments.

            Returns:
                an object with no segments list.

            """
            return {self.key: f"{audio}"}

    broken = Pipeline(
        pipeline.load_audio,
        lambda: _Empty().transcribe,
        pipeline.aligner,
        pipeline.diarizer,
        pipeline.token,
        pipeline.release,
    )
    with pytest.raises(StageError) as caught:
        run(broken, _SOURCES)
    assert str(caught.value) == "align: call a: TypeError"


def test_stages_chained_through_json_equal_the_in_process_run() -> None:
    """Each stage in its own call, its results round-tripped through JSON, gives run()'s records.

    ⚑ This is what lets the CLI run each stage in a process of its own under its own lease: the
    handoff between stages is plain data, and nothing survives in memory from one to the next.
    """
    expected = run(_Harness().pipeline(), _SOURCES)
    harness = _Harness()
    results: list[object] = []
    for stage in STAGES:
        handoff = json.dumps(run_stage(stage, harness.pipeline(), _SOURCES, results))
        results = cast("list[object]", json.loads(handoff))
    assert records(_SOURCES, results) == expected
    assert harness.alive_at_release == [False, False, False]


@pytest.mark.parametrize(
    ("stage", "previous"),
    [
        ("transcribe", [{"segments": []}, {"segments": []}]),
        ("align", []),
        ("diarize", []),
        ("summarize", []),
    ],
)
def test_run_stage_refuses_results_that_do_not_fit_the_stage(
    stage: str, previous: list[object]
) -> None:
    """Transcribe takes no previous results, the others need them, and no other stage exists."""
    harness = _Harness()
    with pytest.raises(ValueError, match=stage):
        run_stage(stage, harness.pipeline(), _SOURCES, previous)
    assert harness.log == []
