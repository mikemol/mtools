# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pinned opa evaluator: output parsing, refusal of a wrong opa, and what it sends opa.

W1006. ⚑ THE EVALUATOR WAS ONLY REACHED THROUGH A REAL opa, so a declared defect in it (stdin
not passed, a failed eval read as a verdict, an error cut wrong) was never exercised. A scripted
stand-in records what it was sent and answers what the test says.
"""

from pathlib import Path

import pytest

from mikemol.pytestspec import opa
from mikemol.pytestspec.spec import Case, SpecDataError, Verdict

_ADMITTED = '{"result": [{"expressions": [{"value": {"deny": [], "withheld": []}}]}]}'
_CASE: Case = {"case": "c"}
_CUT = 500
_PIN = "Version: 1.20.2"


def _fake_opa(tmp_path: Path, version: str) -> None:
    """Put an `opa` on PATH whose `version` prints the given version and nothing else."""
    script = tmp_path / "opa"
    script.write_text(f"#!/bin/sh\necho 'Version: {version}'\n", encoding="utf-8")
    script.chmod(0o700)


def _scripted_opa(
    tmp_path: Path, *, out: str = "", err: str = "", code: int = 0, version: str = _PIN
) -> Path:
    """Write an `opa` that answers `version`, and on `eval` records argv and stdin then replies.

    Returns:
        the script's path; `args` and `stdin` appear beside it once an eval has run.

    """
    (tmp_path / "out").write_text(out, encoding="utf-8")
    (tmp_path / "err").write_text(err, encoding="utf-8")
    script = tmp_path / "scripted-opa"
    lines = [
        "#!/bin/sh",
        f"if [ \"$1\" = version ]; then echo '{version}'; exit 0; fi",
        f"printf '%s\\n' \"$@\" > '{tmp_path}/args'",
        f"cat > '{tmp_path}/stdin'",
        f"cat '{tmp_path}/out'",
        f"cat '{tmp_path}/err' >&2",
        f"exit {code}",
    ]
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    script.chmod(0o700)
    return script


def _spec(tmp_path: Path) -> Path:
    """Write a spec in package `a.b`.

    Returns:
        its path.

    """
    spec = tmp_path / "s.rego"
    spec.write_text("package a.b\n", encoding="utf-8")
    return spec


def test_an_admitted_result_carries_no_deny_or_withheld() -> None:
    """Empty `deny` and `withheld` sets parse to the admitted verdict."""
    assert opa.verdict_from(_ADMITTED) == Verdict()


def test_deny_messages_parse_sorted() -> None:
    """A Rego set has no order, so its messages are sorted before comparison."""
    out = '{"result": [{"expressions": [{"value": {"deny": ["b", "a"]}}]}]}'
    assert opa.verdict_from(out) == Verdict(deny=("a", "b"))


def test_withheld_messages_are_read_from_their_own_key() -> None:
    """The withheld half is the `withheld` set, not a copy of `deny`."""
    out = '{"result": [{"expressions": [{"value": {"deny": [], "withheld": ["w2", "w1"]}}]}]}'
    assert opa.verdict_from(out) == Verdict(withheld=("w1", "w2"))


def test_a_set_that_is_not_a_list_reads_as_no_messages() -> None:
    """A string where a set belongs is not iterated into characters; it reads as none."""
    out = '{"result": [{"expressions": [{"value": {"deny": "ab"}}]}]}'
    assert opa.verdict_from(out) == Verdict()


def test_empty_result_is_withheld_not_admitted() -> None:
    """An empty result object (the package is undefined) is WITHHELD: nothing was measured."""
    verdict = opa.verdict_from("{}")
    assert verdict.withheld
    assert not verdict.deny


@pytest.mark.parametrize(
    "text",
    [
        '{"result": []}',
        '{"result": [{"expressions": []}]}',
        '{"result": [1]}',
        '{"result": {}}',
        "[]",
    ],
)
def test_a_document_of_the_wrong_shape_is_withheld_and_never_raises(text: str) -> None:
    """Every step of the walk to the package document tolerates a value of the wrong shape."""
    verdict = opa.verdict_from(text)
    assert verdict.withheld
    assert not verdict.deny


def test_a_package_without_deny_is_withheld() -> None:
    """A package document with no `deny` key (no rule could deny) is WITHHELD, not admitted."""
    verdict = opa.verdict_from('{"result": [{"expressions": [{"value": {}}]}]}')
    assert verdict.withheld
    assert not verdict.deny


def test_package_is_read_from_the_spec(tmp_path: Path) -> None:
    """The query path is the spec's own `package` line."""
    spec = tmp_path / "s.rego"
    spec.write_text("# c\npackage pycodemod.guarded\n", encoding="utf-8")
    assert opa.package_of(spec) == "pycodemod.guarded"


