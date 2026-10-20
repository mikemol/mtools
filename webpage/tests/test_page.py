# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The page-error record and the clockless wait, against a stand-in page and no browser."""

import pytest

from mikemol.webpage import page

_READY = "() => true"
_BROKEN_TEXT = "boom"


class _Stub:
    """A page that records what it was asked and answers `evaluate` with a set message."""

    def __init__(self, broken: object = None) -> None:
        self.broken = broken
        self.calls: list[tuple[str, str]] = []
        self.timeout: float | None = None

    def add_init_script(self, script: str) -> None:
        self.calls.append(("init", script))

    def goto(self, url: str) -> None:
        self.calls.append(("goto", url))

    def wait_for_function(self, expression: str, *, timeout: float) -> None:
        self.calls.append(("wait", expression))
        self.timeout = timeout

    def evaluate(self, expression: str) -> object:
        self.calls.append(("evaluate", expression))
        return self.broken


def test_watch_installs_the_error_and_rejection_record() -> None:
    """The init script records both a window error and an unhandled rejection."""
    stub = _Stub()
    page.watch(stub)
    assert stub.calls == [("init", page.WATCH)]
    assert "'error'" in page.WATCH
    assert "'unhandledrejection'" in page.WATCH


def test_the_wait_has_no_clock_and_rests_on_the_predicate_or_the_record() -> None:
    """Timeout zero, and the expression is the record OR the caller's predicate."""
    stub = _Stub()
    assert page.until_expecting(stub, _READY) is None
    assert stub.timeout == 0
    assert stub.calls[0] == ("wait", "() => window.__broken != null || (() => true)()")


def test_a_page_that_broke_ends_the_wait_with_its_message() -> None:
    """`until` raises with the page's error; `until_expecting` returns it."""
    assert page.until_expecting(_Stub(_BROKEN_TEXT), _READY) == _BROKEN_TEXT
    with pytest.raises(page.PageBrokenError, match=_BROKEN_TEXT):
        page.until(_Stub(_BROKEN_TEXT), _READY)


def test_a_page_that_raised_nothing_passes_until() -> None:
    """No record, no raise."""
    page.until(_Stub(), _READY)


def test_load_watches_then_navigates_then_waits() -> None:
    """The record must exist before the page loads, so the order is fixed."""
    stub = _Stub()
    page.load(stub, "http://x/", _READY)
    assert [name for name, _ in stub.calls] == ["init", "goto", "wait", "evaluate"]
