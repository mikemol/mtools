# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `logs_push`: a hook log's findings reach the sink, tagged, and nothing else."""

from __future__ import annotations

import http.server
import json
import socket
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from mikemol.buildtel import logs_push

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_USAGE_EXIT = 2
_SERVER_ERROR = 500
_REFUSED_PORT = 1
_LOG_LINES = (
    "chatter that matches nothing",
    "FAIL: //pkg:target (Exit 1)",
    "ERROR: //pkg:other (Exit 137)",
    "paperkit-gate: check UNRESOLVABLE for [@claim-1.a]: reason",
    "coherence: GROUNDING 2 of 9 rests-on edges undischarged",
    "  [@left] rests-on [@right]",
    "java.lang.OutOfMemoryError: Java heap space",
    "[pre-commit] ok: ruff",
    "[pre-commit] FAIL: mypy",
    "input dependency //x:y was modified during execution",
)
_LOG = "\n".join(_LOG_LINES)
_KINDS = [
    ("bazel_target_fail", ("//pkg:target", "1"), 2),
    ("bazel_target_fail", ("//pkg:other", "137"), 3),
    ("gate_unresolvable", ("claim-1.a", "reason"), 4),
    ("coherence_grounding", ("2", "9"), 5),
    ("coherence_miss", ("left", "right"), 6),
    ("jvm_oom", ("java.lang.OutOfMemoryError: Java heap space",), 7),
    ("hook_step", ("ok", "ruff"), 8),
    ("hook_step", ("FAIL", "mypy"), 9),
    ("sandbox_invalidated", ("//x:y",), 10),
]


@dataclass
class _Sink:
    """A local log store: what it was sent, and what status it answers."""

    port: int = 0
    status: int = 200
    seen: list[tuple[str, str, str]] = field(default_factory=list)


@pytest.fixture()
def sink() -> Iterator[_Sink]:
    """Serve one local HTTP endpoint that records `(path, content type, body)` of each POST.

    Yields:
        the sink handle, its `port` filled in.

    """
    state = _Sink()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            state.seen.append((self.path, self.headers.get("Content-Type", ""), body))
            self.send_response(state.status)
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()


def _lines(body: str) -> list[dict[str, object]]:
    """Parse a JSON-lines body.

    Returns:
        one dict per line.

    """
    rows: list[dict[str, object]] = []
    for text in body.splitlines():
        rec: object = json.loads(text)
        assert isinstance(rec, dict)
        rows.append({str(k): v for k, v in rec.items()})
    return rows


def test_findings_names_each_kind_with_its_fields_and_log_line(tmp_path: Path) -> None:
    """Every vocabulary pattern is recognised, in order, with its groups and 1-based line."""
    log = tmp_path / "hook.log"
    log.write_text(_LOG, encoding="utf-8")
    got = [(f.kind, f.fields, f.line) for f in logs_push.findings(log)]
    assert got == _KINDS


def test_findings_drops_unrecognised_lines_and_clips_the_message(tmp_path: Path) -> None:
    """Chatter is not forwarded; a recognised line's `_msg` is capped at MSG_MAX characters."""
    log = tmp_path / "hook.log"
    long = "java.lang.OutOfMemoryError: " + "x" * (logs_push.MSG_MAX + 50)
    log.write_text(f"noise\n{long}   \n", encoding="utf-8")
    (only,) = logs_push.findings(log)
    assert (only.kind, only.line, len(only.msg)) == ("jvm_oom", 2, logs_push.MSG_MAX)


def test_findings_of_a_missing_log_is_empty(tmp_path: Path) -> None:
    """An unreadable log yields no findings rather than raising."""
    assert logs_push.findings(tmp_path / "absent.log") == []


def test_a_finding_renders_the_common_fields_then_its_own() -> None:
    """The record carries the run's common fields plus kind, fields, line and `_msg`."""
    finding = logs_push.Finding("jvm_oom", ("a", "b"), 3, "msg")
    assert finding.record({"run": "r1"}) == {
        "run": "r1",
        "kind": "jvm_oom",
        "fields": ["a", "b"],
        "line": 3,
        "_msg": "msg",
    }


def test_push_posts_json_lines_with_the_stream_content_type(sink: _Sink) -> None:
    """One POST carries one JSON line per finding, to the URL's path and query."""
    events = [
        logs_push.Finding("jvm_oom", ("x",), 1, "m1"),
        logs_push.Finding("hook_step", (), 2, "m2"),
    ]
    url = f"http://127.0.0.1:{sink.port}/insert/jsonline?_stream_fields=run"
    ok, detail = logs_push.push(events, url, {"run": "r1"})
    assert (ok, detail) == (True, "200 (2 events)")
    ((path, content_type, body),) = sink.seen
    assert path == "/insert/jsonline?_stream_fields=run"
    assert content_type == "application/stream+json"
    assert [rec["_msg"] for rec in _lines(body)] == ["m1", "m2"]


def test_push_with_no_findings_sends_nothing(sink: _Sink) -> None:
    """An empty list is a success that never reaches the network."""
    ok, detail = logs_push.push([], f"http://127.0.0.1:{sink.port}/", {})
    assert (ok, detail) == (True, "no findings to push")
    assert sink.seen == []


def test_push_reports_a_non_2xx_answer_as_not_ok(sink: _Sink) -> None:
    """A 500 is `(False, '500 (1 events)')`."""
    sink.status = _SERVER_ERROR
    ok, detail = logs_push.push(
        [logs_push.Finding("jvm_oom", (), 1, "m")], f"http://127.0.0.1:{sink.port}", {}
    )
    assert (ok, detail) == (False, "500 (1 events)")
    assert sink.seen[0][0] == "/"


