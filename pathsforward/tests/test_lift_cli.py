# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--lift JWS --jwk FILE` through the command line (mtools:W1277, W1194).

⚑ THE SIGNATURES ARE REAL: the pinned opa signs with the two RFC 8032 test keys (public test
vectors, not secrets), so the command line is shown lifting a held row under a valid ruling and
refusing, with the queue byte-identical, a ruling signed by another key, a row that is not held, a
missing key, and an opa that cannot run. The core's own cases are in test_lift.
"""

from __future__ import annotations

import base64
import json
import subprocess
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli, lift, opa_eval

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_TIME = "2026-10-15T11:59:00Z"
_SECRET_ONE = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
_PUBLIC_ONE = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
_SECRET_TWO = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
_PUBLIC_TWO = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
_OK = cli.EXIT_OK
_REFUSED = cli.EXIT_REFUSED


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(part: str) -> str:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)).decode("utf-8")


def _jwk_file(tmp_path: Path, public: bytes) -> Path:
    key: dict[str, str] = {"kty": "OKP", "crv": "Ed25519", "x": _b64(public)}
    path = tmp_path / "operator.jwk"
    path.write_text(json.dumps(key), encoding="utf-8")
    return path


def _sign(card: str, secret: bytes, public: bytes) -> str:
    """Sign a done-ruling for `card` with a test key through the pinned opa.

    Returns:
        the compact JWS.

    """
    signing = lift.signing_input(card, "Close it", _TIME, "done")
    header, body = (_unb64(part) for part in signing.split("."))
    private: dict[str, str] = {"kty": "OKP", "crv": "Ed25519", "d": _b64(secret), "x": _b64(public)}
    key = json.dumps(private)
    query = f"io.jwt.encode_sign_raw({json.dumps(header)}, {json.dumps(body)}, {json.dumps(key)})"
    done = subprocess.run(
        [opa_eval.resolve(), "eval", "--format", "raw", query],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def _card(symbol: str, status: str, kind: str | None) -> dict[str, object]:
    held = status == "blocked"
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "enables": [],
        "blocked_on": ["operator: act x"] if held else [],
        "blocked_kind": kind,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }


def _state(tmp_path: Path) -> Path:
    cards = [_card("W1", "blocked", "human"), _card("W2", "ready", None)]
    doc: dict[str, object] = {
        "counter": 2,
        "project_root": str(tmp_path),
        "waypoints": cards,
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _row(path: Path, symbol: str) -> dict[str, object]:
    doc = cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))
    rows = cast("list[dict[str, object]]", doc["waypoints"])
    return next(r for r in rows if r["symbol"] == symbol)


def _lift(path: Path, jws: str, *rest: str) -> int:
    return cli.main(["--state", str(path), "--lift", jws, *rest])


def test_a_valid_ruling_lifts_the_held_row_from_the_command_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W1 goes done under the operator's key and says LIFTED; W2 is untouched."""
    path = _state(tmp_path)
    before = _row(path, "W2")
    jws = _sign("W1", _SECRET_ONE, _PUBLIC_ONE)
    assert _lift(path, jws, "--jwk", str(_jwk_file(tmp_path, _PUBLIC_ONE))) == _OK
    assert "LIFTED W1" in capsys.readouterr().out
    assert _row(path, "W1")["status"] == "done"
    assert _row(path, "W2") == before


def test_a_ruling_signed_by_another_key_is_refused_and_the_queue_is_unchanged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The stranger's signature does not verify under the operator's key: exit 2, same bytes."""
    path = _state(tmp_path)
    saved = path.read_bytes()
    jws = _sign("W1", _SECRET_TWO, _PUBLIC_TWO)
    assert _lift(path, jws, "--jwk", str(_jwk_file(tmp_path, _PUBLIC_ONE))) == _REFUSED
    assert "does not verify" in capsys.readouterr().err
    assert path.read_bytes() == saved


def test_a_row_that_is_not_held_is_refused_even_under_a_valid_signature(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2 is ready: the operator's own key cannot lift what was never held."""
    path = _state(tmp_path)
    saved = path.read_bytes()
    jws = _sign("W2", _SECRET_ONE, _PUBLIC_ONE)
    assert _lift(path, jws, "--jwk", str(_jwk_file(tmp_path, _PUBLIC_ONE))) == _REFUSED
    assert "is not held on the operator" in capsys.readouterr().err
    assert path.read_bytes() == saved


def test_a_missing_key_a_key_that_is_not_a_file_and_an_opa_that_cannot_run_are_refusals(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """No --jwk, a directory for --jwk, and no usable opa each exit 2 with nothing saved."""
    path = _state(tmp_path)
    saved = path.read_bytes()
    jws = _sign("W1", _SECRET_ONE, _PUBLIC_ONE)
    assert _lift(path, jws) == _REFUSED
    assert "needs --jwk" in capsys.readouterr().err
    assert _lift(path, jws, "--jwk", str(tmp_path)) == _REFUSED
    assert "not a regular file" in capsys.readouterr().err
    monkeypatch.setenv(opa_eval.OPA_ENV, str(tmp_path / "no-opa"))
    assert _lift(path, jws, "--jwk", str(_jwk_file(tmp_path, _PUBLIC_ONE))) == _REFUSED
    assert "opa not found" in capsys.readouterr().err
    assert path.read_bytes() == saved


def test_jwk_without_lift_and_lift_with_a_stray_flag_are_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--lift` takes only --jwk: a field flag beside it is refused by name."""
    path = _state(tmp_path)
    jws = _sign("W1", _SECRET_ONE, _PUBLIC_ONE)
    key = str(_jwk_file(tmp_path, _PUBLIC_ONE))
    assert _lift(path, jws, "--jwk", key, "--weight", "1") == _REFUSED
    assert "does not apply to --lift" in capsys.readouterr().err


def _status_lines(tmp_path: Path) -> list[str]:
    ledger = (tmp_path / "paths-forward.ledger").read_text(encoding="utf-8")
    return [row for row in ledger.splitlines() if " status " in row]


def test_a_lift_ledgers_its_status_change_as_the_operators_and_a_plain_edit_does_not(
    tmp_path: Path,
) -> None:
    """W1790 (nemik:W770): `actor=operator` follows a verified lift, and no other status line."""
    path = _state(tmp_path)
    jws = _sign("W1", _SECRET_ONE, _PUBLIC_ONE)
    assert _lift(path, jws, "--jwk", str(_jwk_file(tmp_path, _PUBLIC_ONE))) == _OK
    [lifted] = _status_lines(tmp_path)
    assert " W1 " in lifted
    assert "actor=operator" in lifted
    plain = ["--state", str(path), "--update", "W2", "--status", "blocked"]
    held = ["--blocked-on", "operator: act y", "--blocked-kind", "human"]
    assert cli.main([*plain, *held]) == _OK
    last = _status_lines(tmp_path)[-1]
    assert " W2 " in last
    assert "actor=" not in last
