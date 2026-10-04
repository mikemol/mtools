# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `hook_grid`: the hand-transcribed //:hook list must agree with MODULE.bazel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.gatecheck import hook_grid

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_MODULE = """\
bib.project(name = "paperkit_a", adequacy = True, emerge = True)
bib.project(name = "paperkit_b")
bib.project(flags = "no name here")
something_else(name = "paperkit_ignored", emerge = True)
"""

_MEMBERS = (
    '"@paperkit_a//:gate", "@paperkit_a//:adequacy", "@paperkit_a//:cohere",'
    ' "@paperkit_a//:decisions", "@paperkit_b//:gate", "//canary:canary"'
)

_EXEMPT_REPOS = ("paperkit_setup", "paperkit_report", "paperkit_image")


def _build(members: str = _MEMBERS) -> str:
    return (
        'test_suite(\n    name = "hook",\n    tests = [\n'
        "        # a wiki-style ref [[place-by-ownership]] carries a close bracket\n"
        f"        {members},\n"
        "    ],\n)\n"
    )


def test_declared_derives_the_emitted_kinds_from_each_projects_flags() -> None:
    """`gate` is unconditional; `adequacy` and `emerge` add kinds; a nameless tag is skipped."""
    assert hook_grid.declared(_MODULE) == {
        "paperkit_a": {"gate", "adequacy", "cohere", "decisions"},
        "paperkit_b": {"gate"},
    }


def test_transcribed_counts_brackets_so_a_comment_ref_does_not_end_the_list() -> None:
    """A `]` inside a comment is not the end: every quoted label after it is still scraped."""
    assert hook_grid.transcribed(_build()) == {
        "@paperkit_a//:gate",
        "@paperkit_a//:adequacy",
        "@paperkit_a//:cohere",
        "@paperkit_a//:decisions",
        "@paperkit_b//:gate",
        "//canary:canary",
    }


def test_transcribed_keeps_only_labels_and_only_the_hook_suite() -> None:
    """A quoted non-label is dropped, and a `tests = [` before the hook's own name is not read."""
    build = (
        'test_suite(name = "other", tests = ["//wrong:one"])\n'
        'test_suite(name = "hook", tests = ["//a:b", "not-a-label", "@r//:c"])\n'
    )
    assert hook_grid.transcribed(build) == {"//a:b", "@r//:c"}


def test_transcribed_is_empty_when_there_is_no_hook_list() -> None:
    """No `tests = [` after the hook's name: an empty set, which `check` reports."""
    assert hook_grid.transcribed('test_suite(name = "hook")\n') == set()


def test_a_matching_grid_passes_and_summarises_with_its_exemptions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every emitted target is in the hook: exit 0, counts, and each exemption listed with why."""
    exempt = {"@paperkit_b//:gate": "because"}
    build = _build(_MEMBERS.replace('"@paperkit_b//:gate", ', ""))
    assert hook_grid.check(_MODULE, build, exempt) == 0
    out = capsys.readouterr().out
    assert "2 project(s), 5 emitted target(s), 1 declared exemption(s)" in out
    assert "1 harness member; 5 transcribed" in out
    assert "  exempt  @paperkit_b//:gate\n          because\n" in out


def test_a_target_the_generator_emits_but_the_hook_lacks_is_named_missing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A dropped member is red, named, and the repair is said to be editing BUILD.bazel."""
    build = _build(_MEMBERS.replace('"@paperkit_a//:cohere", ', ""))
    assert hook_grid.check(_MODULE, build, {}) == 1
    err = capsys.readouterr().err
    assert "MISSING from //:hook — @paperkit_a//:cohere" in err
    assert "(1 missing, 0 stale)" in err
    assert "EDIT BUILD.bazel" in err


def test_a_hook_member_no_declaration_emits_is_named_stale(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A member nothing emits is red: the stray-member case the set-equality exists for."""
    build = _build(_MEMBERS + ', "@paperkit_zzz//:gate"')
    assert hook_grid.check(_MODULE, build, {}) == 1
    err = capsys.readouterr().err
    assert "STALE in //:hook — @paperkit_zzz//:gate" in err
    assert "(0 missing, 1 stale)" in err


def test_the_canary_is_the_one_harness_member_and_its_absence_is_red(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`//canary:canary` is required: without it the hook is missing the positive control."""
    assert sorted(hook_grid.NON_PROJECT) == ["//canary:canary"]
    build = _build(_MEMBERS.replace(', "//canary:canary"', ""))
    assert hook_grid.check(_MODULE, build, {}) == 1
    assert "MISSING from //:hook — //canary:canary" in capsys.readouterr().err


def test_an_exemption_that_nothing_emits_is_stale_even_when_the_grid_matches(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The policy outlived its subject: red, and named, before the grid is even compared."""
    exempt = {"@paperkit_gone//:gate": "old reason"}
    assert hook_grid.check(_MODULE, _build(), exempt) == 1
    err = capsys.readouterr().err
    assert "STALE EXEMPTION — @paperkit_gone//:gate" in err
    assert "no bib.project tag emits it any more" in err


def test_an_exemption_the_hook_also_runs_is_contradicted(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Excused AND run is incoherent: red, with the remedy to drop the exemption."""
    exempt = {"@paperkit_b//:gate": "reason"}
    assert hook_grid.check(_MODULE, _build(), exempt) == 1
    err = capsys.readouterr().err
    assert "CONTRADICTED EXEMPTION — @paperkit_b//:gate" in err
    assert "drop the exemption" in err


def test_a_build_without_a_hook_list_is_reported(capsys: pytest.CaptureFixture[str]) -> None:
    """No member list found is its own red, not a vacuous pass."""
    assert hook_grid.check(_MODULE, 'test_suite(name = "hook")\n', {}) == 1
    assert "could not find the //:hook member list" in capsys.readouterr().err


def test_the_default_exemptions_are_the_three_paperkit_gates() -> None:
    """The declared policy is data: exactly these three, each carrying a reason."""
    assert sorted(hook_grid.HOOK_EXEMPT) == [
        "@paperkit_image//:gate",
        "@paperkit_report//:gate",
        "@paperkit_setup//:gate",
    ]
    assert all(hook_grid.HOOK_EXEMPT.values())


def test_the_default_exemptions_apply_when_none_is_passed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With no `exempt` argument the paperkit three are in force: this MODULE emits none."""
    assert hook_grid.check(_MODULE, _build()) == 1
    assert "STALE EXEMPTION — @paperkit_setup//:gate" in capsys.readouterr().err


def test_main_reads_both_files_under_the_root_option(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--root` names the directory holding MODULE.bazel and BUILD.bazel."""
    module = _MODULE + "".join(f'bib.project(name = "{n}")\n' for n in _EXEMPT_REPOS)
    (tmp_path / "MODULE.bazel").write_text(module, encoding="utf-8")
    (tmp_path / "BUILD.bazel").write_text(_build(), encoding="utf-8")
    assert hook_grid.main(["--root", str(tmp_path)]) == 0
    assert "//:hook matches MODULE.bazel — 5 project(s)" in capsys.readouterr().out


def test_main_defaults_the_root_to_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no option the repo root is the cwd, as in the pre-commit hook."""
    (tmp_path / "MODULE.bazel").write_text(_MODULE, encoding="utf-8")
    (tmp_path / "BUILD.bazel").write_text(_build(), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert hook_grid.main([]) == 1
    assert "STALE EXEMPTION" in capsys.readouterr().err
