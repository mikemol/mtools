# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Is the Build Event Protocol sink accepting a connection? One TCP connect, three outcomes.

⚑⚑⚑ IN THE TREE, NOT THE SCRATCHPAD. Its predecessor `await_bep.py` lived in the scratchpad and
was erased by a directory move on 2026-09-19 along with every other probe this session had built.
A handle only survives if its referent lives outside the context.

⚑⚑ TCP CONNECT, NOT curl. The sink speaks gRPC on 31985, and `curl` returns `http_code=000` to a
gRPC listener WHETHER IT IS HEALTHY OR ABSENT — measured on 2026-09-13, both directions. curl is
void on this port. A connect is the one cheap thing that distinguishes *listening* from *not*.

⚑ AND IT SAYS WHICH OF THREE, because a probe collapsing three outcomes into pass/fail has already
discarded the discriminating bit. `exit 7` (refused) and `exit 1` (reached, wrong protocol) were
different claims on 2026-09-13 and the difference is what settled a three-tick hold.
"""

from __future__ import annotations

import socket
import sys

HOST, PORT = "127.0.0.1", 31985


def main() -> int:
    """Try one connection and report the outcome by name.

    Returns:
        0 when the sink accepts, 1 when refused, 2 on any other socket error.

    """
    try:
        with socket.create_connection((HOST, PORT), timeout=3):
            print(f"BEP sink {HOST}:{PORT} ACCEPTS — something is listening (not proof it is ready)")
            return 0
    except ConnectionRefusedError:
        print(f"BEP sink {HOST}:{PORT} REFUSED — nothing is listening on the port")
        return 1
    except OSError as e:
        print(f"BEP sink {HOST}:{PORT} UNREACHABLE — {e} (not a refusal; the route is the subject)")
        return 2


if __name__ == "__main__":
    sys.exit(main())
