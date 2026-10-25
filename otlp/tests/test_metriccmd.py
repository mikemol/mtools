# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-otlp metric`: one sample out, of the kind asked (W1445).

⚑ A PLANTED LOCAL STORE, NOT LUTHEN'S: it records each POST, so the path, the protobuf body and the
kind of metric are read back through the same wheel. Whether the live vmsingle agrees is a witness
that needs the cluster and is not claimed here. The controls: a gauge must NOT arrive as a sum (a
reader that rates it would be wrong), an up-down must arrive as a non-monotonic sum, a store that
refuses is exit 1, and no destination is a usage refusal.
"""

from __future__ import annotations

import io
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING, cast

from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)

from mikemol.otlp import cli, metriccmd, sender

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    import pytest

Doc = dict[str, object]
ACCEPTED = 200
REFUSED = 500


@contextmanager
def _store(status: int = ACCEPTED) -> Iterator[tuple[str, list[tuple[str, bytes]]]]:
    posts: list[tuple[str, bytes]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            posts.append((self.path, body))
            self.send_response(status)
            self.end_headers()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", posts
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _argv(base: str, *extra: str) -> list[str]:
    who = ["--service", "mikemol-commit", "--namespace", "mtools"]
    return ["metric", "--url", base, *who, "--name", "mikemol.commit.queued", *extra]


def _metric(body: bytes) -> Doc:
    doc = MessageToDict(ExportMetricsServiceRequest.FromString(body))
    resource = cast("list[Doc]", doc["resourceMetrics"])[0]
    scope = cast("list[Doc]", resource["scopeMetrics"])[0]
    return cast("list[Doc]", scope["metrics"])[0]


def test_a_gauge_is_posted_to_the_metrics_path_as_a_gauge(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The default kind: the path is luthen's, the metric is a gauge with the value and labels."""
    with _store() as (base, posts):
        argv = _argv(base, "--value", "3", "--field", "repo=mtools")
        assert cli.main(argv) == metriccmd.EXIT_SENT
    path, body = posts[0]
    assert path == sender.METRICS_PATH
    sent = _metric(body)
    assert sent["name"] == "mikemol.commit.queued"
    assert "gauge" in sent
    assert "sum" not in sent
    point = cast("list[Doc]", cast("Doc", sent["gauge"])["dataPoints"])[0]
    assert point["asInt"] == "3"
    assert "sent gauge mikemol.commit.queued=3" in capsys.readouterr().out


def test_an_up_down_sample_arrives_as_a_non_monotonic_sum() -> None:
    """The other kind: a cumulative sum that is allowed to fall."""
    with _store() as (base, posts):
        assert cli.main(_argv(base, "--value", "2", "--kind", "updown")) == metriccmd.EXIT_SENT
    total = cast("Doc", _metric(posts[0][1])["sum"])
    assert total.get("isMonotonic", False) is False
    assert total["aggregationTemporality"] == "AGGREGATION_TEMPORALITY_CUMULATIVE"


def test_a_fractional_value_stays_a_double() -> None:
    """2.5 is not rounded to 2: it arrives as a double point."""
    with _store() as (base, posts):
        assert cli.main(_argv(base, "--value", "2.5")) == metriccmd.EXIT_SENT
    point = cast("list[Doc]", cast("Doc", _metric(posts[0][1])["gauge"])["dataPoints"])[0]
    assert "asInt" not in point
    assert str(point["asDouble"]) == "2.5"


