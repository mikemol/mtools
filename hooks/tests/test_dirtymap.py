# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Each dirty path is mapped to what carries it, and only-in-main is a number (W2104).

⚑ THE CONTROLS: a path held by a stack and a scratch tree is named for the stack, the queue files
and the inbox are excepted by name and never counted as only-in-main, and a path nothing carries
is NONE and is the figure the count line ends on.
"""

from mikemol.hooks import dirtymap

_STACKS = {"111": {"a.py", "shared.py"}, "222": {"b.py"}}
_SCRATCH = {"w9": {"c.py", "shared.py"}}


def test_a_stack_beats_a_scratch_tree_and_a_scratch_tree_beats_nothing() -> None:
    """Carriers in order: stack key, scratch name, the named exceptions, NONE."""
    cases = {
        "a.py": "stack:111",
        "shared.py": "stack:111",
        "c.py": "scratch:w9",
        ".claude/paths-forward.json": "excepted:queue",
        "inbox/archive/x.md": "excepted:inbox",
        "loose.py": "NONE",
    }
    for path, expected in cases.items():
        assert dirtymap.carrier_of(path, _STACKS, _SCRATCH) == expected


def test_the_lines_end_on_a_count_that_separates_only_in_main() -> None:
    """Six dirty paths: three carried, two excepted, one only in main."""
    dirty = ["a.py", "c.py", "b.py", ".claude/paths-forward.md", "inbox/y.md", "loose.py"]
    assert dirtymap.carrier_lines(dirty, _STACKS, _SCRATCH) == [
        "a.py carrier=stack:111",
        "c.py carrier=scratch:w9",
        "b.py carrier=stack:222",
        ".claude/paths-forward.md carrier=excepted:queue",
        "inbox/y.md carrier=excepted:inbox",
        "loose.py carrier=NONE",
        "# 6 dirty, 3 carried, 2 excepted, 1 only in main",
    ]


def test_a_clean_tree_is_a_zero_count_line() -> None:
    """No dirty path gives only the count line."""
    assert dirtymap.carrier_lines([], {}, {}) == [
        "# 0 dirty, 0 carried, 0 excepted, 0 only in main"
    ]


def test_porcelain_text_is_read_into_paths_and_a_rename_names_its_new_path() -> None:
    """Modified, untracked, staged and renamed entries; the status columns are dropped."""
    text = " M hooks/a.py\n?? new.txt\nA  staged.py\nR  old.py -> moved.py\n\n"
    assert dirtymap.dirty_paths(text) == ["hooks/a.py", "new.txt", "staged.py", "moved.py"]
