# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for lifting a held row on a signed ruling (mtools:W1270, W1271, W1194).

⚑ THE SIGNATURES ARE REAL: the pinned opa signs with the two RFC 8032 test keys (public test
vectors, not secrets) and verifies through `opa_eval.verify_eddsa`, so a valid ruling, a ruling for
another card, a ruling signed by another key and an empty signature are each judged by the same
cryptography the lift uses. ⚑ THE CONTROLS ARE THE REFUSALS: nothing but the one named, held row
ever changes, and every refusal leaves the whole queue equal to what it was.
"""

from __future__ import annotations

import base64
import copy
import json
import subprocess
from typing import cast

import pytest

from mikemol.pathsforward import lift, opa_eval, ops
from mikemol.pathsforward.model import RefusedError, State, validate

_NOW = "2026-10-15T12:00:00Z"
_TIME = "2026-10-15T11:59:00Z"
_SECRET_ONE = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
_PUBLIC_ONE = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
_SECRET_TWO = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
_PUBLIC_TWO = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(part: str) -> str:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)).decode("utf-8")


def _jwk(public: bytes) -> str:
    key: dict[str, str] = {"kty": "OKP", "crv": "Ed25519", "x": _b64(public)}
    return json.dumps(key)


def _opa() -> str:
    return opa_eval.resolve()


def _verify(jws: str, jwk: str) -> bool:
    return opa_eval.verify_eddsa(jws, jwk, _opa())


def _sign(signing: str, secret: bytes, public: bytes) -> str:
    """Sign exactly `signing` with a test key, through the pinned opa.

    Returns:
        the compact JWS whose first two parts are `signing`.

    """
    header, body = (_unb64(part) for part in signing.split("."))
    private: dict[str, str] = {"kty": "OKP", "crv": "Ed25519", "d": _b64(secret), "x": _b64(public)}
    key = json.dumps(private)
    query = f"io.jwt.encode_sign_raw({json.dumps(header)}, {json.dumps(body)}, {json.dumps(key)})"
    done = subprocess.run(
        [_opa(), "eval", "--format", "raw", query], capture_output=True, text=True, check=True
    )
    jws = done.stdout.strip()
    assert jws.rsplit(".", 1)[0] == signing
    return jws


def _ruling(card: str = "W1", to: str = "done", blocked_on: tuple[str, ...] = ()) -> str:
    signing = lift.signing_input(card, "Close it", _TIME, to, blocked_on)
    return _sign(signing, _SECRET_ONE, _PUBLIC_ONE)


def _wp(
    sym: str, status: str, kind: str | None = None, waits: tuple[str, ...] = ()
) -> dict[str, object]:
    return {
        "symbol": sym,
        "title": f"title of {sym}",
        "status": status,
        "blocked_on": list(waits),
        "blocked_kind": kind,
        "next_bounded_step": "the step",
        "evidence": "",
        "ticks_blocked": 0,
    }


def _state() -> State:
    """Build a queue with two held rows, a ready row and an agent-blocked row.

    Returns:
        the state.

    """
    return validate(
        {
            "counter": 4,
            "heartbeat": "h0",
            "waypoints": [
                _wp("W1", "blocked", "human", ("operator: act apply the change",)),
                _wp("W2", "ready"),
                _wp("W3", "blocked", "human", ("operator: decide the split",)),
                _wp("W4", "blocked", "agent", ("W2",)),
            ],
            "residue": [],
        }
    )


def _lift(state: State, jws: str, public: bytes = _PUBLIC_ONE) -> str:
    return lift.lift(state, jws, _jwk(public), _verify, _NOW)


def test_a_valid_ruling_lifts_exactly_the_named_held_row_and_records_it() -> None:
    """W1 goes done with the ruling in its evidence; W2, W3 and W4 are untouched."""
    state = _state()
    others = copy.deepcopy([w for w in state.waypoints if w["symbol"] != "W1"])
    assert _lift(state, _ruling()) == "W1"
    row = ops.find(state, "W1")
    assert row["status"] == "done"
    assert f"operator ruling {_TIME} (signature verified): Close it" in str(row["evidence"])
    assert [w for w in state.waypoints if w["symbol"] != "W1"] == others


def test_a_ruling_can_reblock_the_row_on_a_named_card_as_an_agent_block() -> None:
    """The W1153 shape: the operator withdraws the ask and the row waits on the split design."""
    state = _state()
    _lift(state, _ruling("W3", "blocked", ("W2",)))
    row = ops.find(state, "W3")
    assert (row["status"], row["blocked_on"], row["blocked_kind"]) == ("blocked", ["W2"], "agent")


def test_a_signature_cannot_be_moved_to_another_card_or_another_outcome() -> None:
    """The signature over W1 is kept and the payload edited to name W3, or to say ready: refused."""
    state = _state()
    before = copy.deepcopy(state.waypoints)
    header, body, signature = _ruling("W1").split(".")
    for edit in ({"card": "W3"}, {"to": "ready"}, {"ruling": "Do something else"}):
        original = cast("dict[str, object]", json.loads(_unb64(body)))
        edited: dict[str, object] = {**original, **edit}
        forged = f"{header}.{_b64(json.dumps(edited, sort_keys=True).encode())}.{signature}"
        with pytest.raises(RefusedError, match="does not verify"):
            _lift(state, forged)
    assert state.waypoints == before


def test_a_ruling_signed_by_another_key_or_with_no_signature_is_refused() -> None:
    """The key is the operator's: a different key's signature, an empty one and a zero one fail."""
    state = _state()
    before = copy.deepcopy(state.waypoints)
    signing = lift.signing_input("W1", "Close it", _TIME, "done")
    stranger = _sign(signing, _SECRET_TWO, _PUBLIC_TWO)
    for token in (stranger, f"{signing}.", f"{signing}.{_b64(bytes(64))}"):
        with pytest.raises(RefusedError, match=r"does not verify|three parts"):
            _lift(state, token)
    assert state.waypoints == before


def test_a_valid_ruling_cannot_lift_a_row_that_is_not_held() -> None:
    """W2 is ready and W4 is blocked on an agent: neither is held on the operator."""
    state = _state()
    before = copy.deepcopy(state.waypoints)
    for card in ("W2", "W4"):
        with pytest.raises(RefusedError, match="is not held on the operator"):
            _lift(state, _ruling(card))
    with pytest.raises(RefusedError, match="W9"):
        _lift(state, _ruling("W9"))
    assert state.waypoints == before


def test_a_ruling_lifts_a_row_once_even_if_it_is_held_again() -> None:
    """After the lift the row is not held; held again, the same signed ruling is still refused."""
    state = _state()
    ruling = _ruling()
    _lift(state, ruling)
    with pytest.raises(RefusedError, match="not held"):
        _lift(state, ruling)
    row = ops.find(state, "W1")
    row.update(
        {"status": "blocked", "blocked_kind": "human", "blocked_on": ["operator: act again"]}
    )
    with pytest.raises(RefusedError, match="already carries this ruling"):
        _lift(state, ruling)


@pytest.mark.parametrize(
    ("jws", "fragment"),
    [
        ("a.b", "three parts"),
        ("!!.!!.!!", "does not decode"),
        (f"{_b64(b'{}')}.{_b64(b'{}')}.x", "header is"),
        (f"{_b64(lift.HEADER.encode())}.{_b64(b'[]')}.x", "not an object"),
        (f"{_b64(lift.HEADER.encode())}.{_b64(b'{}')}.x", "fields are"),
    ],
)
def test_a_malformed_ruling_is_refused_before_anything_is_judged(jws: str, fragment: str) -> None:
    """Each shape of garbage is a named refusal, not a traceback and not a false verdict."""
    with pytest.raises(RefusedError, match=fragment):
        lift.payload_of(jws)


def test_the_payload_must_have_the_right_types_outcome_and_blocked_on() -> None:
    """A number for a string, an unknown outcome, and blocked_on out of step with the outcome."""
    base = {"card": "W1", "ruling": "r", "time": "t", "to": "done", "blocked_on": []}
    bad = [
        ({**base, "card": 1}, "wrong types"),
        ({**base, "blocked_on": [1]}, "wrong types"),
        ({**base, "to": "dropped"}, "not one of"),
        ({**base, "to": "blocked"}, "only then"),
        ({**base, "blocked_on": ["W2"]}, "only then"),
    ]
    for payload, fragment in bad:
        token = f"{_b64(lift.HEADER.encode())}.{_b64(json.dumps(payload).encode())}.x"
        with pytest.raises(RefusedError, match=fragment):
            lift.payload_of(token)
    ok = f"{_b64(lift.HEADER.encode())}.{_b64(json.dumps(base).encode())}.x"
    assert lift.payload_of(ok) == base


def test_the_signing_input_is_canonical_and_reads_back_as_the_same_payload() -> None:
    """Sorted keys, no spaces: one ruling, one byte string; and payload_of reads it back."""
    signing = lift.signing_input("W1", "Close it", _TIME, "blocked", ("W2", "W3"))
    header, body = signing.split(".")
    assert _unb64(header) == lift.HEADER
    assert _unb64(body) == (
        '{"blocked_on":["W2","W3"],"card":"W1","ruling":"Close it",'
        f'"time":"{_TIME}","to":"blocked"}}'
    )
    assert lift.payload_of(f"{signing}.x")["blocked_on"] == ["W2", "W3"]
