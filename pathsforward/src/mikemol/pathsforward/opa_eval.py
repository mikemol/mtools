# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run the pinned opa over the realizability policy (W850): the ONE subprocess in this package.

⚑⚑ AN ABSENT OR WRONG-VERSION opa IS AN ERROR, NEVER A CLEAN VERDICT. A waypoint that was not
judged has measured nothing, so this raises and the caller exits "not checked". The pin is the
one pytestspec's `opa.PINNED` and MODULE.bazel's `@opa` hold (1.20.2): a different opa is a
different checker.

⚑ `OPA_BIN` WINS OVER PATH. Under bazel it names the hash-pinned `@opa` staged into the sandbox;
unset, PATH answers, and the version check still holds the binary to the pin.

⚑ THE QUEUE TRAVELS ON STDIN. The argv is the binary, fixed words and the package's own policy
file; no waypoint text ever becomes a word in the command.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

    from mikemol.pathsforward.model import Json

PINNED = "1.20.2"
OPA_ENV = "OPA_BIN"
POLICY = Path(__file__).with_name("policy") / "realizability.rego"
QUERY = "data.realizability.verdicts"
# ⚑ BOUNDED: a hung opa must fail the run, not hang the caller.
TIMEOUT_S = 60
# How much of opa's own account to carry into an error: enough to name the failure.
_ERR_CHARS = 500
_VERSION = "Version: "


class OpaUnavailableError(RuntimeError):
    """opa is absent, is not the pinned version, or did not evaluate the policy."""


def _run(cmd: list[str], stdin: str) -> tuple[int, str, str]:
    """Run one bounded command with text on stdin.

    Returns:
        (exit code, stdout, stderr).

    """
    proc = subprocess.run(
        cmd, input=stdin, capture_output=True, text=True, check=False, timeout=TIMEOUT_S
    )
    code: int = proc.returncode
    out: str = proc.stdout
    err: str = proc.stderr
    return code, out, err


def resolve(env: Mapping[str, str] | None = None) -> str:
    """Find opa and confirm it is the pinned version.

    Returns:
        the path of the opa binary.

    Raises:
        OpaUnavailableError: when no opa is found, `opa version` fails, or it is not `PINNED`.

    """
    named = (os.environ if env is None else env).get(OPA_ENV)
    path = named or shutil.which("opa")
    if not path or not Path(path).is_file():
        msg = f"opa not found at {path!r} (set {OPA_ENV} or put opa {PINNED} on PATH)"
        raise OpaUnavailableError(msg)
    code, said, _ = _run([path, "version"], "")
    versions = [ln.removeprefix(_VERSION) for ln in said.splitlines() if ln.startswith(_VERSION)]
    if code or versions != [PINNED]:
        msg = f"{path} is not opa {PINNED} (said {versions or said[:_ERR_CHARS]!r})"
        raise OpaUnavailableError(msg)
    return path


def verdicts(items: list[Json], opa: str) -> list[Json]:
    """Judge every item with the policy, in input order.

    Returns:
        one verdict per item, each {ref, level, reference_arm, residue}.

    Raises:
        OpaUnavailableError: when opa exits nonzero, or returns anything but one verdict per item.

    """
    payload: Json = {"items": items}
    stdin = json.dumps(payload)
    cmd = [opa, "eval", "--format", "json", "--stdin-input", "-d", str(POLICY), QUERY]
    code, out, err = _run(cmd, stdin)
    if code:
        msg = f"opa eval exit {code}: {(err or out)[:_ERR_CHARS]}"
        raise OpaUnavailableError(msg)
    found = verdicts_in(cast("object", json.loads(out)))
    if len(found) != len(items):
        msg = f"opa returned {len(found)} verdict(s) for {len(items)} item(s): nothing is certified"
        raise OpaUnavailableError(msg)
    return found


_VERIFY = "io.jwt.verify_eddsa(input.jws, input.jwk)"


def verify_eddsa(jws: str, jwk: str, opa: str) -> bool:
    """Say whether a compact JWS carries a valid EdDSA signature under a public JWK.

    ⚑ opa DOES THE CRYPTOGRAPHY, NO DEPENDENCY IS ADDED (W1271): the pinned opa's
    `io.jwt.verify_eddsa` was run, not remembered, against a JWS signed with an openssl key: valid
    true; the same signature over another payload, an empty signature and a zero signature false.
    The token and the key travel on stdin as data (the key a JSON string, as the builtin takes it);
    the argv is fixed, so neither ever becomes a word of the command.

    ⚑ ANYTHING BUT A CLEAN `true` IS FALSE, AND opa NOT RUNNING IS AN ERROR, NEVER A FALSE: a
    malformed token evaluates to false here, while an absent or failing opa raises, so "could not
    verify" is never read as "did not verify" by a caller that then retries differently.

    Returns:
        True only when opa evaluated the builtin to true.

    Raises:
        OpaUnavailableError: when opa exits nonzero.

    """
    payload: Json = {"jws": jws, "jwk": jwk}
    cmd = [opa, "eval", "--format", "json", "--stdin-input", _VERIFY]
    code, out, err = _run(cmd, json.dumps(payload))
    if code:
        msg = f"opa eval exit {code}: {(err or out)[:_ERR_CHARS]}"
        raise OpaUnavailableError(msg)
    doc = cast("object", json.loads(out))
    results = cast("Json", doc).get("result") if isinstance(doc, dict) else None
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        return False
    exprs = cast("Json", results[0]).get("expressions")
    if not isinstance(exprs, list) or not exprs or not isinstance(exprs[0], dict):
        return False
    return cast("Json", exprs[0]).get("value") is True


def verdicts_in(doc: object) -> list[Json]:
    """Pull the verdict list out of `opa eval --format json` output.

    Returns:
        the verdicts; empty when opa found the query undefined.

    """
    results = cast("Json", doc).get("result") if isinstance(doc, dict) else None
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        return []
    exprs = cast("Json", results[0]).get("expressions")
    if not isinstance(exprs, list) or not exprs or not isinstance(exprs[0], dict):
        return []
    value = cast("Json", exprs[0]).get("value")
    if not isinstance(value, list):
        return []
    return [cast("Json", v) for v in cast("list[object]", value) if isinstance(v, dict)]
