# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A recursive delete passes only inside a path the session created, else it is refused (W1995)."""

from mikemol.hooks import recursive_delete
from mikemol.hooks.recursive_delete import refusal

CREATED = ["/work/scratch"]
CWD = "/work/scratch"


def test_a_delete_inside_a_created_path_is_allowed() -> None:
    """A relative and an absolute target under the created root, and the root itself, pass."""
    assert refusal("rm -rf build", CREATED, CWD) is None
    assert refusal("rm -rf /work/scratch/a/b", CREATED, CWD) is None
    assert refusal("rm -rf /work/scratch", CREATED, CWD) is None


def test_a_delete_outside_every_created_path_is_refused_with_the_remedy() -> None:
    """The refusal names the form and the target, and carries the remedy."""
    said = refusal("rm -rf /work/other", CREATED, CWD)
    assert said is not None
    assert "rm target '/work/other'" in said
    assert recursive_delete.REMEDY in said


def test_a_sibling_whose_name_starts_with_a_created_path_is_outside_it() -> None:
    """/work/scratch-old is not under /work/scratch; only a whole path component counts."""
    assert refusal("rm -rf /work/scratch-old", CREATED, CWD) is not None


def test_dot_dot_that_climbs_out_of_the_created_path_is_refused() -> None:
    """Relative targets are resolved as text first, so ../x leaves the created root."""
    assert refusal("rm -rf ../x", CREATED, CWD) is not None
    assert refusal("rm -rf a/../../x", CREATED, CWD) is not None
    assert refusal("rm -rf a/../b", CREATED, CWD) is None


def test_the_root_and_an_unexpanded_home_are_refused() -> None:
    """`/` and `~` lie under no created path (the shell has not expanded the tilde)."""
    assert refusal("rm -rf /", CREATED, CWD) is not None
    assert refusal("rm -rf ~/x", CREATED, CWD) is not None


def test_a_git_clean_without_a_pathspec_is_judged_as_the_working_directory() -> None:
    """The implicit target is `.`: allowed inside a created cwd, refused outside one."""
    assert refusal("git clean -fd", CREATED, CWD) is None
    assert refusal("git clean -fd", CREATED, "/work/other") is not None


def test_every_target_of_a_chain_is_judged_and_the_first_stray_is_named() -> None:
    """A good delete does not excuse a later bad one."""
    said = refusal("rm -rf a && rm -rf /etc/x", CREATED, CWD)
    assert said is not None
    assert "'/etc/x'" in said


def test_an_unreadable_command_is_refused_with_the_readers_words() -> None:
    """A target built by expansion is refused, never guessed."""
    said = refusal("rm -rf $DIR", CREATED, CWD)
    assert said is not None
    assert "built by expansion" in said


def test_a_command_with_no_recursive_delete_is_allowed_whatever_was_created() -> None:
    """Nothing to judge, even with an empty record."""
    assert refusal("ls -l /etc", [], CWD) is None
    assert refusal("rm -f /etc/x", [], CWD) is None


def test_with_no_created_path_every_recursive_delete_is_refused() -> None:
    """An empty record allows nothing."""
    assert refusal("rm -rf build", [], CWD) is not None
