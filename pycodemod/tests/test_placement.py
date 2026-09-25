# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for placement: when a guard fires on a bare invocation, not where it is written."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import placement as pl

if TYPE_CHECKING:
    from pathlib import Path

_AT_ENTRY = """\
if __name__ == "__main__":
    require_at_entry()
"""

_UNDER_DISPATCH = """\
if __name__ == "__main__":
    if args.apply:
        require_at_entry()
"""

_COMMENT_IN_BLOCK = """\
if __name__ == "__main__":
    args = parse()
# a comment at column 0, still inside the block
    require_at_entry()
"""

_ONE_HOP = """\
def main():
    require_at_entry()


if __name__ == "__main__":
    main()
"""

_ONE_HOP_DISPATCHED = """\
def main():
    require_at_entry()


if __name__ == "__main__":
    if mode:
        main()
"""

_HELPER_IN_BLOCK = """\
def main():
    require_at_entry()


if __name__ == "__main__":
    def later():
        main()
"""

_NO_BLOCK_ONE_HOP = """\
def main():
    require_at_entry()


main()
"""

_NO_BLOCK = "require_at_entry()\n"

_ELSE_OF_MAIN = """\
if __name__ == "__main__":
    pass
else:
    require_at_entry()
"""

_REVERSED = """\
if '__main__' == __name__:
    require_at_entry()
"""

_METHOD = """\
class Tool:
    def run(self):
        require_at_entry()


if __name__ == "__main__":
    Tool().run()
"""

_ASYNC = """\
async def main():
    require_at_entry()


if __name__ == "__main__":
    asyncio.run(main())
"""

_FIRST_WRITE = """\
def write(p):
    _snapshot_once(p)


if __name__ == "__main__":
    write(1)
"""

_BOTH = _FIRST_WRITE + "    require_at_entry()\n"


def _verdict(tmp_path: Path, text: str) -> list[tuple[str, str, int]]:
    path = tmp_path / "tool.py"
    path.write_text(text, encoding="utf-8")
    return [(r.verdict, r.form, r.line) for r in pl.placement([str(path)]).rows]


def test_a_guard_in_the_entry_block_fires_at_entry(tmp_path: Path) -> None:
    """A guard at module scope inside the `__main__` block is `entry`."""
    assert _verdict(tmp_path, _AT_ENTRY) == [("entry", "require_at_entry", 2)]


def test_a_guard_under_a_dispatch_condition_is_dispatched(tmp_path: Path) -> None:
    """A guard under a mode test inside the block is `dispatched`: written, not fired."""
    assert _verdict(tmp_path, _UNDER_DISPATCH) == [("dispatched", "require_at_entry", 3)]


def test_a_comment_at_column_zero_does_not_end_the_block(tmp_path: Path) -> None:
    """⚑⚑⚑ The entry block is the `if` itself, not an indentation span.

    The origin ended the span at the column-0 comment, so this guard read `dispatched`.
    """
    assert _verdict(tmp_path, _COMMENT_IN_BLOCK) == [("entry", "require_at_entry", 4)]


@pytest.mark.parametrize(
    ("text", "verdict"),
    [(_ONE_HOP, "entry"), (_ONE_HOP_DISPATCHED, "dispatched"), (_HELPER_IN_BLOCK, "dispatched")],
)
def test_one_hop_follows_the_callers_scope(tmp_path: Path, text: str, verdict: str) -> None:
    """⚑⚑ A guard in a def is `entry` only if the block calls that def at module scope, unguarded.

    A helper DEFINED in the block runs nothing; the origin matched it by line range.
    """
    assert _verdict(tmp_path, text) == [(verdict, "require_at_entry", 2)]


@pytest.mark.parametrize(("text", "line"), [(_NO_BLOCK, 1), (_NO_BLOCK_ONE_HOP, 2)])
def test_a_script_with_no_main_block_runs_at_entry(tmp_path: Path, text: str, line: int) -> None:
    """⚑⚑ With no `__main__` block, module scope IS the entry, for a direct call and one hop.

    The origin's one-hop check refused a def called from module scope for want of a span.
    """
    assert _verdict(tmp_path, text) == [("entry", "require_at_entry", line)]


def test_the_else_of_the_main_block_is_dispatched(tmp_path: Path) -> None:
    """An `else` of the entry test runs on import, never on invocation: `dispatched`."""
    assert _verdict(tmp_path, _ELSE_OF_MAIN) == [("dispatched", "require_at_entry", 4)]


def test_either_operand_order_and_quote_is_the_entry_test(tmp_path: Path) -> None:
    """`'__main__' == __name__` is the entry test as much as the usual spelling."""
    assert _verdict(tmp_path, _REVERSED) == [("entry", "require_at_entry", 2)]


@pytest.mark.parametrize("text", [_METHOD, _ASYNC])
def test_a_method_or_async_def_reached_from_the_block_is_entry(tmp_path: Path, text: str) -> None:
    """⚑ A method's scope is qualified by its class; the block calls it by its own name."""
    assert _verdict(tmp_path, text) == [("entry", "require_at_entry", 3 if text is _METHOD else 2)]


def test_a_first_write_form_is_first_write_and_entry_outranks_it(tmp_path: Path) -> None:
    """`_snapshot_once` is `first-write`; a file that also guards at entry earns `entry`."""
    assert _verdict(tmp_path, _FIRST_WRITE) == [("first-write", "_snapshot_once", 2)]
    assert _verdict(tmp_path, _BOTH) == [("entry", "require_at_entry", 7)]


def test_the_first_write_forms_are_the_callers(tmp_path: Path) -> None:
    """Forms passed as first-write are graded first-write, whatever their name."""
    path = tmp_path / "tool.py"
    path.write_text(_AT_ENTRY.replace("require_at_entry", "guard"), encoding="utf-8")
    got = pl.placement([str(path)], forms=(), first_write_forms=("guard",)).rows
    assert [(r.verdict, r.form) for r in got] == [("first-write", "guard")]


@pytest.mark.parametrize(
    ("cond", "want"),
    [
        ('__name__ == "__main__"', True),
        ("'__main__' == __name__", True),
        ('__name__ != "__main__"', False),
        ('a == __name__ == "__main__"', False),
        ("mode", False),
        ("not (", False),
    ],
)
def test_the_entry_test_is_exactly_the_comparison(cond: str, *, want: bool) -> None:
    """Only `__name__ == "__main__"`, in either order, is the entry test."""
    assert pl.is_entry_test(cond) is want


def test_an_unreadable_file_is_skipped_and_the_limits_are_returned(tmp_path: Path) -> None:
    """⚑ A file the scan could not read is skipped; what cannot be decided rides every result."""
    path = tmp_path / "bad.py"
    path.write_bytes(b"\xff\xfe require_at_entry")
    got = pl.placement([str(path)])
    whys: list[str] = [s.why for s in got.skipped]
    assert (len(got.rows), whys, got.undecidable) == (0, ["undecodable"], pl.UNDECIDABLE)
