# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A baseline is checked against the ledger's last after-state before an apply (estate:W52, W2056).

⚑ THE CONTROLS: a baseline that equals the last `after_sha256` of its root is allowed; any other is
`hash-mismatch`; no entry is a first apply ONLY when the baseline came from the import; an edited
line is `chain-broken`; a chain cut short that is still intact, a ledger deleted with its mark left
beside it and a mark that cannot be read are `truncated-below-mark`; one root's entry never covers
another's; and each refusal is its own fixed string.
"""

from pathlib import Path

from mikemol.waldo import planjson, planledger
from mikemol.waldo.planconfig import PlanConfig

_ROOT = "zone-a"
_OTHER = "zone-b"
_ONE = "1" * 64
_TWO = "2" * 64
_THREE = "3" * 64
_PLAN = "p" * 64
_AT = "2026-10-27T00:00:00Z"
_REASONS = 4


def _config(tmp: Path) -> PlanConfig:
    return PlanConfig(
        root=tmp,
        terraform=tmp / "terraform",
        policy=tmp / "policy",
        rego_package="luthen",
        opa_pin="1.20.2",
        user_state=tmp / "user_state",
        root_state=tmp / "root_state",
        root_planned=frozenset(),
    )


def _apply(config: PlanConfig, root: str, before: str, after: str) -> Path:
    step = planledger.Transition(root, before, after, _PLAN, _AT)
    return planledger.record_after_state(config, step)


def _ok(
    config: PlanConfig, baseline: str, *, imported: bool = False, root: str = _ROOT
) -> str | None:
    return planledger.baseline_ok(config, root, baseline, imported=imported)


def test_a_baseline_equal_to_the_last_after_state_is_allowed(tmp_path: Path) -> None:
    """After two applies the last after is the one the next baseline must equal."""
    config = _config(tmp_path)
    _apply(config, _ROOT, _ONE, _TWO)
    _apply(config, _ROOT, _TWO, _THREE)
    assert _ok(config, _THREE) is None
    assert _ok(config, _TWO) == planledger.HASH_MISMATCH


def test_the_entry_is_a_lattice_edge_with_its_plan_and_applier(tmp_path: Path) -> None:
    """kind, root, before, after, plan, applier and time are all there, chained by prev."""
    config = _config(tmp_path)
    path = _apply(config, _ROOT, _ONE, _TWO)
    line = path.read_text(encoding="utf-8").splitlines()[0]
    record = planjson.parse_object(line) or {}
    assert record["kind"] == planledger.AFTER_STATE
    assert (record["root"], record["before_sha256"], record["after_sha256"]) == (_ROOT, _ONE, _TWO)
    assert (record["plan_sha256"], record["at"]) == (_PLAN, _AT)
    assert isinstance(record["applier"], dict)
    assert not record["prev"]


def test_no_entry_is_a_first_apply_only_when_the_baseline_was_imported(tmp_path: Path) -> None:
    """A missing ledger after tampering must not read as a first apply."""
    config = _config(tmp_path)
    assert _ok(config, _ONE, imported=True) is None
    assert _ok(config, _ONE, imported=False) == planledger.NO_ENTRY_NOT_IMPORTED


def test_one_roots_entry_does_not_cover_another_root(tmp_path: Path) -> None:
    """One chain per zone: zone-a's after-state says nothing about zone-b's baseline."""
    config = _config(tmp_path)
    _apply(config, _ROOT, _ONE, _TWO)
    assert _ok(config, _TWO, root=_ROOT) is None
    assert _ok(config, _TWO, root=_OTHER) == planledger.NO_ENTRY_NOT_IMPORTED
    assert _ok(config, _TWO, root=_OTHER, imported=True) is None


def test_an_edited_line_breaks_the_chain(tmp_path: Path) -> None:
    """Rewriting an earlier line breaks every later link."""
    config = _config(tmp_path)
    path = _apply(config, _ROOT, _ONE, _TWO)
    _apply(config, _ROOT, _TWO, _THREE)
    text = path.read_text(encoding="utf-8").replace(_ONE, "9" * 64, 1)
    path.write_text(text, encoding="utf-8")
    assert _ok(config, _THREE) == planledger.CHAIN_BROKEN


def test_an_intact_chain_cut_short_is_truncated_below_the_mark(tmp_path: Path) -> None:
    """Dropping the last line leaves an intact chain; the mark says it once held more."""
    config = _config(tmp_path)
    path = _apply(config, _ROOT, _ONE, _TWO)
    _apply(config, _ROOT, _TWO, _THREE)
    first = path.read_text(encoding="utf-8").splitlines()[0]
    path.write_text(first + "\n", encoding="utf-8")
    assert planledger.ledger_intact(path)
    assert _ok(config, _TWO) == planledger.TRUNCATED_BELOW_MARK


def test_a_deleted_ledger_with_its_mark_left_is_truncated_not_first(tmp_path: Path) -> None:
    """Even `imported` cannot excuse a ledger that existed and is gone."""
    config = _config(tmp_path)
    path = _apply(config, _ROOT, _ONE, _TWO)
    path.unlink()
    assert _ok(config, _TWO, imported=True) == planledger.TRUNCATED_BELOW_MARK


def test_a_replaced_last_line_is_caught_by_the_mark_digest(tmp_path: Path) -> None:
    """Same line count, different last line: the digest at the mark's position differs."""
    config = _config(tmp_path)
    path = _apply(config, _ROOT, _ONE, _TWO)
    mark = planledger.mark_path(path)
    mark.write_text('{"count": 1, "digest": "' + "0" * 64 + '"}\n', encoding="utf-8")
    assert _ok(config, _TWO) == planledger.TRUNCATED_BELOW_MARK


def test_an_unreadable_mark_is_a_refusal_and_a_missing_mark_is_not(tmp_path: Path) -> None:
    """Garbage beside the ledger is tampering; an older ledger with no mark is allowed to pass."""
    config = _config(tmp_path)
    path = _apply(config, _ROOT, _ONE, _TWO)
    mark = planledger.mark_path(path)
    mark.write_text("not json", encoding="utf-8")
    assert _ok(config, _TWO) == planledger.TRUNCATED_BELOW_MARK
    mark.unlink()
    assert _ok(config, _TWO) is None


def test_every_refusal_is_its_own_fixed_string() -> None:
    """The interlock prints which one without parsing prose."""
    reasons = {
        planledger.HASH_MISMATCH,
        planledger.NO_ENTRY_NOT_IMPORTED,
        planledger.CHAIN_BROKEN,
        planledger.TRUNCATED_BELOW_MARK,
    }
    assert len(reasons) == _REASONS