def test_spec_without_package_is_refused(tmp_path: Path) -> None:
    """A spec with no `package` line cannot be queried, and says so."""
    spec = tmp_path / "s.rego"
    spec.write_text("deny contains 1 if true\n", encoding="utf-8")
    with pytest.raises(SpecDataError, match="no `package` line"):
        opa.package_of(spec)


def test_absent_opa_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With no opa on PATH, resolution FAILS; it never falls through to a skip."""
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(opa.OpaUnavailableError, match="not found on PATH"):
        opa.resolve()


def test_wrong_version_opa_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An opa that is not the pinned version is a different checker, and is refused."""
    _fake_opa(tmp_path, "0.0.1")
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(opa.OpaUnavailableError, match="not the pinned"):
        opa.resolve()


def test_pinned_version_opa_is_accepted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The pinned version resolves to its absolute path (the P-arm of the version check)."""
    _fake_opa(tmp_path, opa.PINNED)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert opa.resolve() == str(tmp_path / "opa")


def test_an_opa_whose_version_command_fails_is_refused_though_it_prints_the_pin(
    tmp_path: Path,
) -> None:
    """The exit status is read as well as the Version line: a pin printed on a failure is no pin."""
    script = tmp_path / "failing-opa"
    script.write_text("#!/bin/sh\necho 'Version: 1.20.2'\nexit 3\n", encoding="utf-8")
    script.chmod(0o700)
    with pytest.raises(opa.OpaUnavailableError, match="exit 3"):
        opa.resolve(str(script))


def test_a_version_line_with_no_value_is_refused_not_indexed(tmp_path: Path) -> None:
    """`Version:` with nothing after it is no version, and is refused rather than IndexError."""
    script = _scripted_opa(tmp_path, version="Version:")
    with pytest.raises(opa.OpaUnavailableError, match="no Version line"):
        opa.resolve(str(script))


def test_the_case_goes_on_stdin_and_the_spec_package_is_queried(tmp_path: Path) -> None:
    """The argv is: format, stdin input, the spec, each extra data path, then the package query."""
    spec = _spec(tmp_path)
    shared = tmp_path / "shared.rego"
    script = _scripted_opa(tmp_path, out=_ADMITTED)
    evaluate = opa.evaluator(str(script), (shared,))
    assert evaluate(spec, _CASE) == Verdict()
    assert (tmp_path / "stdin").read_text(encoding="utf-8") == '{"case": "c"}'
    args = (tmp_path / "args").read_text(encoding="utf-8").splitlines()
    assert args == [
        "eval",
        "--format",
        "json",
        "--stdin-input",
        "--data",
        str(spec),
        "--data",
        str(shared),
        "data.a.b",
    ]


def test_a_failed_eval_reports_stderr_on_one_line_cut_short(tmp_path: Path) -> None:
    """A nonzero exit raises naming stderr (not stdout), newlines folded and the length cut."""
    script = _scripted_opa(tmp_path, out="ignored", err="bad\nthing " + "x" * 600, code=2)
    evaluate = opa.evaluator(str(script))
    with pytest.raises(opa.OpaUnavailableError) as info:
        evaluate(_spec(tmp_path), _CASE)
    text = str(info.value)
    prefix = "opa eval exit 2: "
    assert text.startswith(prefix + "bad thing x")
    assert "\n" not in text
    assert "ignored" not in text
    assert len(text) == len(prefix) + _CUT


def test_a_failed_eval_with_an_empty_stderr_reports_stdout(tmp_path: Path) -> None:
    """A compile error opa prints on stdout, with stderr empty, still reaches the failure."""
    script = _scripted_opa(tmp_path, out="rego_type_error", code=2)
    evaluate = opa.evaluator(str(script))
    with pytest.raises(opa.OpaUnavailableError) as info:
        evaluate(_spec(tmp_path), _CASE)
    assert str(info.value) == "opa eval exit 2: rego_type_error"
