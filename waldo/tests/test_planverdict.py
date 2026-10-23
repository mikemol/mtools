# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Verdict custody: where a verdict lives, who wrote it, what voids it (W1850, from luthen W261).

⚑ EVERY FORGERY IS REFUSED AND THE CONTROL ADMITS: a host record copied into the user's directory,
a root directory the planner can write, a record of another owner, an edited record and a changed
policy are each refused with their reason, while the untouched record is admitted.
"""

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

from mikemol.waldo import planjson, planverdict
from mikemol.waldo.planconfig import PlanConfig

_PLAN = b"the plan bytes"
_DIGEST = hashlib.sha256(_PLAN).hexdigest()


def _config(tmp: Path) -> PlanConfig:
    policy = tmp / "policy"
    policy.mkdir()
    (policy / "plan.rego").write_text("package luthen.plan\n", encoding="utf-8")
    return PlanConfig(
        root=tmp,
        terraform=tmp / "terraform",
        policy=policy,
        rego_package="luthen",
        opa_pin="1.20.2",
        user_state=tmp / "user_state",
        root_state=tmp / "root_state",
        root_planned=frozenset({"host"}),
        trusted_uid=os.getuid(),
    )


def _plan(tmp: Path) -> Path:
    path = tmp / "p.tfplan"
    path.write_bytes(_PLAN)
    return path


def _put(state: Path, doc: dict[str, object]) -> Path:
    sealed: dict[str, object] = {**doc, "seal": planverdict.seal_of(doc)}
    record = planverdict.verdict_path(state, _DIGEST)
    record.parent.mkdir(parents=True, exist_ok=True)
    record.parent.chmod(0o755)
    record.write_text(json.dumps(sealed), encoding="utf-8")
    return record


def _admitted(config: PlanConfig, root: str) -> dict[str, object]:
    return {"exit": 0, "root": root, "policy_sha256": planverdict.policy_digest(config)}


def test_an_untouched_user_record_is_admitted(tmp_path: Path) -> None:
    """The control: a sealed passing record under the current policy is returned."""
    config = _config(tmp_path)
    _put(config.user_state, _admitted(config, "stage2"))
    got = planverdict.load_verdict(config, _plan(tmp_path))
    assert isinstance(got, dict)
    assert got["root"] == "stage2"


def test_an_untouched_host_record_in_the_root_directory_is_admitted(tmp_path: Path) -> None:
    """The control for the root-planned root: the record in the trusted directory is admitted."""
    config = _config(tmp_path)
    assert config.root_state is not None
    _put(config.root_state, _admitted(config, "host"))
    assert isinstance(planverdict.load_verdict(config, _plan(tmp_path)), dict)


def test_a_host_record_copied_into_the_user_directory_is_refused(tmp_path: Path) -> None:
    """The planner copying a host record into its own directory does not admit the plan."""
    config = _config(tmp_path)
    _put(config.user_state, _admitted(config, "host"))
    got = planverdict.load_verdict(config, _plan(tmp_path))
    assert isinstance(got, str)
    assert "root-owned directory" in got


def test_a_root_directory_the_planner_can_write_is_refused(tmp_path: Path) -> None:
    """A state directory with a group or other write bit is not a root state directory."""
    config = _config(tmp_path)
    assert config.root_state is not None
    record = _put(config.root_state, _admitted(config, "host"))
    record.parent.chmod(0o777)
    got = planverdict.load_verdict(config, _plan(tmp_path))
    assert isinstance(got, str)
    assert "root-only directory" in got


def test_a_record_of_another_owner_is_refused(tmp_path: Path) -> None:
    """With a different trusted uid the same files are not the trusted user's."""
    config = _config(tmp_path)
    assert config.root_state is not None
    _put(config.root_state, _admitted(config, "host"))
    other = replace(config, trusted_uid=os.getuid() + 1)
    got = planverdict.load_verdict(other, _plan(tmp_path))
    assert isinstance(got, str)
    assert "root-only directory" in got


def test_an_edited_record_fails_its_seal(tmp_path: Path) -> None:
    """Flipping a denied record's exit to 0 without re-sealing does not admit it."""
    config = _config(tmp_path)
    record = _put(config.user_state, {**_admitted(config, "stage2"), "exit": 1})
    edited = planjson.parse_object(record.read_text(encoding="utf-8")) or {}
    edited["exit"] = 0
    record.write_text(json.dumps(edited), encoding="utf-8")
    got = planverdict.load_verdict(config, _plan(tmp_path))
    assert isinstance(got, str)
    assert "seal" in got


def test_a_denied_verdict_is_not_admitted(tmp_path: Path) -> None:
    """A correctly sealed record with a non-zero exit is a refusal, not an admission."""
    config = _config(tmp_path)
    _put(config.user_state, {**_admitted(config, "stage2"), "exit": 1})
    got = planverdict.load_verdict(config, _plan(tmp_path))
    assert isinstance(got, str)
    assert "was not admitted (exit 1)" in got


def test_a_changed_policy_voids_the_verdict(tmp_path: Path) -> None:
    """A verdict recorded under another policy digest is not admitted."""
    config = _config(tmp_path)
    _put(config.user_state, _admitted(config, "stage2"))
    (config.policy / "plan.rego").write_text("package luthen.plan\n# changed\n", encoding="utf-8")
    got = planverdict.load_verdict(config, _plan(tmp_path))
    assert isinstance(got, str)
    assert "policy changed" in got


def test_a_planfile_whose_bytes_moved_has_no_verdict(tmp_path: Path) -> None:
    """The record is keyed by the planfile's hash, so moved bytes find nothing."""
    config = _config(tmp_path)
    _put(config.user_state, _admitted(config, "stage2"))
    moved = _plan(tmp_path)
    moved.write_bytes(b"moved")
    got = planverdict.load_verdict(config, moved)
    assert isinstance(got, str)
    assert "never judged here" in got


def test_an_unreadable_planfile_is_a_reason_not_a_crash(tmp_path: Path) -> None:
    """A planfile that is not there says so."""
    got = planverdict.load_verdict(_config(tmp_path), tmp_path / "nope.tfplan")
    assert isinstance(got, str)
    assert "is not readable" in got


def test_the_digest_ignores_rego_tests_only_and_follows_declared_data(tmp_path: Path) -> None:
    """A *_test.rego change does not move the digest, a rule or a declared data file does."""
    config = _config(tmp_path)
    (tmp_path / "data.json").write_text("{}", encoding="utf-8")
    declared = {"limits": "data.json"}
    base = planverdict.policy_digest(config, declared)
    (config.policy / "x_test.rego").write_text("t", encoding="utf-8")
    assert planverdict.policy_digest(config, declared) == base
    (tmp_path / "data.json").write_text('{"k": 1}', encoding="utf-8")
    assert planverdict.policy_digest(config, declared) != base
    assert planverdict.policy_digest(config) != planverdict.policy_digest(config, declared)


def test_with_custody_off_a_host_record_in_the_user_directory_is_a_user_record(
    tmp_path: Path,
) -> None:
    """The consumer's explicit choice: no root directory, so the root-planned rule is off."""
    config = replace(_config(tmp_path), root_custody=False)
    _put(config.user_state, _admitted(config, "host"))
    assert isinstance(planverdict.load_verdict(config, _plan(tmp_path)), dict)
