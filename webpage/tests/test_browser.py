# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The browser behaviour the helpers rest on, against the pinned chromium (W1820, nemik:W715, W717).

⚑ NEMIK'S PROBES, AS TESTS, ON THE BROWSER THIS REPOSITORY PINS: a page that throws ends a clockless
wait with its message, a page that is ready ends it quietly, a handler that raises does NOT abort a
pending wait (the exception resurfaces at the next call, which is why `watch` records the error in
the page), and a page crashed or closed over CDP ends a pending wait by itself, so the helper needs
no crash code. No wait here has a bound: each ends on the page's own event, or the harness ends it.

⚑ A PENDING WAIT CANNOT BE INTERRUPTED FROM ITS OWN PROCESS (sync Playwright blocks it), so the
crash and the close are sent by `cdp_poke.py`, a second process, once the wait is provably pending.
"""

import os
import resource
import socket
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast
from urllib.parse import quote

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

from mikemol.webpage import page as webpage

BREAKS = "<script>setTimeout(() => { throw new Error('boom'); }, 200);</script>"
READIES = "<script>setTimeout(() => { window.ready = true; }, 200);</script>"
THROWS_THEN_READIES = (
    "<script>setTimeout(() => { throw new Error('boom'); }, 200);"
    "setTimeout(() => { window.ready = true; }, 600);</script>"
)
NEVER_READY = "<script>window.ready = false;</script>"
READY = "() => window.ready === true"
POLLED_READY = "() => { window.__polling = true; return window.ready === true; }"


def _located(name: str) -> Path | None:
    where = os.environ.get(name)
    runfiles = os.environ.get("RUNFILES_DIR") or os.environ.get("TEST_SRCDIR")
    return Path(runfiles) / where if where and runfiles else None


@pytest.fixture(name="chrome")
def _chrome(monkeypatch: pytest.MonkeyPatch) -> Path:
    found = _located("CHROME_RLOCATION")
    if found is None:
        pytest.skip("not run under bazel: no CHROME_RLOCATION to launch")
    # ⚑ THE SANDBOX HAS NO /var/tmp, WHICH PLAYWRIGHT'S DRIVER USES FOR ITS ARTIFACTS: measured, the
    # first run failed with ENOENT on mkdtemp /var/tmp/playwright-artifacts-*. Bazel gives each
    # test a writable TEST_TMPDIR, and the driver and the poker inherit TMPDIR from this process.
    scratch = os.environ.get("TEST_TMPDIR")
    if scratch:
        monkeypatch.setenv("TMPDIR", scratch)
    # ⚑ NO CORE FILE FROM A CRASH THE TEST CAUSES ON PURPOSE (luthen's coredump_loop alert,
    # 2026-10-22, exe=chrome-headless-shell): the crash probe sends `Page.crash` and the renderer
    # dumps core. The limit is set in this process, so the browser, the driver and the poker all
    # inherit it: the standing rule of a core size of 0, as nemik's codon fix applies.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    return found


def _free_port() -> int:
    with socket.socket() as holder:
        holder.bind(("127.0.0.1", 0))
        return cast("int", holder.getsockname()[1])


@contextmanager
def _opened(chrome: Path, html: str, *, watched: bool = True) -> Iterator[tuple[Page, int]]:
    """Launch the pinned browser with a debugging port, open `html`, and close it after.

    Yields:
        the page and the debugging port.

    """
    port = _free_port()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=str(chrome), args=[f"--remote-debugging-port={port}"]
        )
        page = browser.new_page()
        if watched:
            webpage.watch(page)
        page.goto("data:text/html," + quote(html))
        try:
            yield page, port
        finally:
            browser.close()


def _poker(port: int, action: str) -> subprocess.Popen[bytes]:
    poke = _located("CDP_POKE")
    assert poke is not None
    return subprocess.Popen([sys.executable, str(poke), str(port), action])


def test_a_page_that_throws_ends_the_wait_with_its_message(chrome: Path) -> None:
    """The wait never sees its predicate hold, and fails with the page's own error."""
    with (
        _opened(chrome, BREAKS) as (page, _port),
        pytest.raises(webpage.PageBrokenError, match="boom"),
    ):
        webpage.until(page, READY)


def test_a_page_that_raises_its_event_ends_the_wait_quietly(chrome: Path) -> None:
    """A page that becomes ready returns without an error."""
    with _opened(chrome, READIES) as (page, _port):
        webpage.until(page, READY)


def test_a_page_that_throws_on_purpose_hands_the_message_back(chrome: Path) -> None:
    """The expecting form returns the page's error and leaves the verdict to the test."""
    with _opened(chrome, BREAKS) as (page, _port):
        found = webpage.until_expecting(page, READY)
    assert found is not None
    assert "boom" in found


def test_an_unwatched_page_rests_on_its_predicate_alone(chrome: Path) -> None:
    """With no error record the wait still ends when the page is ready, and returns no error."""
    with _opened(chrome, READIES, watched=False) as (page, _port):
        assert webpage.until_expecting(page, READY) is None


def test_a_pageerror_handler_that_raises_does_not_abort_a_pending_wait(chrome: Path) -> None:
    """The handler fires and raises, the wait still ends on its predicate, the error resurfaces."""
    fired: list[str] = []

    def handler(_error: PlaywrightError) -> None:
        fired.append("fired")
        message = "handler boom"
        raise RuntimeError(message)

    with _opened(chrome, THROWS_THEN_READIES, watched=False) as (page, _port):
        page.on("pageerror", handler)
        page.wait_for_function(READY, timeout=webpage.NO_TIMEOUT)
        assert fired == ["fired"]
        with pytest.raises(RuntimeError, match="handler boom"):
            page.title()


def test_a_page_crashed_over_cdp_ends_a_pending_wait_by_itself(chrome: Path) -> None:
    """Playwright raises "Target crashed" itself: the helper needs no crash code."""
    with _opened(chrome, NEVER_READY) as (page, port):
        poker = _poker(port, "crash")
        try:
            with pytest.raises(PlaywrightError, match=r"(?i)crash"):
                page.wait_for_function(POLLED_READY, timeout=webpage.NO_TIMEOUT)
        finally:
            # ⚑ THE POKER'S OWN `Page.crash` CALL NEVER GETS AN ANSWER FROM THE PAGE IT CRASHED, so
            # it is ended here, not waited for: the wait above is the thing this test measures.
            poker.kill()
            poker.wait()


def test_a_page_closed_over_cdp_ends_a_pending_wait_by_itself(chrome: Path) -> None:
    """Playwright raises TargetClosedError itself, naming the closed page, context or browser."""
    with _opened(chrome, NEVER_READY) as (page, port):
        poker = _poker(port, "close")
        try:
            with pytest.raises(PlaywrightError, match=r"(?i)closed"):
                page.wait_for_function(POLLED_READY, timeout=webpage.NO_TIMEOUT)
        finally:
            poker.kill()
            poker.wait()


def test_the_browser_runs_with_a_core_size_of_zero(chrome: Path) -> None:
    """The fixture sets RLIMIT_CORE to 0 before anything is launched, so a crash leaves no core."""
    assert chrome.name == "chrome-headless-shell"
    assert resource.getrlimit(resource.RLIMIT_CORE) == (0, 0)
