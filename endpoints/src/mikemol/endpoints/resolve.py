# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Resolve a NAMED endpoint to a URL through the host's own file (W1419).

⚑⚑ NO ADDRESS IS IN MTOOLS. `MIKEMOL_ENDPOINTS` holds the PATH of a JSON file the host writes,
`{"victorialogs-http": "http://host:port"}`, so a port change moves that file and nothing here.

⚑ EVERY FAILURE IS "NO ANSWER" (`None`), NEVER AN EXCEPTION: an unset variable, an unreadable file,
a file that is not JSON, one that is not an object, an unknown name, a value that is not a string
and a scheme other than http(s) all return None. A caller decides what a blind answer means.

⚑ ONE IMPLEMENTATION OF TWO (W1419): `fence.reading.endpoint_url` (W919) and
`otlp.endpoints.base_url` (W1418) each carried this body because neither dist depended on the
other. Both now import this one; the two copies were the same contract written twice.

CONSUMED BY: mikemol-fence and mikemol-otlp.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

ENV = "MIKEMOL_ENDPOINTS"
HOME_FILE = ".config/mikemol/endpoints.json"
SCHEMES = frozenset({"http", "https"})


def endpoints_path(environ: Mapping[str, str]) -> str | None:
    """Name the host's endpoints file: the variable's path, else the file luthen publishes (W1528).

    ⚑ A SESSION CARRIES NO `MIKEMOL_ENDPOINTS` (luthen-observability, 2026-10-18: no mikemol.*
    series reached the store from any session), so an unset variable falls back to
    `$HOME/.config/mikemol/endpoints.json`, the file the host already writes. `HOME` is read from
    the environment passed in, never from the process, so a caller with no `HOME` gets no answer.

    Returns:
        the path, or None when neither the variable nor `HOME` is set.

    """
    path = environ.get(ENV)
    if path:
        return path
    home = environ.get("HOME")
    return str(Path(home) / HOME_FILE) if home else None


def base_url(name: str, environ: Mapping[str, str]) -> str | None:
    """Resolve an endpoint name through the host's file.

    Returns:
        the base URL, or None when no endpoints file is named, it is unreadable, it holds no such
        name or the value is not an http(s) URL.

    """
    path = endpoints_path(environ)
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
    if not isinstance(url, str):
        return None
    try:
        scheme = urlsplit(url).scheme
    except ValueError:
        return None
    return url if scheme in SCHEMES else None
