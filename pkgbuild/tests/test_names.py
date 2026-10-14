# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `names` asks the index about each dist's normalized name and reports what it said.

W1149. ⚑ THE INDEX IS A FAKE with a status per name, so `free`, `taken` and `error` are each reached
and the exit is judged by the worst. ⚑ THE REAL REQUEST FUNCTION IS EXERCISED against a local HTTP
server, so `http_status` is not an untested seam. ⚑ A SYMLINKED DIRECTORY AND A NAMELESS PYPROJECT
ARE THE CONTROLS: the first is not a dist, the second is an error row and not a crash.
"""

from __future__ import annotations

import http.server
import json
import threading
from typing import TYPE_CHECKING, cast

from mikemol.pkgbuild import names

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

Row = dict[str, object]
_USAGE = 2
_OTHER = 418
_SERVED = {"/pypi/free-one/json": 404, "/pypi/taken-one/json": 200}


class _Index(http.server.BaseHTTPRequestHandler):
    """Answer a GET with the status the table names for the path."""

    def do_GET(self) -> None:
        self.send_response(_SERVED.get(self.path, _OTHER))
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        """Say nothing."""


def _dist(root: Path, folder: str, name: str | None) -> None:
    (root / folder).mkdir()
    body = f'[project]\nname = "{name}"\n' if name is not None else "[build-system]\n"
    (root / folder / "pyproject.toml").write_text(body, encoding="utf-8")


def _fake(statuses: dict[str, int], asked: list[str]) -> names.Fetch:
    def fetch(url: str) -> int:
        asked.append(url)
        if url.endswith("/boom/json"):
            msg = "no route"
            raise OSError(msg)
        return statuses.get(url.rsplit("/", 2)[1], 404)

    return fetch


def _rows(capsys: pytest.CaptureFixture[str]) -> dict[str, Row]:
    lines = capsys.readouterr().out.splitlines()
    rows = [cast("Row", json.loads(line)) for line in lines]
    return {str(r["dist"]): r for r in rows}


def test_a_name_is_normalized_like_an_index_before_it_is_asked() -> None:
    """Runs of `-`, `_` and `.` become one dash and case is dropped (PEP 503)."""
    assert names.normalized("Mikemol_Hooks..Extra--Bits") == "mikemol-hooks-extra-bits"


def test_each_dist_is_asked_by_its_normalized_name_and_the_worst_state_sets_the_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """free, taken and an error row; one 404-free dist alone exits 0."""
    _dist(tmp_path, "a", "Free_One")
    _dist(tmp_path, "b", "taken-one")
    _dist(tmp_path, "c", "boom")
    asked: list[str] = []
    fetch = _fake({"taken-one": 200}, asked)
    assert names.run([str(tmp_path), "--index", "https://idx.example/pypi/"], fetch) == 1
    rows = _rows(capsys)
    assert rows["a"]["state"] == "free"
    assert rows["b"]["state"] == "taken"
    assert str(rows["c"]["state"]).startswith("error: OSError")
    assert asked[0] == "https://idx.example/pypi/free-one/json"
    only = tmp_path / "only"
    only.mkdir()
    _dist(only, "x", "Free_One")
    assert names.run([str(only)], fetch) == 0


def test_an_unexpected_status_is_an_error_not_a_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A 503 is neither free nor taken: it is reported with its status and fails the run."""
    _dist(tmp_path, "a", "flaky")
    assert names.run([str(tmp_path)], _fake({"flaky": 503}, [])) == 1
    assert _rows(capsys)["a"]["state"] == "error: HTTP 503"


def test_a_symlinked_directory_is_not_a_dist_and_a_nameless_pyproject_is_an_error_row(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The controls: `link` is never asked, and `bare` has no name to ask for."""
    root = tmp_path / "root"
    root.mkdir()
    _dist(root, "real", "free-one")
    _dist(root, "bare", None)
    (root / "link").symlink_to(root / "real", target_is_directory=True)
    asked: list[str] = []
    assert names.run([str(root)], _fake({}, asked)) == 1
    rows = _rows(capsys)
    assert sorted(rows) == ["bare", "real"]
    assert rows["bare"]["state"] == "error: no [project].name"
    assert len(asked) == 1


def test_the_request_function_reads_the_status_from_a_real_server() -> None:
    """`http_status` returns 404 and 200 as served, and a plain `http` index needs no TLS."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Index)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}/pypi"
        assert names.http_status(f"{base}/free-one/json") == names.FREE
        assert names.http_status(f"{base}/taken-one/json") == names.TAKEN
        assert names.http_status(f"{base}/other/json") == _OTHER
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_a_missing_root_or_a_dangling_index_flag_is_a_usage_error(tmp_path: Path) -> None:
    """No root, a root that is no directory, and `--index` with nothing after it exit 2."""
    assert names.run([]) == _USAGE
    assert names.run([str(tmp_path / "absent")]) == _USAGE
    assert names.run([str(tmp_path), "--index"]) == _USAGE
