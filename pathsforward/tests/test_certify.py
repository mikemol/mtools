# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for --certify: the policy input built read-only, the pinned opa, three exit codes."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import certify, cli, opa_eval, store
from mikemol.pathsforward.model import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_NOW = "2026-10-08T12:00:00Z"
_REPO = "home"
_PEER = "peer"
_BOUND = 3
_EXEC = 0o755
_CLEAN: Rec = {
    "symbol": "W1",
    "title": "one bounded thing",
    "status": "ready",
    "blocked_on": [],
    "blocked_kind": None,
    "enables": ["W2", "peer:W9"],
    "next_bounded_step": "run it",
    "evidence": "it printed OK",
    "ticks_blocked": 0,
    "population": {"source": "the files under src/", "bound": _BOUND},
}


def _wp(sym: str, status: str = "ready", **extra: object) -> Rec:
    """Build a waypoint from the clean one.

    Returns:
        the waypoint.

    """
    return {**_CLEAN, "symbol": sym, "status": status, "enables": [], **extra}


def _queue(root: Path, repo: str, waypoints: list[Rec], residue: list[str]) -> Path:
    """Write `<root>/<repo>/.claude/paths-forward.json`.

    Returns:
        the queue's path.

    """
    path = root / repo / ".claude" / "paths-forward.json"
    path.parent.mkdir(parents=True)
    doc: Rec = {
        "counter": 9,
        "waypoints": waypoints,
        "residue": [{"symbol": s, "reason": "why"} for s in residue],
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _home(root: Path) -> Path:
    """Write the home queue (W1 clean, W2 live, W4 done, W3 residue) and a peer holding W9.

    Returns:
        the home queue's path.

    """
    _queue(root, _PEER, [_wp("W9")], ["W8"])
    unbounded = _wp("W5", population={"source": "all of them", "bound": None})
    return _queue(root, _REPO, [_CLEAN, _wp("W2"), _wp("W4", "done"), unbounded], ["W3"])


def _fake_opa(tmp_path: Path, body: str) -> str:
    """Write an executable stand-in for opa.

    Returns:
        its path.

    """
    path = tmp_path / "fake-opa"
    path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
    path.chmod(_EXEC)
    return str(path)


def _certify(path: Path, root: Path, *syms: str) -> int:
    """Run `--certify` on a queue.

    Returns:
        the exit code.

    """
    return cli.main(["--state", str(path), "--certify", *syms, "--root", str(root)])


def _verdict(line: str) -> Rec:
    """Read one printed verdict.

    Returns:
        the verdict.

    """
    return cast("Rec", json.loads(line))


def test_items_carry_the_waypoint_the_ref_the_clock_and_the_local_graph(tmp_path: Path) -> None:
    """Live and landed are this queue's own symbols; enables keeps only local edges."""
    path = _home(tmp_path)
    (item,) = certify.items(store.load(path), ["W1"], _REPO, _NOW, tmp_path)
    assert (item["ref"], item["now"], item["waypoint"]) == (f"{_REPO}:W1", _NOW, _CLEAN)
    graph = cast("Rec", item["graph"])
    assert graph["live"] == ["W1", "W2", "W5"]
    assert graph["landed"] == ["W3", "W4"]
    assert cast("Rec", graph["enables"])["W1"] == ["W2"]
    assert graph["known"] == ["peer:W9"]


def test_a_foreign_reference_resolves_only_when_its_owner_holds_it(tmp_path: Path) -> None:
    """peer:W9 is live there, peer:W8 is its residue; peer:W7 and gone:W1 resolve to nothing."""
    path = _home(tmp_path)
    refs = ["peer:W9", "peer:W8", "peer:W7", "gone:W1", "W2", f"{_REPO}:W2"]
    assert certify.known(tmp_path, _REPO, store.load(path), refs) == [
        f"{_REPO}:W2",
        "peer:W8",
        "peer:W9",
    ]


@pytest.mark.parametrize("sym", ["W3", "W77"])
def test_a_symbol_not_live_here_is_refused_not_judged(tmp_path: Path, sym: str) -> None:
    """Residue has no lifecycle left, and a symbol never issued is a typo the caller must see."""
    with pytest.raises(RefusedError, match=sym):
        certify.items(store.load(_home(tmp_path)), ["W1", sym], _REPO, _NOW, tmp_path)


@pytest.mark.parametrize(
    "doc",
    [
        None,
        {},
        {"result": []},
        {"result": ["x"]},
        {"result": [{}]},
        {"result": [{"expressions": []}]},
        {"result": [{"expressions": ["x"]}]},
        {"result": [{"expressions": [{"value": {}}]}]},
    ],
)
def test_an_undefined_or_malformed_result_yields_no_verdicts(doc: object) -> None:
    """Anything but a list under result[0].expressions[0].value is no verdict at all."""
    assert not opa_eval.verdicts_in(doc)


def test_a_result_keeps_only_object_verdicts() -> None:
    """The list is read in order, and a non-object entry is dropped rather than trusted."""
    doc = {"result": [{"expressions": [{"value": [{"ref": "a"}, 1, {"ref": "b"}]}]}]}
    assert opa_eval.verdicts_in(doc) == [{"ref": "a"}, {"ref": "b"}]


def test_no_opa_is_unavailable_never_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With OPA_BIN unset and nothing on PATH, or naming no file, resolve raises."""
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(opa_eval.OpaUnavailableError, match="not found"):
        opa_eval.resolve({})
    with pytest.raises(opa_eval.OpaUnavailableError, match="not found"):
        opa_eval.resolve({opa_eval.OPA_ENV: str(tmp_path / "absent")})


@pytest.mark.parametrize(
    "body", ["echo 'Version: 0.70.0'", "echo 'Version: 1.20.2'; exit 3", "echo nothing"]
)
def test_an_opa_that_is_not_the_pin_is_refused(tmp_path: Path, body: str) -> None:
    """A wrong version, a failing `opa version` or no version line are all not the pin."""
    with pytest.raises(opa_eval.OpaUnavailableError, match=opa_eval.PINNED):
        opa_eval.resolve({opa_eval.OPA_ENV: _fake_opa(tmp_path, body)})


def test_the_pinned_opa_named_by_the_environment_is_used(tmp_path: Path) -> None:
    """OPA_BIN wins over PATH, and the pin is read from `opa version`'s own Version line."""
    fake = _fake_opa(tmp_path, f"echo 'Version: {opa_eval.PINNED}'")
    assert opa_eval.resolve({opa_eval.OPA_ENV: fake}) == fake


def test_a_failing_eval_raises_with_its_account(tmp_path: Path) -> None:
    """A nonzero exit from opa is an error carrying what it said, never an empty verdict list."""
    fake = _fake_opa(tmp_path, "echo 'policy did not compile' >&2; exit 2")
    with pytest.raises(opa_eval.OpaUnavailableError, match="did not compile"):
        opa_eval.verdicts([{"waypoint": _CLEAN}], fake)


def test_fewer_verdicts_than_items_certifies_nothing(tmp_path: Path) -> None:
    """A verdict list that does not match the items one for one is refused whole."""
    fake = _fake_opa(tmp_path, """echo '{"result":[{"expressions":[{"value":[]}]}]}'""")
    with pytest.raises(opa_eval.OpaUnavailableError, match="0 verdict"):
        opa_eval.verdicts([{"waypoint": _CLEAN}], fake)


def test_certify_prints_one_runtime_valid_verdict_and_exits_ok(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The real policy under the pinned opa: a fully declared waypoint is runtime-valid."""
    assert _certify(_home(tmp_path), tmp_path, "W1") == cli.EXIT_OK
    (line,) = capsys.readouterr().out.splitlines()
    assert _verdict(line) == {
        "level": "coverable",
        "ref": f"{_REPO}:W1",
        "reference_arm": "host:luthen",
        "residue": [],
    }


def test_certify_exits_failed_when_any_verdict_carries_residue(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unbounded population stops W5 at observable, so the set is not all runtime-valid."""
    assert _certify(_home(tmp_path), tmp_path, "W1", "W5") == cli.EXIT_FAILED
    got = capsys.readouterr()
    assert [_verdict(ln)["level"] for ln in got.out.splitlines()] == ["coverable", "observable"]
    assert "1 runtime-valid, 1 residue" in got.err


def test_certify_refuses_when_nothing_could_be_judged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A symbol not live here, or no pinned opa, is exit 2 and prints no verdict."""
    path = _home(tmp_path)
    assert _certify(path, tmp_path, "W3") == cli.EXIT_REFUSED
    monkeypatch.setenv(opa_eval.OPA_ENV, str(tmp_path / "absent"))
    assert _certify(path, tmp_path, "W1") == cli.EXIT_REFUSED
    got = capsys.readouterr()
    refusals = [ln for ln in got.err.splitlines() if ln.startswith("not certified: ")]
    assert (got.out, len(refusals)) == ("", len(("W3", "no opa")))
