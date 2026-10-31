# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The bazel shim adds the build-event file to `test` and `build` once, and never finds itself.

⚑ THE CONTROLS: other verbs are untouched, a command that already names the flag keeps its own, a
startup option before the verb is skipped, and the real bazel is never the shim's own directory.
"""

from pathlib import Path

from mikemol.hooks import bazelshim

_BEP = "/gate/.bep.json"
_FLAG = "--build_event_json_file"


def test_a_test_or_build_gets_the_flag_right_after_its_verb_past_startup_options() -> None:
    """The flag follows the verb, and `--output_base=...` before it is skipped over."""
    assert bazelshim.with_bep(["test", "//...", "--keep_going"], _BEP) == [
        "test",
        f"{_FLAG}={_BEP}",
        "//...",
        "--keep_going",
    ]
    assert bazelshim.with_bep(["--output_base=/o", "build", "//a"], _BEP) == [
        "--output_base=/o",
        "build",
        f"{_FLAG}={_BEP}",
        "//a",
    ]


def test_another_verb_no_verb_or_an_existing_flag_leaves_the_command_alone() -> None:
    """query, info, run and a bare `--version` are not changed; an own file is kept, once."""
    for same in (["query", "//..."], ["info"], ["--version"], [], ["run", "//x"]):
        assert bazelshim.with_bep(same, _BEP) == same
    own = ["test", f"{_FLAG}=/mine.json", "//..."]
    assert bazelshim.with_bep(own, _BEP) == own
    spaced = ["build", _FLAG, "/mine.json", "//..."]
    assert bazelshim.with_bep(spaced, _BEP) == spaced


def test_the_real_bazel_is_the_first_on_the_path_outside_the_shims_own_directory() -> None:
    """The shim's directory is skipped even when it comes first; no other bazel gives None."""
    shim = Path("/shim")
    present = {Path("/shim/bazel"), Path("/usr/bin/bazel"), Path("/opt/bazel")}

    def exists(path: Path) -> bool:
        return path in present

    assert bazelshim.real_bazel("/shim:/usr/bin:/opt", shim, exists) == Path("/usr/bin/bazel")
    assert bazelshim.real_bazel("/shim::/opt", shim, exists) == Path("/opt/bazel")
    assert bazelshim.real_bazel("/shim:/nowhere", shim, exists) is None
