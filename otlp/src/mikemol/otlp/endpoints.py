# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Resolve a NAMED endpoint to a URL through the host's own file (W1418; luthen's request).

⚑⚑ NO ADDRESS IS IN MTOOLS. `MIKEMOL_ENDPOINTS` names a JSON file `{"victorialogs-http":
"http://host:port"}` that the host writes (luthen-observability's `user/published_endpoints.json`),
so a port change moves the file and nothing here. This is the contract of `fence.reading.
endpoint_url` (W919), which was read before this was written: the environment variable holds the
file's PATH; an unreadable file, an unknown name and a scheme other than http(s) are all "no
answer" (None), never an exception.

⚑ A SECOND IMPLEMENTATION, RECORDED AS ONE: fence's copy returns the base the same way and the two
could be one shared function; neither dist depends on the other, so the consolidation is a card, not
a quiet merge.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

ENV = "MIKEMOL_ENDPOINTS"
_SCHEMES = frozenset({"http", "https"})


def base_url(name: str, environ: Mapping[str, str]) -> str | None:
    """Resolve an endpoint name through the host's file.

    Returns:
        the base URL, or None when the variable is unset, the file is unreadable, it holds no such
        name or the value is not an http(s) URL.

    """
    path = environ.get(ENV)
    if not path:
        return None
    try:
        doc: object = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
        return None
    if not isinstance(doc, dict):
        return None
    url = cast("dict[object, object]", doc).get(name)
    if not isinstance(url, str) or urlsplit(url).scheme not in _SCHEMES:
        return None
    return url


def url_for(name: str, path: str, environ: Mapping[str, str]) -> str | None:
    """Build the full URL of one signal: the named endpoint's base plus the signal's path.

    Returns:
        the URL, or None when the name does not resolve.

    """
    base = base_url(name, environ)
    return None if base is None else base.rstrip("/") + path
