# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The bazel timing profile is read from the invocation and summed by category (W1577)."""

import gzip
import json
from typing import cast

import pytest

from mikemol.buildtel import bazelprofile

_URI = "bytestream://bes.example:1985/blobs/abc/92220"
_ID = "5b22b85e-35ed-45e4-97ee-42c2b4888b33"
_TRACE: dict[str, object] = {
    "otherData": {"build_id": _ID},
    "traceEvents": [
        {"name": "thread_name", "ph": "M", "pid": 1, "tid": 0},
        {"cat": "build phase marker", "name": "x", "ph": "i", "ts": 0, "dur": 999},
        {"cat": "action processing", "name": "a", "ph": "X", "ts": 1, "dur": 400},
        {"cat": "action processing", "name": "b", "ph": "X", "ts": 2, "dur": 600},
        {"cat": "sandbox setup", "name": "c", "ph": "X", "ts": 3, "dur": 50},
        {"cat": "analysis", "name": "d", "ph": "X", "ts": 4},
    ],
}
_THOUSAND = 1000
_FIFTY = 50
_SPLIT = {"action processing": _THOUSAND, "sandbox setup": _FIFTY}


def _invocation() -> dict[str, object]:
    files = [{"name": "other.log", "uri": "x"}, {"name": bazelprofile.NAME, "uri": _URI}]
    return {"invocation": [{"event": {"buildToolLogs": {"log": files}}}]}


def _fetch(_invocation_id: str) -> object:
    return _invocation()


def _bare(_invocation_id: str) -> object:
    return {"invocation": []}


def _down(_invocation_id: str) -> object:
    msg = "HTTP 503"
    raise OSError(msg)


def _profile(_path: str) -> bytes:
    return gzip.compress(json.dumps(_TRACE).encode())


def _never(_path: str) -> bytes:
    pytest.fail("the profile must not be asked for")


def test_the_profile_address_is_found_anywhere_in_the_response() -> None:
    """Nested in lists and dicts; a file with another name does not count."""
    assert bazelprofile.profile_uri(_invocation()) == _URI
    assert bazelprofile.profile_uri({"invocation": [{"name": "other", "uri": "x"}]}) is None


def test_the_request_path_carries_the_file_name_the_uri_and_the_invocation() -> None:
    """The form the service answered 200 to: the uri keeps its colons and slashes."""
    path = bazelprofile.download_path(_URI, _ID)
    assert "filename=command.profile.gz&bytestream_url=bytestream://bes.example:1985" in path
    assert path.endswith(f"&invocation_id={_ID}")


def test_only_complete_events_with_a_duration_are_summed_by_category() -> None:
    """A metadata row, an instant and an event with no dur add nothing."""
    assert bazelprofile.totals(_TRACE) == _SPLIT
    assert bazelprofile.totals("not a trace") == {}
    assert bazelprofile.totals({"traceEvents": "nope"}) == {}


def test_the_split_fetches_the_invocation_then_the_gzipped_profile() -> None:
    """The profile bytes come from the path the address names."""
    asked: list[str] = []

    def get(path: str) -> bytes:
        asked.append(path)
        return _profile(path)

    assert bazelprofile.split(_ID, _fetch, get) == _SPLIT
    assert asked == [bazelprofile.download_path(_URI, _ID)]


def test_an_invocation_with_no_profile_is_none_and_the_command_says_so(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 3 and a sentence, never an empty table."""
    assert bazelprofile.split(_ID, _bare, _never) is None
    assert bazelprofile.main([_ID], _bare, _never) == bazelprofile.EXIT_NO_PROFILE
    assert "names no command.profile.gz" in capsys.readouterr().err


def test_the_command_prints_the_largest_category_first_and_names_the_unit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """One JSON line per category, thread microseconds, largest first."""
    assert bazelprofile.main([_ID], _fetch, _profile) == 0
    lines = capsys.readouterr().out.splitlines()
    rows = [cast("dict[str, object]", json.loads(line)) for line in lines]
    assert [r["category"] for r in rows] == ["action processing", "sandbox setup"]
    assert rows[0]["thread_micros"] == _THOUSAND
    assert rows[0]["invocation"] == _ID


def test_an_unreachable_service_and_a_bad_argument_are_not_a_split(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A transport error is exit 3 with its reason; a flag is a usage error."""
    assert bazelprofile.main([_ID], _down, _never) == bazelprofile.EXIT_NO_PROFILE
    assert "HTTP 503" in capsys.readouterr().err
    assert bazelprofile.main(["--x"]) == bazelprofile.EXIT_USAGE