@pytest.mark.parametrize("url", ["ftp://host/x", "http:///nohost", "not a url"])
def test_push_refuses_an_unusable_sink_url(url: str) -> None:
    """A non-http(s) scheme or a missing host is refused with the URL in the detail."""
    ok, detail = logs_push.push([logs_push.Finding("jvm_oom", (), 1, "m")], url, {})
    assert (ok, detail) == (False, f"unusable sink URL: {url!r}")


def test_push_returns_the_error_instead_of_raising_when_the_sink_is_down() -> None:
    """A refused connection is `(False, 'ConnectionRefusedError: ...')`, never an exception."""
    ok, detail = logs_push.push(
        [logs_push.Finding("jvm_oom", (), 1, "m")], f"http://127.0.0.1:{_REFUSED_PORT}/", {}
    )
    assert ok is False
    assert detail.startswith("ConnectionRefusedError")


def test_parse_reads_the_log_and_the_flag_value_pairs() -> None:
    """The first operand is the log; the rest are flag/value pairs."""
    args = logs_push.parse(["hook.log", "--rc", "1", "--seconds", "12"])
    assert args is not None
    assert (str(args.log), args.opts) == ("hook.log", {"--rc": "1", "--seconds": "12"})


@pytest.mark.parametrize(
    "argv",
    [[], ["--rc"], ["log", "--rc"], ["log", "--bogus", "1"], ["log", "--rc", "1", "--rc", "2"]],
)
def test_parse_refuses_anything_but_the_documented_shape(argv: list[str]) -> None:
    """No log, an odd tail, an unknown flag or a repeated flag is `None`."""
    assert logs_push.parse(argv) is None


def test_main_pushes_a_red_runs_findings_with_run_identity(
    sink: _Sink, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failed run's findings arrive tagged red, with rc, seconds, host and the given run id."""
    log = tmp_path / "hook.log"
    log.write_text(_LOG, encoding="utf-8")
    argv = [str(log), "--rc", "1", "--seconds", "42", "--run-id", "run-7"]
    argv += ["--url", f"http://127.0.0.1:{sink.port}/in"]
    assert logs_push.main(argv) == 0
    rows = _lines(sink.seen[0][2])
    assert len(rows) == len(_KINDS)
    assert rows[0] == {
        "service": "paperkit",
        "host": socket.gethostname(),
        "run": "run-7",
        "verdict": "red",
        "rc": "1",
        "build_seconds": "42",
        "kind": "bazel_target_fail",
        "fields": ["//pkg:target", "1"],
        "line": 2,
        "_msg": "FAIL: //pkg:target (Exit 1)",
    }
    assert "logs_push: pushed — 200 (9 events)\n" in capsys.readouterr().err


def test_main_tags_a_zero_rc_green_and_defaults_the_run_to_host_and_log_mtime(
    sink: _Sink, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A zero rc is green with no extra fields; the run is `<host>-<mtime>`, or PK_RUN_ID if set."""
    monkeypatch.delenv("PK_RUN_ID", raising=False)
    log = tmp_path / "hook.log"
    log.write_text("FAIL: //a:b (Exit 2)\n", encoding="utf-8")
    url = f"http://127.0.0.1:{sink.port}/"
    logs_push.main([str(log), "--rc", "0", "--url", url])
    expected = f"{socket.gethostname()}-{int(log.stat().st_mtime)}"
    monkeypatch.setenv("PK_RUN_ID", "from-env")
    logs_push.main([str(log), "--url", url])
    first, second = (_lines(body)[0] for _path, _type, body in sink.seen)
    assert (first["run"], first["verdict"], "rc" in first, "build_seconds" in first) == (
        expected,
        "green",
        True,
        False,
    )
    assert (second["run"], second["verdict"], "rc" in second) == ("from-env", "green", False)


def test_main_reads_the_sink_from_the_environment(
    sink: _Sink, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no --url, PAPERKIT_LOGS_URL names the sink."""
    monkeypatch.setenv("PAPERKIT_LOGS_URL", f"http://127.0.0.1:{sink.port}/env")
    log = tmp_path / "hook.log"
    log.write_text("FAIL: //a:b (Exit 2)\n", encoding="utf-8")
    assert logs_push.main([str(log)]) == 0
    assert sink.seen[0][0] == "/env"


def test_main_without_a_sink_skips_quietly_with_exit_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No --url and no PAPERKIT_LOGS_URL is a no-op that says so on stderr."""
    monkeypatch.delenv("PAPERKIT_LOGS_URL", raising=False)
    assert logs_push.main([str(tmp_path / "hook.log")]) == 0
    assert "PAPERKIT_LOGS_URL unset" in capsys.readouterr().err


def test_main_reports_a_failed_push_but_still_exits_0(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Telemetry never fails a commit: a dead sink is `FAILED` on stderr and exit 0."""
    log = tmp_path / "hook.log"
    log.write_text("FAIL: //a:b (Exit 2)\n", encoding="utf-8")
    url = f"http://127.0.0.1:{_REFUSED_PORT}/"
    assert logs_push.main([str(log), "--url", url]) == 0
    assert "logs_push: FAILED — ConnectionRefusedError" in capsys.readouterr().err


def test_main_refuses_a_bad_command_line_with_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    """A flag where the log should be is a usage error."""
    assert logs_push.main(["--rc", "1"]) == _USAGE_EXIT
    assert capsys.readouterr().err == logs_push.USAGE + "\n"
