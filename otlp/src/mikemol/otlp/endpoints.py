# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Resolve a NAMED endpoint to a URL through the host's own file (W1418; luthen's request).

⚑⚑ NO ADDRESS IS IN MTOOLS. `MIKEMOL_ENDPOINTS` names a JSON file `{"victorialogs-http":
"http://host:port"}` that the host writes (luthen-observability's `user/published_endpoints.json`),
so a port change moves the file and nothing here.

⚑ THE RESOLVER IS SHARED (W1419): `base_url` is `mikemol.endpoints.resolve.base_url`, the one body
that this module and `fence.reading.endpoint_url` (W919) each carried before. Fence keeps its own
copy because it declares no runtime dependencies on purpose (MODULE.bazel), and a parity test pins
the two together.
"""

from collections.abc import Mapping

from mikemol.endpoints.resolve import ENV, base_url

__all__ = ["ENV", "base_url", "url_for"]


def url_for(name: str, path: str, environ: Mapping[str, str]) -> str | None:
    """Build the full URL of one signal: the named endpoint's base plus the signal's path.

    Returns:
        the URL, or None when the name does not resolve.

    """
    base = base_url(name, environ)
    return None if base is None else base.rstrip("/") + path
