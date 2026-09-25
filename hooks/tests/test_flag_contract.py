# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.hooks.flag_contract`: substrate's `ratchet_flags` arms, generalised.

⚑ NO NETWORK IS TOUCHED. Most arms pass no destination, so no event leaves; the two that check an
event's content reach a `curl` this suite writes under `tmp_path`, as `test_refusal_log` does.
"""

from __future__ import annotations

import json
import stat
from typing import TYPE_CHECKING, cast

from mikemol.hooks import flag_contract, refusal_log

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_KNOWN = ("--quiet", "--list")
_REFUSED = flag_contract.EXIT_REFUSED
_DEST = "http://logs.invalid/insert/jsonline"

# A caller-built pair, standing in for substrate's tenant choice: the MECHANISM is the package's.
_TENANT = flag_contract.Choice(
    flags=("--sandbox", "--live"),
    subject="This tool reaches a STORE.",
    consequence="A read that hits the wrong tenant returns plausible rows.",
    reason="unstated-tenant",
    remedy="A caller whose tenant is not the operator's to choose states it in code.",
)


def _recording_curl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Install a `curl` that records the event on its stdin, and return where it lands.

    Returns:
        the path the event is written to.

    """
    script = tmp_path / "curl"
    script.write_text(f'#!/bin/sh\ncat > "{tmp_path}/stdin"\n', encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)

    def which(_name: str) -> str:
        return str(script)

    monkeypatch.setattr(refusal_log, "which", which)
    return tmp_path / "stdin"


def _event(path: Path) -> dict[str, object]:
    """Read the event the fake curl received.

    Returns:
        the event's fields.

    """
    return cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))


def test_an_unknown_flag_is_refused_naming_the_known_set(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--queit` is refused, and the refusal names `--quiet` among the flags that exist."""
    got = flag_contract.check_flags(["gate", "--queit"], _KNOWN, "gate", destination=None)
    assert got == _REFUSED
    err = capsys.readouterr().err
    assert "--queit" in err
    assert "--quiet" in err


def test_a_known_flag_and_a_bare_path_are_accepted() -> None:
    """A known flag passes, and a bare path is not a flag at all."""
    argv = ["gate", "--quiet", "some/path.py"]
    assert flag_contract.check_flags(argv, _KNOWN, "gate", destination=None) is None


def test_a_pre_sliced_argv_still_checks_its_first_flag() -> None:
    """A caller passing `argv[1:]` still has its only flag checked: THE PRE-SLICED ARM.

    ⚑ Substrate measured `--queit` returning rc=0 from the caller that sliced before calling.
    """
    assert flag_contract.check_flags(["--queit"], _KNOWN, "gate", destination=None) == _REFUSED


def test_an_unknown_flag_event_carries_what_was_typed_and_what_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refusal's event names the typo and the known set: a near-miss, not only an error."""
    stdin = _recording_curl(tmp_path, monkeypatch)
    flag_contract.check_flags(["gate", "--queit"], _KNOWN, "gate", destination=_DEST)
    event = _event(stdin)
    assert event["reason"] == "unknown-flag"
    assert event["typed"] == "--queit"
    assert event["known"] == "--list --quiet"


def test_mutation_refuses_neither_and_both_and_accepts_one() -> None:
    """`MUTATION` refuses an unstated intent and a contradiction; exactly one passes."""
    choice = flag_contract.MUTATION
    assert flag_contract.exactly_one(["t"], "t", choice, destination=None) == _REFUSED
    both = ["t", "--apply", "--dry-run"]
    assert flag_contract.exactly_one(both, "t", choice, destination=None) == _REFUSED
    assert flag_contract.exactly_one(["t", "--apply"], "t", choice, destination=None) is None
    assert flag_contract.exactly_one(["t", "--dry-run"], "t", choice, destination=None) is None


def test_a_caller_built_choice_refuses_the_same_way_and_names_its_remedy(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A pair the caller declares (here a stand-in tenant) gets the same three cases and its remedy.

    ⚑ The MECHANISM travels; the tenant flags and remedy are the caller's policy.
    """
    assert flag_contract.exactly_one(["t"], "t", _TENANT, destination=None) == _REFUSED
    assert "states it in code" in capsys.readouterr().err
    both = ["t", "--live", "--sandbox"]
    assert flag_contract.exactly_one(both, "t", _TENANT, destination=None) == _REFUSED
    assert flag_contract.exactly_one(["t", "--live"], "t", _TENANT, destination=None) is None


def test_an_unstated_choice_emits_its_own_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Neither flag stated emits the choice's reason, so each contract is its own census."""
    stdin = _recording_curl(tmp_path, monkeypatch)
    flag_contract.exactly_one(["t"], "t", _TENANT, destination=_DEST)
    assert _event(stdin)["reason"] == "unstated-tenant"
