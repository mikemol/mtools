# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.hooks.refusal_log`: substrate's `ratchet_log` arms, and its letter's §3.1.

⚑ NO NETWORK IS TOUCHED. `curl` is a script this suite writes under `tmp_path`, reached by
patching the module's `which`; it records its stdin and argv, and exits as the arm needs.
"""

from __future__ import annotations

import json
import stat
from typing import TYPE_CHECKING, cast

from mikemol.hooks import refusal_log

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_DEST = "http://logs.invalid/insert/jsonline?_stream_fields=tool,reason"
_CURL_FAILED = 7


def _fake_curl(tmp_path: Path, code: int) -> Path:
    """Write a `curl` that records its stdin and argv beside itself, then exits `code`.

    Returns:
        the script's path.

    """
    script = tmp_path / "curl"
    script.write_text(
        "#!/bin/sh\n"
        f'cat > "{tmp_path}/stdin"\n'
        f'printf "%s\\n" "$@" > "{tmp_path}/argv"\n'
        "echo 'refused' >&2\n"
        f"exit {code}\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def _curl_at(monkeypatch: pytest.MonkeyPatch, curl: Path | None) -> None:
    """Make the module resolve `curl` to `curl` (or to nothing)."""

    def which(_name: str) -> str | None:
        return None if curl is None else str(curl)

    monkeypatch.setattr(refusal_log, "which", which)


def _event(path: Path) -> dict[str, object]:
    """Read the event the fake curl received.

    ⚑ `json.loads` RETURNS `Any`; the cast states the shape at the one place it enters.

    Returns:
        the event's fields.

    """
    return cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))


def test_a_none_label_is_unknown_not_the_string_none() -> None:
    """`stream_tool(None)` is "unknown": `str(None)` is the truthy string "None"."""
    assert refusal_log.stream_tool(None) == refusal_log.UNKNOWN_TOOL
    assert refusal_log.stream_tool("   ") == refusal_log.UNKNOWN_TOOL


def test_a_label_is_bounded_to_its_tools_basename() -> None:
    """An invocation label keeps only its first word's basename: the stream stays bounded."""
    assert refusal_log.stream_tool("/usr/bin/bibstruct --add KEY") == "bibstruct"


def test_no_destination_is_reported_and_starts_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no destination, NOT emitted is reported and curl is never started.

    ⚑⚑ THE LETTER'S §3.1: substrate's copy fell back to a written-down address, which went stale
    once and swallowed every event silently. There is nothing to fall back to here.
    """
    _curl_at(monkeypatch, _fake_curl(tmp_path, 0))
    got = refusal_log.log_fallthrough("gate", "unknown-flag", "--queit", destination=None)
    assert got == refusal_log.Emission(emitted=False, why=refusal_log.NO_DESTINATION)
    assert not (tmp_path / "argv").exists()


def test_a_destination_emits_one_jsonline_to_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive control: with a destination, curl gets it as a word and the event on stdin."""
    _curl_at(monkeypatch, _fake_curl(tmp_path, 0))
    refusal = refusal_log.Refusal(known=("--quiet", "--list"), argv=("gate", "--queit"))
    got = refusal_log.log_fallthrough(
        "gate --queit", "unknown-flag", "--queit", refusal, destination=_DEST
    )
    assert got == refusal_log.Emission(emitted=True)
    assert _DEST in (tmp_path / "argv").read_text(encoding="utf-8").splitlines()
    event = _event(tmp_path / "stdin")
    assert event["tool"] == "gate"
    assert event["known"] == "--list --quiet"
    assert event["argv"] == "gate --queit"


def test_a_failing_curl_is_reported_with_its_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dead store is reported as NOT emitted with curl's code, never mistaken for a quiet one."""
    _curl_at(monkeypatch, _fake_curl(tmp_path, _CURL_FAILED))
    got = refusal_log.log_fallthrough("gate", "unknown-flag", destination=_DEST)
    assert not got.emitted
    assert got.why.startswith(f"curl exit {_CURL_FAILED}")


def test_no_curl_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no curl on PATH, NOT emitted is reported, naming why."""
    _curl_at(monkeypatch, None)
    got = refusal_log.log_fallthrough("gate", "unknown-flag", destination=_DEST)
    assert got == refusal_log.Emission(emitted=False, why=refusal_log.NO_CURL)


def test_junk_arguments_never_raise(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Junk in every slot still emits: a gate that cannot log must still gate."""
    _curl_at(monkeypatch, _fake_curl(tmp_path, 0))
    junk = refusal_log.Refusal(known=None, argv=None)
    assert refusal_log.log_fallthrough(None, None, "", junk, destination=_DEST).emitted
