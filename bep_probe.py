# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Is the Build Event Protocol sink accepting a connection? One TCP connect, four outcomes.

⚑⚑⚑ IN THE TREE, NOT THE SCRATCHPAD. Its predecessor `await_bep.py` lived in the scratchpad and
was erased by a directory move on 2026-09-19 along with every other probe this session had built.
A handle only survives if its referent lives outside the context.

⚑⚑⚑ THE ADDRESS IS ASKED FOR AT PROBE TIME, NEVER WRITTEN HERE. The first version carried
`127.0.0.1:31985` as a constant. On 2026-09-20 the operator retired every loopback NodePort on the
cluster ("Services not NodePorts"), every service became a ClusterIP reached BY NAME through a
systemd dns-delegate on this host, and this probe reported REFUSED for a sink that was UP — a
stale written address read as authoritative, which is exactly how luthen said it would fail.
So the name and port come from luthen's endpoint directory (`checks/endpoints_query.py`), which
carries an `as_of`, and a directory that cannot answer is its own outcome rather than a refusal.

⚑⚑ TCP CONNECT, NOT curl. The sink speaks gRPC, and `curl` returns `http_code=000` to a gRPC
listener WHETHER IT IS HEALTHY OR ABSENT — measured on 2026-09-13, both directions. curl is void
on this port. A connect is the one cheap thing that distinguishes *listening* from *not*.

⚑ AND IT SAYS WHICH OF FOUR, because a probe collapsing outcomes into pass/fail has already
discarded the discriminating bit. `exit 7` (refused) and `exit 1` (reached, wrong protocol) were
different claims on 2026-09-13 and the difference is what settled a three-tick hold.

    python3 bep_probe.py              # ask the directory, then connect
    python3 bep_probe.py HOST:PORT    # connect to a stated address (a control, or a peer's claim)
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path

_LUTHEN = Path("/home/mikemol/github/luthen-observability")
_QUERY = [str(_LUTHEN / ".venv/bin/python"), str(_LUTHEN / "checks/endpoints_query.py")]
_SERVICE = "grpc-bes"


def directory_address() -> tuple[str, int] | None:
    """Ask luthen's endpoint directory for the BES gRPC address, host side.

    Returns:
        `(host, port)` as the directory answers it now, or None when the directory itself
        cannot answer — an absent checkout, a refused name, or unparseable output. ⚑ None is
        reported by the caller as its OWN outcome; it is never turned into a refusal.

    """
    try:
        done = subprocess.run(  # noqa: S603 — a fixed argv into a sibling checkout; nothing untrusted
            [*_QUERY, _SERVICE, "--side", "host"],
            check=False, capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    try:
        answer = json.loads(done.stdout)
        return str(answer["host"]), int(answer["port"])
    except (ValueError, KeyError, TypeError):
        return None


def main(argv: list[str]) -> int:
    """Try one connection and report the outcome by name.

    Returns:
        0 when the sink accepts, 1 when refused, 2 on any other socket error, 3 when the
        directory could not supply an address and none was given.

    """
    if len(argv) > 1:
        host, _, port_text = argv[1].rpartition(":")
        target: tuple[str, int] | None = (host, int(port_text))
        origin = "stated on the command line"
    else:
        target = directory_address()
        origin = "from luthen's endpoint directory"
    if target is None:
        print("BEP sink UNMEASURED — the endpoint directory gave no address "
              f"({' '.join(_QUERY)} {_SERVICE} --side host); pass HOST:PORT to probe one")
        return 3
    host, port = target
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"BEP sink {host}:{port} ACCEPTS ({origin}) — something is listening "
                  "(not proof it is ready)")
            return 0
    except ConnectionRefusedError:
        print(f"BEP sink {host}:{port} REFUSED ({origin}) — nothing is listening on the port")
        return 1
    except OSError as e:
        print(f"BEP sink {host}:{port} UNREACHABLE ({origin}) — {e} "
              "(not a refusal; the route is the subject)")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
