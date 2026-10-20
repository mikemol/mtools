# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1685: wait on a Playwright page with no clock, and end the wait when the page breaks.

Lifted from nemik's `tests/webpage.py` (nemik:W715, W717). `watch` installs a script that records
the first window error or unhandled rejection; `until` waits on the page's own predicate OR that
record, so a page that breaks ends the wait with its message instead of hanging until the harness
kills the target. A handler that raises does not abort a pending wait (probed by nemik 2026-10-18:
the exception resurfaced at the next call), which is why the record exists.

⚑ NO BROWSER IS IMPORTED: `Waitable` names only what these functions call, so the record and the
wait are tested against a stand-in page.
"""

from typing import Protocol

WATCH = (
    "window.__broken = null;"
    "window.addEventListener('error', e => "
    "{ window.__broken = window.__broken || String(e.message); });"
    "window.addEventListener('unhandledrejection', e => "
    "{ window.__broken = window.__broken || String(e.reason); });"
)
NO_TIMEOUT = 0


class PageBrokenError(AssertionError):
    """The page raised an error or an unhandled rejection while a test waited on it."""


class Waitable(Protocol):
    """What `watch` and `until` use of a Playwright page, so they need no Any."""

    def add_init_script(self, script: str) -> object:
        """Run `script` in every document the page loads."""
        ...

    def goto(self, url: str) -> object:
        """Navigate the page to `url`."""
        ...

    def wait_for_function(self, expression: str, *, timeout: float) -> object:
        """Wait for a JS predicate to hold."""
        ...

    def evaluate(self, expression: str) -> object:
        """Evaluate a JS expression in the page."""
        ...


def watch(page: Waitable) -> None:
    """Install the error record on a page; call it before the page navigates.

    Args:
        page: The Playwright page.

    """
    page.add_init_script(WATCH)


def until_expecting(page: Waitable, expr: str) -> str | None:
    """Wait for a page predicate with no clock, returning the page's error instead of raising.

    For a page that throws on purpose: the wait ends when the predicate holds or the page raises,
    and the test decides what the message must be. `!= null` (loose) because a page that was not
    watched has no record at all, and the wait must then rest on its predicate alone.

    Args:
        page: The Playwright page, watched before it navigated.
        expr: A JS arrow function that is truthy once the page is ready.

    Returns:
        The page's first error or unhandled-rejection message, or None when it raised none.

    """
    page.wait_for_function(f"() => window.__broken != null || ({expr})()", timeout=NO_TIMEOUT)
    broken = page.evaluate("() => window.__broken")
    return None if broken is None else str(broken)


def until(page: Waitable, expr: str) -> None:
    """Wait for a page predicate with no clock, or fail with the page's own error.

    Args:
        page: The Playwright page, watched before it navigated.
        expr: A JS arrow function that is truthy once the page is ready.

    Raises:
        PageBrokenError: The page raised an error or unhandled rejection before the predicate held.

    """
    broken = until_expecting(page, expr)
    if broken is not None:
        message = f"the page broke while the test waited on it: {broken}"
        raise PageBrokenError(message)


def load(page: Waitable, url: str, wait: str) -> None:
    """Watch a page, navigate it to `url`, and wait with no clock until `wait` holds.

    Args:
        page: A new Playwright page.
        url: The address to open.
        wait: A JS arrow function that is truthy once the page is ready.

    """
    watch(page)
    page.goto(url)
    until(page, wait)
