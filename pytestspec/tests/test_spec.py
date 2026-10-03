# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Case data and the verdict judgment, without pytest collection."""

from pathlib import Path

import pytest

from mikemol.pytestspec.spec import (
    Case,
    Expect,
    SpecDataError,
    Verdict,
    cases_path,
    expectation,
    judge,
    load_cases,
)

_S0 = Expect(deny=frozenset({"S0"}))
_W = Expect(withheld=frozenset({"W"}))


def test_expected_deny_passes_when_exactly_those_rules_deny() -> None:
    """With expect, a deny from exactly the expected rule ids passes, matched before the `:`."""
    assert judge(Verdict(deny=("S0: refused", "S0: again")), _S0) is None


def test_expected_deny_fails_when_the_case_is_admitted() -> None:
    """An expected deny that never fires fails, naming the rule that did not refuse."""
    assert judge(Verdict(), _S0) == "DENY MISMATCH: missing S0; unexpected none"


def test_expected_deny_fails_on_an_extra_rule() -> None:
    """A deny from a rule not expected fails; the id is exact, so S10 is not S1."""
    failure = judge(Verdict(deny=("S1: a", "S10: b")), Expect(deny=frozenset({"S1"})))
    assert failure == "DENY MISMATCH: missing none; unexpected S10"


def test_withheld_never_satisfies_an_expected_deny() -> None:
    """A withheld case fails though a deny is expected: a rule that did not run did not refuse."""
    failure = judge(Verdict(deny=("S0: x",), withheld=("W: no input",)), _S0)
    assert failure == "WITHHELD MISMATCH: missing none; unexpected W"


def test_expected_withhold_passes_when_exactly_those_rules_withhold() -> None:
    """W381: a could-not-measure arm passes on exactly its withheld ids, with no deny."""
    assert judge(Verdict(withheld=("W: qmllint is null",)), _W) is None


def test_a_deny_fails_a_case_expecting_only_a_withhold() -> None:
    """An omitted `deny` means none: a deny beside the expected withhold fails, naming it."""
    failure = judge(Verdict(deny=("L2: x",), withheld=("W: y",)), _W)
    assert failure == "DENY MISMATCH: missing none; unexpected L2"


def test_both_sets_mismatched_name_both() -> None:
    """When deny and withheld both differ, the failure names each, so neither is hidden."""
    failure = judge(Verdict(deny=("L2: x",)), _W)
    assert failure == (
        "DENY MISMATCH: missing none; unexpected L2 | WITHHELD MISMATCH: missing W; unexpected none"
    )


def test_expect_is_read_from_the_case() -> None:
    """`expect` holds deny and withheld id sets; a case without `expect` is admitted-only."""
    read = expectation("c", {"case": "c", "expect": {"deny": ["S0", " L2 "], "withheld": ["W"]}})
    assert read == Expect(deny=frozenset({"S0", "L2"}), withheld=frozenset({"W"}))
    assert expectation("c", {"case": "c", "expect": {"withheld": ["W"]}}) == _W
    assert expectation("c", {"case": "c"}) is None


@pytest.mark.parametrize(
    "expect",
    [
        "denied",
        {"deny": []},
        {"deny": "S0"},
        {"deny": [""]},
        {"admit": ["S0"]},
        {"withheld": []},
        {"deny": [], "withheld": []},
        {"deny": ["S0"], "impl": []},
        {"deny": ["S0"], "impl": "reference"},
        {"deny": ["S0"], "impl": [""]},
        {"impl": ["reference"]},
    ],
)
def test_malformed_expect_is_a_data_error(expect: object) -> None:
    """A bare "denied", no id at all, an unknown key, or a non-id entry is refused."""
    with pytest.raises(SpecDataError, match="case c: "):
        expectation("c", {"case": "c", "expect": expect})


_SCOPED: Case = {"case": "c", "expect": {"deny": ["S0"], "impl": ["reference"]}}


def test_scoped_expect_holds_only_under_its_impl() -> None:
    """W508: an expect scoped by `impl` applies under a named impl only; elsewhere it is absent."""
    assert expectation("c", _SCOPED, "reference") == _S0
    assert expectation("c", _SCOPED, "subject") is None
    assert expectation("c", _SCOPED) is None


def test_unscoped_expect_holds_under_every_impl() -> None:
    """An expect with no `impl` binds as-written and under every implementation alike."""
    case: Case = {"case": "c", "expect": {"deny": ["S0"]}}
    assert expectation("c", case, "subject") == _S0
    assert expectation("c", case) == _S0


def test_cases_sit_beside_the_spec() -> None:
    """`guarded.rego` reads `guarded.cases.json` in the same directory."""
    assert cases_path(Path("specs/guarded.rego")) == Path("specs/guarded.cases.json")


def test_admitted_verdict_passes() -> None:
    """Nothing denied and nothing withheld is the only verdict that passes."""
    assert judge(Verdict()) is None


def test_deny_fails_with_its_messages() -> None:
    """A deny fails, carrying every deny message."""
    assert judge(Verdict(deny=("a", "b"))) == "DENIED: a; b"


def test_withheld_fails_as_unmeasured() -> None:
    """A withheld case FAILS as UNMEASURED; it is never a pass."""
    failure = judge(Verdict(withheld=("no rule",)))
    assert failure is not None
    assert failure.startswith("UNMEASURED")


def test_deny_is_reported_before_withheld() -> None:
    """A case both denied and withheld reports the deny, which is the finding."""
    assert judge(Verdict(deny=("d",), withheld=("w",))) == "DENIED: d"


def test_cases_load_in_file_order(tmp_path: Path) -> None:
    """Each record's `case` names it, and file order is kept."""
    spec = tmp_path / "s.rego"
    cases_path(spec).write_text('[{"case": "b"}, {"case": "a", "x": 1}]', encoding="utf-8")
    assert load_cases(spec) == [("b", {"case": "b"}), ("a", {"case": "a", "x": 1})]


@pytest.mark.parametrize(
    ("text", "needle"),
    [
        (None, "no case data"),
        ("{", "not JSON"),
        ("[]", "non-empty JSON list"),
        ("[1]", "not an object"),
        ('[{"x": 1}]', "no string `case`"),
    ],
)
def test_bad_case_data_is_refused(tmp_path: Path, text: str | None, needle: str) -> None:
    """Absent, non-JSON, empty, or unnamed case data raises; it never loads as zero cases."""
    spec = tmp_path / "s.rego"
    if text is not None:
        cases_path(spec).write_text(text, encoding="utf-8")
    with pytest.raises(SpecDataError, match=needle):
        load_cases(spec)
