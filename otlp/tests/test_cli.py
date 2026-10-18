# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-otlp log`: stdin lines arrive as OTLP records with the nonce (W1418).

⚑ THE ENDPOINT IS A PLANTED LOOPBACK SERVER; each request it records is parsed back by the same
published wheel, so what the CLI built is what was read. The controls are the refusals: no URL and
a malformed `--field` are exit 2 with nothing sent, blank lines are skipped, and an unreachable
endpoint is exit 1 with the reason and how many records were sent before it.
"""

from __future__ import annotations

import io
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING, cast

from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest

from mikemol.otlp import cli, endpoints, sender

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    import pytest

Doc = dict[str, object]
Bodies = list[bytes]
_USAGE = 2
_FAILED = 1
_TWO = 2


@contextmanager
def _endpoint() -> Iterator[tuple[str, Bodies]]:
    # A one-purpose local receiver that records each POST body and answers 204.
    bodies: Bodies = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            bodies.append(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            self.send_response(204)
            self.end_headers()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}{sender.LOGS_PATH}", bodies
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _record(body: bytes) -> Doc:
    doc = MessageToDict(ExportLogsServiceRequest.FromString(body))
    resource = cast("list[Doc]", doc["resourceLogs"])[0]
    scope = cast("list[Doc]", resource["scopeLogs"])[0]
    return cast("list[Doc]", scope["logRecords"])[0]


def _attrs(record: Doc) -> dict[str, object]:
    return {str(a["key"]): a["value"] for a in cast("list[Doc]", record["attributes"])}


def test_each_non_blank_line_arrives_with_its_fields_severity_and_one_shared_nonce(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Two lines and a blank: two records, the same nonce, the field and the severity text."""
    argv = ["log", "--service", "svc", "--namespace", "mtools", "--field", "sha=abc"]
    with _endpoint() as (url, bodies):
        code = cli.main([*argv, "--url", url, "--severity", "WARN"], io.StringIO("one\n\ntwo\n"))
    assert code == cli.EXIT_SENT
    records = [_record(b) for b in bodies]
    assert [cast("Doc", r["body"])["stringValue"] for r in records] == ["one", "two"]
    first, second = (_attrs(r) for r in records)
    assert first["otlp_log_nonce"] == second["otlp_log_nonce"]
    assert first["sha"] == {"stringValue": "abc"}
    assert records[0]["severityText"] == "WARN"
    assert f"nonce={cast('Doc', first['otlp_log_nonce'])['stringValue']}" in capsys.readouterr().out


def test_no_url_and_a_malformed_field_are_usage_refusals_that_send_nothing(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The control: exit 2 for a missing URL and for a `--field` with no `=`; nothing is sent."""
    monkeypatch.delenv(cli.URL_ENV, raising=False)
    # ⚑ HERMETIC AGAINST THE HOST (found 2026-10-17): with MIKEMOL_ENDPOINTS in the caller's
    # environment this test resolved the real logs store, SENT a record to it and failed.
    # ⚑ AND AGAINST THE HOST'S FILE (W1528, 2026-10-18): with the variable unset the resolver reads
    # $HOME/.config/mikemol/endpoints.json, so HOME is an empty directory here.
    monkeypatch.delenv(endpoints.ENV, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    base = ["log", "--service", "svc", "--namespace", "mtools"]
    assert cli.main(base, io.StringIO("x\n")) == _USAGE
    assert (
        cli.main([*base, "--url", "http://127.0.0.1:1", "--field", "bad"], io.StringIO("x"))
        == _USAGE
    )
    assert "need --url" in capsys.readouterr().err


def test_the_url_may_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """MIKEMOL_OTLP_LOGS_URL stands in for --url."""
    with _endpoint() as (url, bodies):
        monkeypatch.setenv(cli.URL_ENV, url)
        code = cli.main(["log", "--service", "s", "--namespace", "n"], io.StringIO("hello\n"))
    assert (code, len(bodies)) == (cli.EXIT_SENT, 1)


def _publish(path: Path, base: str) -> None:
    # The host's endpoints file with the one name this CLI resolves.
    doc: dict[str, str] = {"victorialogs-http": base}
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_the_named_endpoint_resolves_through_the_hosts_file_and_the_full_url_still_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Luthen's route: MIKEMOL_ENDPOINTS names the base and the path is appended; a URL wins."""
    with _endpoint() as (url, bodies):
        base = url.removesuffix(sender.LOGS_PATH)
        names = tmp_path / "endpoints.json"
        _publish(names, base)
        monkeypatch.delenv(cli.URL_ENV, raising=False)
        monkeypatch.setenv(endpoints.ENV, str(names))
        argv = ["log", "--service", "s", "--namespace", "n"]
        assert cli.main(argv, io.StringIO("by name\n")) == cli.EXIT_SENT
        assert len(bodies) == 1
        _publish(names, "http://127.0.0.1:1")
        monkeypatch.setenv(cli.URL_ENV, url)
        assert cli.main(argv, io.StringIO("full url wins\n")) == cli.EXIT_SENT
        assert len(bodies) == _TWO


def test_an_unreachable_endpoint_is_exit_one_naming_the_reason_and_the_count_sent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A closed port fails the first line: exit 1, `0 sent before it`, the cause on stderr."""
    with _endpoint() as (url, _):
        pass
    code = cli.main(["log", "--service", "s", "--namespace", "n", "--url", url], io.StringIO("x\n"))
    assert code == _FAILED
    assert "0 sent before it" in capsys.readouterr().err
