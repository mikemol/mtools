# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A stack is refused at submit when a build file names a source nowhere to be found (W1603)."""

from mikemol.hooks import stackbuildfiles
from mikemol.hooks.stacksnap import Frozen

_MODE = "100644"
_BZL = "luthen/unit_tests.bzl"
_TEST = "luthen/checks/hook_exec_test.py"
_LISTED = 'unit_test(name = "hook_exec", srcs = ["checks/hook_exec_test.py"])\n'
_NOT_SOURCES = (
    'srcs = glob(["tests/*.py"]) + ["@other//pkg:x.py", "//pkg:y.py", ":z.py", "data.json"]\n'
)
_MISSING = (
    f"W1: {_BZL} names checks/hook_exec_test.py, which neither HEAD nor this entry's or an "
    "earlier entry's files carry"
)


def _frozen(path: str, blob: str) -> Frozen:
    return Frozen(path, _MODE, blob)


def _blobs(**texts: str) -> stackbuildfiles.ReadBlob:
    return texts.get


def _never(_path: str) -> bool:
    return False


def _in(*paths: str) -> stackbuildfiles.InHead:
    return lambda path: path in paths


def test_a_listed_source_that_nothing_carries_is_a_finding() -> None:
    """The luthen shape: the .bzl names a test, the file is in no entry and not in HEAD."""
    entries = [("W1", [_frozen(_BZL, "b1")])]
    assert stackbuildfiles.findings(entries, _blobs(b1=_LISTED), _never) == [_MISSING]


def test_the_source_in_the_same_entry_is_sound() -> None:
    """One commit carries the build file and the test it lists."""
    entries = [("W1", [_frozen(_BZL, "b1"), _frozen(_TEST, "b2")])]
    assert stackbuildfiles.findings(entries, _blobs(b1=_LISTED), _never) == []


def test_the_source_in_an_earlier_entry_or_head_is_sound() -> None:
    """Landing order puts it first, or HEAD already has it."""
    later = [("W1", [_frozen(_TEST, "b2")]), ("W2", [_frozen(_BZL, "b1")])]
    assert stackbuildfiles.findings(later, _blobs(b1=_LISTED), _never) == []
    only = [("W1", [_frozen(_BZL, "b1")])]
    assert stackbuildfiles.findings(only, _blobs(b1=_LISTED), _in(_TEST)) == []


def test_a_source_carried_by_a_later_entry_is_still_a_finding() -> None:
    """Order matters: the build file's commit would be broken until entry 2 lands."""
    entries = [("W1", [_frozen(_BZL, "b1")]), ("W2", [_frozen(_TEST, "b2")])]
    assert len(stackbuildfiles.findings(entries, _blobs(b1=_LISTED), _never)) == 1


def test_a_path_from_the_repository_root_is_read_as_a_second_base() -> None:
    """A macro's paths are relative to its caller's package, so the root spelling counts too."""
    entries = [("W1", [_frozen(_BZL, "b1"), _frozen("checks/hook_exec_test.py", "b2")])]
    assert stackbuildfiles.findings(entries, _blobs(b1=_LISTED), _never) == []


def test_globs_labels_and_non_python_names_are_never_findings() -> None:
    """Only a plain quoted .py path is a named source."""
    entries = [("W1", [_frozen("d/BUILD.bazel", "b1")])]
    assert stackbuildfiles.findings(entries, _blobs(b1=_NOT_SOURCES), _never) == []


def test_only_build_files_and_bzl_files_are_read() -> None:
    """A Python file that happens to quote a path is not a build file."""
    entries = [("W1", [_frozen("d/src/pkg/mod.py", "b1")])]
    assert stackbuildfiles.findings(entries, _blobs(b1=_LISTED), _never) == []
    assert stackbuildfiles.is_build_file("d/BUILD")
    assert stackbuildfiles.is_build_file("d/BUILD.bazel")
    assert stackbuildfiles.is_build_file("d/x.bzl")
    assert not stackbuildfiles.is_build_file("d/BUILDER.py")


def test_a_literal_path_inside_a_glob_is_optional_and_never_a_finding() -> None:
    """A glob with allow_empty names no missing source, as buildtel's conftest glob shows."""
    optional = 'srcs = [src] + glob(["tests/conftest.py"], allow_empty = True)\n'
    entries = [("W1", [_frozen("buildtel/BUILD.bazel", "b1")])]
    assert stackbuildfiles.findings(entries, _blobs(b1=optional), _never) == []
    assert stackbuildfiles.named_sources(optional) == []
    assert stackbuildfiles.named_sources(optional + 'x = "real.py"\n') == ["real.py"]


def test_a_blob_that_cannot_be_read_is_skipped() -> None:
    """The gate says why; the check never refuses on what it cannot read."""
    entries = [("W1", [_frozen(_BZL, "gone")])]
    assert stackbuildfiles.findings(entries, _blobs(), _never) == []


_ROOT_BUILD = "BUILD.bazel"
_BARE = 'scripts = ["mutate_runner.py"]\n'


def _names(*names: str) -> stackbuildfiles.HeadNames:
    return lambda: frozenset(names)


def test_a_bare_name_is_present_wherever_head_holds_a_file_of_that_name() -> None:
    """W1886: the root BUILD.bazel lists atoms' scripts by bare name, and they live elsewhere."""
    entries = [("W1", [_frozen(_ROOT_BUILD, "b1")])]
    blobs = _blobs(b1=_BARE)
    assert len(stackbuildfiles.findings(entries, blobs, _never)) == 1
    assert stackbuildfiles.findings(entries, blobs, _never, _names("mutate_runner.py")) == []
    assert len(stackbuildfiles.findings(entries, blobs, _never, _names("other.py"))) == 1


def test_a_bare_name_is_present_wherever_the_stack_holds_a_file_of_that_name() -> None:
    """W1886: a file of that basename in any entry counts, in any directory."""
    carried = [_frozen(_ROOT_BUILD, "b1"), _frozen("check_mutants/mutate_runner.py", "b2")]
    entries = [("W1", carried)]
    assert stackbuildfiles.findings(entries, _blobs(b1=_BARE), _never) == []


def test_a_name_with_a_directory_is_still_judged_as_a_path() -> None:
    """W1886: the basename rule is for bare names only, so luthen's finding stands."""
    entries = [("W1", [_frozen(_BZL, "b1")])]
    assert stackbuildfiles.findings(
        entries, _blobs(b1=_LISTED), _never, _names("hook_exec_test.py")
    ) == [_MISSING]
