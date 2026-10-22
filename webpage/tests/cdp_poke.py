# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A second process that crashes or closes a page over CDP while a wait is pending (W1820).

⚑ A SYNC PLAYWRIGHT CALL BLOCKS ITS WHOLE PROCESS, so a wait that is pending in the test cannot be
interrupted from the test: nemik's probes (nemik:W715) used a second process, and so does this one.
It connects to the browser the test launched, WAITS ON THE PAGE'S OWN SIGNAL (the predicate under
wait sets `window.__polling`, so the wait is provably pending) and only then acts. No sleep decides
when: the pending wait is the event.

    python cdp_poke.py PORT crash|close
"""

import sys
from typing import cast

from playwright.sync_api import sync_playwright

CRASH = "crash"
CLOSE = "close"
POLLING = "() => window.__polling === true"
USAGE = "usage: cdp_poke.py PORT crash|close\n"
ARGUMENTS = 3


def main(argv: list[str]) -> int:
    """Wait for the page's pending wait, then crash or close the page.

    Returns:
        0 once the action was sent, 2 for a usage error.

    """
    if len(argv) != ARGUMENTS or argv[2] not in {CRASH, CLOSE}:
        sys.stderr.write(USAGE)
        return 2
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{argv[1]}")
        # ⚑ THE TEST'S PAGE LIVES IN A CONTEXT OF ITS OWN, NOT THE DEFAULT ONE (found when the
        # first probe waited for ever on the empty default page): take the page on the data URL.
        found = [(c, pg) for c in browser.contexts for pg in c.pages if pg.url.startswith("data:")]
        context, page = found[0]
        page.wait_for_function(POLLING, timeout=0)
        if argv[2] == CRASH:
            client = context.new_cdp_session(page)
            cast("object", client.send("Page.crash"))
        else:
            page.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
