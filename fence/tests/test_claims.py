# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the claim verbs: a claim that outlives its command, owned by a named process.

W911. ⚑ THE CLAIM THAT LANDS AND LISTS IS THE POSITIVE CONTROL: the second taker's refusal, the
owner-only release and the dead owner's reaping only mean something beside a claim that is held,
shown by `claims`, and taken again once it is released.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from mikemol.fence import admit, claims, membudget_cli

if TYPE_CHECKING:
    from pathlib import Path

LABEL = "claim:label:touch:mtools:bazel"
SESSION = os.getpid()
PEER = os.getppid()
TOTAL = 1000
EXIT_REFUSED = 3
EXIT_USAGE = 2
AGE = 42


def _total() -> int:
    """Return the injected default total.

    Returns:
        `TOTAL`.

    """
    return TOTAL


def _cli(ledger: Path, *argv: str) -> int:
    """Run one membudget verb over `ledger` with an injected default total.

    Returns:
        the verb's exit code.

    """
    env = {"MEMBUDGET_FILE": str(ledger), "HOME": str(ledger.parent), "PATH": os.environ["PATH"]}
    ctx = membudget_cli.Context(env=env, host=admit.Host(default_total=_total))
    return membudget_cli.main(list(argv), ctx)


@pytest.fixture()
def ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a ledger path with no inherited parent lease.

    Returns:
        the path, not yet created.

    """
    monkeypatch.delenv(admit.ENV_PARENT, raising=False)
    return tmp_path / "budget.cotype"


def _dead_pid() -> int:
    """Return the pid of a process that has run and exited.

    Returns:
        a pid no process holds.

    """
    pid = os.posix_spawnp("true", ["true"], dict(os.environ))
    os.waitpid(pid, 0)
    return pid


def test_a_claim_is_held_and_listed_with_its_owner(
    ledger: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: the lease id is printed and `claims` names the label, the owner and the id."""
    assert _cli(ledger, "claim", LABEL, "--owner-pid", str(SESSION)) == 0
    lease_id = capsys.readouterr().out.strip()
    assert _cli(ledger, "claims") == 0
    listed = capsys.readouterr().out
    assert LABEL in listed
    assert f"owner={admit.owner_of(SESSION)}" in listed
    assert f"id={lease_id}" in listed


def test_a_second_taker_is_refused_and_told_who_holds_it(
    ledger: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 3, the holder's owner and lease id named, and the first claim untouched."""
    assert _cli(ledger, "claim", LABEL, "--owner-pid", str(SESSION)) == 0
    held = capsys.readouterr().out.strip()
    assert _cli(ledger, "claim", LABEL, "--owner-pid", str(PEER)) == EXIT_REFUSED
    said = capsys.readouterr().err
    assert admit.owner_of(SESSION) in said
    assert held in said


def test_other_labels_do_not_exclude_each_other(ledger: Path) -> None:
    """Two different touches tags are two claims."""
    assert _cli(ledger, "claim", LABEL, "--owner-pid", str(SESSION)) == 0
    assert _cli(ledger, "claim", "claim:label:touch:mtools:typing", "--owner-pid", str(PEER)) == 0


def test_path_claims_compare_by_realpath(ledger: Path, tmp_path: Path) -> None:
    """Two spellings of one path are one claim."""
    target = tmp_path / "work"
    target.mkdir()
    assert _cli(ledger, "claim", f"claim:path:{target}", "--owner-pid", str(SESSION)) == 0
    spelled = f"claim:path:{target}//../work/"
    assert _cli(ledger, "claim", spelled, "--owner-pid", str(PEER)) == EXIT_REFUSED


def test_only_the_owner_releases_and_then_the_claim_is_free(ledger: Path) -> None:
    """A non-owner's release is refused and changes nothing; the owner's frees the label."""
    assert _cli(ledger, "claim", LABEL, "--owner-pid", str(SESSION)) == 0
    assert _cli(ledger, "release", LABEL, "--owner-pid", str(PEER)) == EXIT_REFUSED
    assert _cli(ledger, "claim", LABEL, "--owner-pid", str(PEER)) == EXIT_REFUSED
    assert _cli(ledger, "release", LABEL, "--owner-pid", str(SESSION)) == 0
    assert _cli(ledger, "claim", LABEL, "--owner-pid", str(PEER)) == 0


def test_a_dead_owners_claim_is_reaped(ledger: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A lease whose owner is gone is not listed and does not exclude the next taker."""
    assert _cli(ledger, "init", str(TOTAL)) == 0
    ghost = admit.Lease("deadbeef0000", 0, "999999999:1", 1, admit.NO_PARENT, LABEL)
    ledger.write_text(ledger.read_text(encoding="utf-8") + ghost.line() + "\n", encoding="utf-8")
    capsys.readouterr()
    assert _cli(ledger, "claims") == 0
    assert capsys.readouterr().out == "(no claims)\n"
    assert _cli(ledger, "claim", LABEL, "--owner-pid", str(SESSION)) == 0


def test_a_claim_for_a_process_that_is_not_running_is_refused(
    ledger: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """It would be born unowned; the refusal says the owner is not running and nothing is held."""
    assert _cli(ledger, "claim", LABEL, "--owner-pid", str(_dead_pid())) == EXIT_REFUSED
    assert "is not running" in capsys.readouterr().err
    assert _cli(ledger, "claim", LABEL, "--owner-pid", str(SESSION)) == 0


def test_a_claim_costs_no_budget(ledger: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The lease is zero units: status still shows nothing leased."""
    assert _cli(ledger, "claim", LABEL, "--owner-pid", str(SESSION)) == 0
    capsys.readouterr()
    assert _cli(ledger, "status") == 0
    assert "top-level-leased=0MB" in capsys.readouterr().out


def test_the_default_owner_is_the_callers_parent(
    ledger: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --owner-pid the claim belongs to the session, not to the short command."""
    assert _cli(ledger, "claim", LABEL) == 0
    capsys.readouterr()
    assert _cli(ledger, "claims") == 0
    assert f"owner={admit.owner_of(PEER)}" in capsys.readouterr().out


@pytest.mark.parametrize(
    "argv",
    [
        ["claim"],
        ["claim", "not-a-claim"],
        ["claim", LABEL, "--owner-pid"],
        ["claim", LABEL, "--owner-pid", "abc"],
        ["claim", LABEL, "extra"],
        ["release"],
        ["claims", "extra"],
    ],
)
def test_malformed_invocations_exit_2(ledger: Path, argv: list[str]) -> None:
    """A missing or non-claim label, a bad pid and stray operands are usage errors."""
    assert _cli(ledger, *argv) == EXIT_USAGE


def test_the_listing_gives_each_claims_age_from_its_epoch() -> None:
    """Age is the given clock minus the lease's epoch, never negative; non-claims are skipped."""
    claim = admit.Lease("aaaaaaaaaaaa", 0, "1:1", 100, admit.NO_PARENT, LABEL)
    plain = admit.Lease("bbbbbbbbbbbb", 5, "1:1", 100, admit.NO_PARENT, "build")
    snap = admit.parse(f"TOTAL_MB {TOTAL}\n{claim.line()}\n{plain.line()}\n")
    assert claims.listing(snap, 100 + AGE) == [f"{LABEL} owner=1:1 id=aaaaaaaaaaaa age={AGE}s"]
    assert claims.listing(snap, 50) == [f"{LABEL} owner=1:1 id=aaaaaaaaaaaa age=0s"]
