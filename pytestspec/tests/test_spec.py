# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Case data and the verdict judgment, without pytest collection."""

from pathlib import Path

import pytest

from mikemol.pytestspec.spec import SpecDataError, Verdict, cases_path, judge, load_cases


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
