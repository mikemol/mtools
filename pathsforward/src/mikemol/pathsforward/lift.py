# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Lift one operator-held row on the strength of a signed ruling (mtools:W1270, W1194).

⚑ STANDING RULE 5 REFUSES AN AGENT THE LIFT OF A HELD ROW, AND THE OPERATOR'S OWN WORDS MUST STILL
BE ABLE TO LIFT IT. The ruling is a compact JWS signed (by the operator's phone authorising an
OpenBao transit key, luthen-observability:W1075) over a canonical payload; this module turns a valid
one into exactly one change. It never sees the code, the secret or the private key: it checks a
signature against a public JWK through an injected `verify`, so the real verifier is opa
(`opa_eval.verify_eddsa`, W1271) and a test plants true or false.

⚑ THE SIGNATURE BINDS EVERYTHING THE LIFT DOES. The payload is `{card, ruling, time, to,
blocked_on}`, signed whole, so a signature cannot be moved to another card, another ruling text, or
another outcome: `to` (done, ready or blocked) and its `blocked_on` are inside the signed bytes. The
requested payload named only card, ruling and time; the outcome is added because a signature that
leaves the outcome free would let whoever holds it choose it.

⚑ ONLY A HELD ROW MOVES, ONLY ONCE. A row is held when it is blocked on a human. Anything else is
refused even under a valid signature, so a ruling cannot rewrite a card that was never held; and a
row whose evidence already carries this ruling's note is refused, so a replay after the row was
re-held cannot lift it a second time. Nothing but the one named row changes.

⚑ EVERY REFUSAL IS BEFORE ANY WRITE: the payload is parsed, the row found and judged held, and the
signature verified, all before `ops.update` is called.
"""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import ops
from mikemol.pathsforward.model import RefusedError, strlist, text

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from mikemol.pathsforward.model import State

HEADER = '{"alg":"EdDSA"}'
FIELDS = frozenset({"card", "ruling", "time", "to", "blocked_on"})
TARGETS = frozenset({"done", "ready", "blocked"})
_PARTS = 3
_PAD = 4


def _b64(data: str) -> str:
    return base64.urlsafe_b64encode(data.encode("utf-8")).rstrip(b"=").decode("ascii")


def _unb64(part: str) -> str:
    padded = part + "=" * (-len(part) % _PAD)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")


def signing_input(
    card: str, ruling: str, time: str, to: str, blocked_on: Sequence[str] = ()
) -> str:
    """Build the exact bytes the operator's key signs, as a JWS signing input.

    ⚑ CANONICAL: sorted keys, no whitespace, so one ruling has one signing input and a verifier
    never depends on how a serializer chose to space it.

    Returns:
        `base64url(header).base64url(payload)`.

    """
    body = {"blocked_on": list(blocked_on), "card": card, "ruling": ruling, "time": time, "to": to}
    return f"{_b64(HEADER)}.{_b64(json.dumps(body, sort_keys=True, separators=(',', ':')))}"


def payload_of(jws: str) -> dict[str, object]:
    """Read and check the payload of a compact JWS, without trusting its signature.

    Returns:
        the payload, exactly the five fields, each of its type.

    Raises:
        RefusedError: when the token is not three parts, the header is not `{"alg":"EdDSA"}`, the
            body is not a JSON object of exactly the fields, a field has the wrong type, or `to`
            is not done, ready or blocked, or blocked_on is empty for blocked and not otherwise.

    """
    parts = jws.split(".")
    if len(parts) != _PARTS:
        msg = "a signed ruling is a compact JWS of three parts"
        raise RefusedError(msg)
    try:
        header = _unb64(parts[0])
        loaded = cast("object", json.loads(_unb64(parts[1])))
    except ValueError as fault:
        msg = f"the signed ruling does not decode: {fault}"
        raise RefusedError(msg) from fault
    if header != HEADER:
        msg = f"the signed ruling's header is {header!r}, not {HEADER}"
        raise RefusedError(msg)
    if not isinstance(loaded, dict):
        msg = "the signed ruling's payload is not an object"
        raise RefusedError(msg)
    body = cast("dict[str, object]", loaded)
    if set(body) != FIELDS:
        msg = f"the signed ruling's fields are {sorted(body)}, not {sorted(FIELDS)}"
        raise RefusedError(msg)
    blocked_on = body["blocked_on"]
    strings = isinstance(blocked_on, list) and all(
        isinstance(x, str) for x in cast("list[object]", blocked_on)
    )
    if not all(isinstance(body[k], str) for k in ("card", "ruling", "time", "to")) or not strings:
        msg = "the signed ruling's fields have the wrong types"
        raise RefusedError(msg)
    if body["to"] not in TARGETS:
        msg = f"the signed ruling's outcome {body['to']!r} is not one of {sorted(TARGETS)}"
        raise RefusedError(msg)
    if (body["to"] == "blocked") != bool(blocked_on):
        msg = "blocked_on is given when the outcome is blocked, and only then"
        raise RefusedError(msg)
    return body


def _note(body: dict[str, object]) -> str:
    return f"operator ruling {body['time']} (signature verified): {body['ruling']}"


def lift(state: State, jws: str, jwk: str, verify: Callable[[str, str], bool], now: str) -> str:
    """Apply one signed ruling to the one held row it names.

    Returns:
        the symbol of the row that was lifted.

    Raises:
        RefusedError: on a payload that does not parse, a card that is absent or not held, a
            ruling already applied to it, or a signature that does not verify.

    """
    body = payload_of(jws)
    card = str(body["card"])
    row = ops.find(state, card)
    status = text(row, "status")
    if status != "blocked" or text(row, "blocked_kind") != "human":
        msg = f"{card} is not held on the operator (status {status!r}): nothing to lift"
        raise RefusedError(msg)
    note = _note(body)
    if note in text(row, "evidence"):
        msg = f"{card} already carries this ruling: a signed ruling lifts a row once"
        raise RefusedError(msg)
    if not verify(jws, jwk):
        msg = f"the signature on the ruling for {card} does not verify"
        raise RefusedError(msg)
    to = str(body["to"])
    if to == "blocked":
        waits = tuple(strlist(body, "blocked_on"))
        update = ops.Update(
            status="blocked", blocked_on=waits, blocked_kind="agent", evidence_append=note
        )
    else:
        update = ops.Update(status=to, evidence_append=note)
    ops.update(state, card, update, now)
    return card
