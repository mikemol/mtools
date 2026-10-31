# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--freeze-from DIR` is read only in its one form; another repository's directory is refused.

⚑ THE CONTROLS: a plain stack form is not a freeze-from form, a flag in any other place is not the
form, and the same-repository judgement fails closed when either common directory is unknown.
"""

from pathlib import Path

from mikemol.hooks import freezefrom

_FROM = ["/r", "--stack", "s.json", "--freeze-from", "/scratch/mtools-W9"]


def test_the_five_word_form_gives_the_directory_and_no_other_arrangement_does() -> None:
    """Only `REPO --stack FILE --freeze-from DIR` yields a directory."""
    assert freezefrom.parse(_FROM) == Path("/scratch/mtools-W9")
    assert freezefrom.parse(["/r", "--stack", "s.json"]) is None
    assert freezefrom.parse(["/r", "--stack", "s.json", "--freeze-from"]) is None
    assert freezefrom.parse(["/r", "--freeze-from", "d", "--stack", "s.json"]) is None
    assert freezefrom.parse(["/r", "--stack", "s.json", "--other", "d"]) is None


def test_both_stack_forms_are_stack_forms_and_a_commit_or_a_stray_flag_is_not() -> None:
    """The plain form and the freeze-from form are stacks; a message commit is not."""
    assert freezefrom.form_is_stack(["/r", "--stack", "s.json"])
    assert freezefrom.form_is_stack(_FROM)
    assert not freezefrom.form_is_stack(["/r", "-m", "subject"])
    assert not freezefrom.form_is_stack(["/r", "--stack", "s.json", "--freeze-from"])


def test_the_same_common_dir_is_admitted_and_another_or_an_unknown_one_is_refused(
    tmp_path: Path,
) -> None:
    """The scratch worktree shares the main repository's common dir; a stranger does not."""
    main = tmp_path / "repo" / ".git"
    given = tmp_path / "scratch"
    assert freezefrom.refusal(main, main, given) is None
    stranger = tmp_path / "other" / ".git"
    text = freezefrom.refusal(main, stranger, given)
    assert text is not None
    assert "another repository" in text
    assert str(given) in text
    assert "not a directory git can read" in str(freezefrom.refusal(None, main, given))
    assert "not a directory git can read" in str(freezefrom.refusal(main, None, given))
