# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The apply ledger is a hash chain: an edit or a deletion breaks every later link (W1852, W260).

⚑ THE CONTROL IS THE UNTOUCHED CHAIN: it reads intact, and each tampering (an edited line, a
deleted first line, a line that is not an object, an unreadable file) reads as broken.
"""

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from mikemol.waldo import planjson, planledger
from mikemol.waldo.planconfig import PlanConfig

_GIT = Path("/usr/bin/git")
_NO_USER = 2_000_000_000


@dataclass
class _Done:
    returncode: int
    stdout: str
    stderr: str = ""


class _Git:
    # A Tools that has git (or not) and answers rev-parse and status from canned replies.
    def __init__(self, *, found: bool = True, head: _Done | None = None, dirty: str = "") -> None:
        self._found = found
        self._head = head or _Done(0, "abc123\n")
        self._status = _Done(0, dirty)
        self.calls: list[tuple[str, ...]] = []

    def find(self, name: str) -> Path | None:
        return _GIT if (self._found and name == "git") else None

    def run(
        self, tool: Path, *args: str, cwd: Path | None = None, stdin_text: str | None = None
    ) -> _Done:
        self.calls.append((str(tool), str(cwd), str(stdin_text), *args))
        return self._head if "rev-parse" in args else self._status

    def run_bounded(
        self, tool: Path, *args: str, cwd: Path | None = None, cpu_seconds: int
    ) -> _Done:
        return self.run(tool, *args, cwd=cwd, stdin_text=str(cpu_seconds))


def _config(tmp: Path) -> PlanConfig:
    return PlanConfig(
        root=tmp,
        terraform=tmp / "terraform",
        policy=tmp / "policy",
        rego_package="luthen",
        opa_pin="1.20.2",
        user_state=tmp / "user_state",
        root_state=tmp / "root_state",
        root_planned=frozenset({"host"}),
    )


def _two(config: PlanConfig) -> Path:
    planledger.append_ledger(config, "stage2", {"n": 1})
    return planledger.append_ledger(config, "stage2", {"n": 2})


def test_the_ledger_lives_beside_the_roots_verdicts(tmp_path: Path) -> None:
    """A root-planned root's ledger is in the root state, any other root's in the user's."""
    config = _config(tmp_path)
    assert planledger.ledger_path(config, "host") == tmp_path / "root_state" / "apply-ledger.jsonl"
    assert planledger.ledger_path(config, "stage2") == (
        tmp_path / "user_state" / "apply-ledger.jsonl"
    )


def test_each_entry_carries_the_hash_of_the_line_before_it(tmp_path: Path) -> None:
    """The first entry's prev is empty, the second's is the sha256 of the first line."""
    path = _two(_config(tmp_path))
    first, second = path.read_text(encoding="utf-8").splitlines()
    digest = hashlib.sha256(first.encode()).hexdigest()
    assert not (planjson.parse_object(first) or {})["prev"]
    assert (planjson.parse_object(second) or {})["prev"] == digest
    assert planledger.ledger_intact(path)


def test_a_third_entry_chains_to_the_second_not_the_first(tmp_path: Path) -> None:
    """The link is to the LAST line, so each entry names its immediate predecessor."""
    config = _config(tmp_path)
    path = _two(config)
    planledger.append_ledger(config, "stage2", {"n": 3})
    lines = path.read_text(encoding="utf-8").splitlines()
    digest = hashlib.sha256(lines[1].encode()).hexdigest()
    assert (planjson.parse_object(lines[2]) or {})["prev"] == digest
    assert planledger.ledger_intact(path)


def test_an_edited_line_breaks_the_chain(tmp_path: Path) -> None:
    """Rewriting the first line changes its hash, so the second entry's prev no longer matches."""
    path = _two(_config(tmp_path))
    lines = path.read_text(encoding="utf-8").splitlines()
    forged: dict[str, object] = {"n": 99, "prev": ""}
    lines[0] = json.dumps(forged, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert not planledger.ledger_intact(path)


def test_a_deleted_first_line_breaks_the_chain(tmp_path: Path) -> None:
    """The remaining entry names a previous line that is gone."""
    path = _two(_config(tmp_path))
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text(lines[1] + "\n", encoding="utf-8")
    assert not planledger.ledger_intact(path)


def test_a_line_that_is_not_an_object_or_a_missing_file_is_broken(tmp_path: Path) -> None:
    """Garbage in the chain and an unreadable ledger both read as not intact."""
    path = _two(_config(tmp_path))
    path.write_text("not json\n", encoding="utf-8")
    assert not planledger.ledger_intact(path)
    assert not planledger.ledger_intact(tmp_path / "never.jsonl")


def test_an_empty_ledger_has_no_last_line_and_is_vacuously_intact(tmp_path: Path) -> None:
    """The digest of nothing is empty, and a file of no lines has no broken link."""
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    assert not planledger.last_line_digest(empty)
    assert not planledger.last_line_digest(tmp_path / "never.jsonl")
    assert planledger.ledger_intact(empty)


def test_the_applier_is_account_names_and_falls_back_to_the_uid() -> None:
    """The login by uid, sudo's user as given, and `uid<N>` for a uid with no passwd entry."""
    assert planledger.applier(os.getuid(), "someone")["sudo_user"] == "someone"
    assert planledger.applier(os.getuid(), "")["user"]
    assert planledger.applier(_NO_USER, "")["user"] == f"uid{_NO_USER}"


def test_the_current_applier_is_this_process_and_its_sudo_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real uid's login, and sudo's invoking user from the environment (empty if unset)."""
    monkeypatch.setenv("SUDO_USER", "invoker")
    assert planledger.current_applier() == planledger.applier(os.getuid(), "invoker")
    monkeypatch.delenv("SUDO_USER")
    assert not planledger.current_applier()["sudo_user"]


def test_the_commit_and_whether_the_apply_inputs_are_dirty(tmp_path: Path) -> None:
    """HEAD from rev-parse, dirty from a porcelain status over terraform and policy."""
    config = _config(tmp_path)
    clean = planledger.repo_commit(_Git(), config)
    assert clean == {"commit": "abc123", "dirty": False}
    assert planledger.repo_commit(_Git(dirty=" M terraform/main.tf\n"), config)["dirty"] is True
    git = _Git()
    planledger.repo_commit(git, config)
    assert git.calls[-1][-3:] == ("--", "terraform", "policy")


def test_without_git_or_a_head_the_commit_is_unknown_not_clean(tmp_path: Path) -> None:
    """No git, or a failing rev-parse, gives an empty commit and an unknown (None) dirty flag."""
    config = _config(tmp_path)
    assert planledger.repo_commit(_Git(found=False), config) == {"commit": "", "dirty": None}
    broken = planledger.repo_commit(_Git(head=_Done(128, "", "no repo")), config)
    assert broken == {"commit": "", "dirty": None}
