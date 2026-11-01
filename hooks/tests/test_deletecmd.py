# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The recursive-delete reader names the targets of rm -r, git clean and find -delete (W1994)."""

import pytest

from mikemol.hooks import deletecmd
from mikemol.hooks.deletecmd import Delete

CLEAN_HERE = [Delete("git-clean", (".",))]


def test_rm_with_a_recursive_flag_in_any_spelling_names_its_operands() -> None:
    """-r, -R, -rf, -fr, --recursive and a combined -rfv all make a delete; -f alone does not."""
    for flags in ("-r", "-R", "-rf", "-fr", "-rfv", "--recursive"):
        assert deletecmd.deletes(f"rm {flags} a b") == [Delete("rm", ("a", "b"))]
    assert deletecmd.deletes("rm -f a") == []
    assert deletecmd.deletes("rm a b") == []


def test_a_double_dash_ends_the_flags_so_an_operand_named_like_a_flag_is_a_target() -> None:
    """`rm -r -- -rf` deletes a path called -rf; it is the operand, not another flag."""
    assert deletecmd.deletes("rm -r -- -rf x") == [Delete("rm", ("-rf", "x"))]


def test_git_clean_needs_force_and_no_dry_run_and_defaults_to_the_working_directory() -> None:
    """-f makes it a delete; -n or --dry-run does not; no pathspec means the directory itself."""
    named = deletecmd.deletes("git clean -fdx build dist")
    assert named == [Delete("git-clean", ("build", "dist"))]
    assert deletecmd.deletes("git clean -fd") == CLEAN_HERE
    assert deletecmd.deletes("git clean --force -d") == CLEAN_HERE
    assert deletecmd.deletes("git clean -nfd") == []
    assert deletecmd.deletes("git clean --dry-run -f") == []
    assert deletecmd.deletes("git clean -d") == []


def test_git_clean_is_found_after_git_s_own_global_options() -> None:
    """`git -C repo -c k=v clean -f x` is still a clean; another git verb is not one."""
    assert deletecmd.deletes("git -C repo -c k=v clean -f x") == [Delete("git-clean", ("x",))]
    assert deletecmd.deletes("git -C repo status") == []
    assert deletecmd.deletes("git log") == []


def test_find_delete_names_its_leading_paths_or_the_working_directory() -> None:
    """The paths come before the first expression word; none means the directory itself."""
    named = deletecmd.deletes("find a b -name '*.pyc' -delete")
    assert named == [Delete("find-delete", ("a", "b"))]
    assert deletecmd.deletes("find -name x -delete") == [Delete("find-delete", (".",))]
    assert deletecmd.deletes("find a -name x -print") == []


def test_a_chained_command_is_read_segment_by_segment_in_order() -> None:
    """&&, ; and | split it; each recursive delete is reported, the rest ignored."""
    got = deletecmd.deletes("cd x && rm -rf a ; ls | cat && git clean -fd y")
    assert got == [Delete("rm", ("a",)), Delete("git-clean", ("y",))]


def test_a_path_prefix_and_sudo_do_not_hide_the_command() -> None:
    """/bin/rm, sudo rm and command rm are all rm."""
    for prefix in ("/bin/rm", "sudo rm", "command rm", "sudo /usr/bin/rm"):
        assert deletecmd.deletes(f"{prefix} -rf a") == [Delete("rm", ("a",))]


def test_a_target_built_by_expansion_is_refused_not_guessed() -> None:
    """A variable, a command substitution and a backtick name nothing the hook can judge."""
    for command in ("rm -rf $DIR", 'rm -rf "$(cat list)"', "rm -rf `pwd`", "find $D -delete"):
        with pytest.raises(deletecmd.UnreadableError):
            deletecmd.deletes(command)


def test_a_command_that_does_not_split_into_words_is_refused() -> None:
    """An unbalanced quote cannot be read at all."""
    with pytest.raises(deletecmd.UnreadableError):
        deletecmd.deletes("rm -rf 'unclosed")


def test_an_ordinary_command_holds_no_delete() -> None:
    """A non-delete, an empty command and a word that only contains rm are not deletes."""
    assert deletecmd.deletes("ls -l") == []
    assert deletecmd.deletes("") == []
    assert deletecmd.deletes("rmdir -p a") == []
    assert deletecmd.deletes("echo rm -rf a") == []