def test_a_store_that_refuses_the_sample_is_a_failed_send(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A 500 is exit 1 naming the status."""
    with _store(REFUSED) as (base, _):
        assert cli.main(_argv(base, "--value", "1")) == metriccmd.EXIT_FAILED
    assert "500" in capsys.readouterr().err


def test_no_destination_is_a_usage_refusal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """With no --url and no endpoints file the command refuses, naming the endpoint."""
    monkeypatch.delenv("MIKEMOL_ENDPOINTS", raising=False)
    # The resolver falls back to $HOME/.config/mikemol/endpoints.json (W1528): an empty HOME.
    monkeypatch.setenv("HOME", str(tmp_path))
    argv = ["metric", "--service", "s", "--namespace", "n", "--name", "x", "--value", "1"]
    assert cli.main(argv) == cli.EXIT_USAGE
    assert metriccmd.ENDPOINT in capsys.readouterr().err


_WHEN = 1_700_000_000_000_000_000
_BATCH = (
    f'{{"name": "mikemol.gate.target.cpu.seconds", "value": 63.1, "time_ns": {_WHEN}, '
    '"fields": {"target": "//hooks:mutants_1", "kind": "mutants"}}\n'
    f'{{"name": "mikemol.gate.target.wall.seconds", "value": 12, "time_ns": {_WHEN + 5}, '
    '"fields": {"target": "//hooks:mutants_1", "kind": "mutants"}}\n'
    f'{{"name": "mikemol.gate.target.cpu.seconds", "value": 4, "time_ns": {_WHEN + 9}, '
    '"fields": {"target": "//ratchet:mutants", "kind": "mutants"}}\n'
)
_THREE_POINTS = 3
_TWO_METRICS = 2


def _batch_argv(base: str) -> list[str]:
    return ["metrics", "--url", base, "--service", "mikemol-gate", "--namespace", "mtools"]


def _metrics(body: bytes) -> list[Doc]:
    doc = MessageToDict(ExportMetricsServiceRequest.FromString(body))
    resource = cast("list[Doc]", doc["resourceMetrics"])[0]
    scope = cast("list[Doc]", resource["scopeMetrics"])[0]
    return cast("list[Doc]", scope["metrics"])


def test_a_batch_is_one_post_with_a_metric_per_name_and_each_points_own_time(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """W1784: three samples, two names, one request; the times are the lines', not arrival."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(_BATCH))
    with _store() as (base, posts):
        assert cli.main(_batch_argv(base)) == metriccmd.EXIT_SENT
    assert len(posts) == 1
    assert posts[0][0] == sender.METRICS_PATH
    sent = _metrics(posts[0][1])
    assert len(sent) == _TWO_METRICS
    cpu = next(m for m in sent if m["name"] == "mikemol.gate.target.cpu.seconds")
    points = cast("list[Doc]", cast("Doc", cpu["gauge"])["dataPoints"])
    assert [p["timeUnixNano"] for p in points] == [str(_WHEN), str(_WHEN + 9)]
    counted = sum(len(cast("list[Doc]", cast("Doc", m["gauge"])["dataPoints"])) for m in sent)
    assert counted == _THREE_POINTS
    assert "sent 3 gauge samples" in capsys.readouterr().out


def test_a_bad_line_refuses_the_whole_batch_and_names_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """All or nothing: nothing is posted, and the second line is the one named."""
    lines = _BATCH.splitlines()[0] + "\nnot json\n" + _BATCH.splitlines()[1] + "\n"
    monkeypatch.setattr(sys, "stdin", io.StringIO(lines))
    with _store() as (base, posts):
        assert cli.main(_batch_argv(base)) == metriccmd.EXIT_FAILED
    assert not posts
    assert "line 2" in capsys.readouterr().err


def test_a_line_without_a_time_is_stamped_with_the_arrival_time() -> None:
    """The default: `time_ns` absent means now, which the caller passes in."""
    samples, why = metriccmd.parse_batch(['{"name": "x", "value": 1}'], _WHEN)
    assert not why
    assert samples[0].time_ns == _WHEN


def test_a_boolean_a_string_value_and_a_non_object_are_not_samples() -> None:
    """The controls: True is not 1, a quoted number is not a number, a list is not a row."""
    for bad in ('{"name": "x", "value": true}', '{"name": "x", "value": "3"}', "[1, 2]"):
        samples, why = metriccmd.parse_batch([bad], _WHEN)
        assert not samples
        assert "line 1" in why


def test_an_empty_batch_sends_nothing_and_succeeds(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Blank lines are skipped; nothing to send is a success with no POST."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("\n\n"))
    with _store() as (base, posts):
        assert cli.main(_batch_argv(base)) == metriccmd.EXIT_SENT
    assert not posts
    assert "sent 0 gauge samples" in capsys.readouterr().out


def test_a_batch_row_may_describe_its_metric() -> None:
    """W1961: unit, description, freshness class, companion and owner are read from the row."""
    row = (
        '{"name": "m.x", "value": 1, "unit": "1", "description": "d", '
        '"freshness_class": "event_driven", "freshness_companion": "m.alive", '
        '"owner": "mtools:W1"}'
    )
    samples, why = metriccmd.parse_batch([row], 0)
    assert not why
    only = samples[0]
    assert (only.unit, only.description, only.freshness_class) == ("1", "d", "event_driven")
    assert (only.freshness_companion, only.owner) == ("m.alive", "mtools:W1")


def test_an_unusable_description_refuses_the_batch() -> None:
    """A number, an unknown class, an event-driven row with no companion, a companion alone."""
    base = '{"name": "m.x", "value": 1, '
    bad = (
        base + '"owner": 3}',
        base + '"freshness_class": "daily"}',
        base + '"freshness_class": "event_driven"}',
        base + '"freshness_class": "continuous", "freshness_companion": "m.alive"}',
        base + '"freshness_companion": "m.alive"}',
    )
    for line in bad:
        refused, reason = metriccmd.parse_batch([line], 0)
        assert refused == []
        assert reason
    fine, why = metriccmd.parse_batch([base + '"freshness_class": "continuous"}'], 0)
    assert not why
    assert len(fine) == 1
