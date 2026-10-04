# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The executor IMAGE digests a verdict is keyed on.

Ported from paperkit's `tools/image_digest.py` (paperkit:W142). Behaviour unchanged; the directory
and the child-process runner are parameters so a test plants a directory and a fake runner.

Every remote verdict is a function of the paper AND of the image it ran in, so the image's
identity must be in the action key: a rebuilt image must re-run the check, an unchanged one must
hit.  There are TWO images, one per pool (tools/pool.bzl):

    default pool   `buildbuddy-executor`  - luthen's thin image (python + strace): the SWEEP's
                                            substrate; every sandbox cell (pk_calc) runs here
    paperkit pool  `paperkit-executor`    - the render toolchain (image/executor/Containerfile);
                                            every `toolchain`-tier check runs here

MEASURED 2026-09-21, the reason the default pool is keyed too: strace was added to the default
image and `boundaries//:gate --config=mutant --config=remote` returned `113 action cache hit` -
the four read-footprint calc baselines refuted against the strace-less image were served back as
hits, because a sandbox cell's key carried nothing about the image.  A cache hit is fine when the
key is sound (operator); this key was not.

Digests are not authored here - luthen-observability declares them (images.json) and answers by
NAME through its own query, so a field change on their side breaks their query, not a parser of
mine.  Same discipline as `project_endpoints`.

    mikemol-image-digest paperkit-executor    # prints `sha256:...`, or `absent`
    mikemol-image-digest buildbuddy-executor

`absent` is a STABLE value, not an error: on a host without the pools nothing runs remotely, so no
verdict is ever produced under it to be mis-cached.  Read by tools/toolchain_status.sh.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.buildtel import proc

if TYPE_CHECKING:
    from collections.abc import Callable

DIRECTORY = Path("/home/mikemol/github/luthen-observability")
IMAGES = ("paperkit-executor", "buildbuddy-executor")
ABSENT = "absent"


def digest(image: str, run: proc.Runner = proc.capture, directory: Path = DIRECTORY) -> str:
    """Ask luthen-observability's image query for `image`'s digest.

    Returns:
        the digest, or `absent` when the query is not installed, fails, prints nothing, or
        does not answer.

    Raises:
        SystemExit: when `image` is not one of `IMAGES`.

    """
    if image not in IMAGES:
        msg = f"image_digest: unknown image {image!r}; known: {', '.join(IMAGES)}"
        raise SystemExit(msg)
    query = directory / "checks" / "images_query.py"
    python = directory / ".venv" / "bin" / "python"
    if not query.is_file() or not python.is_file():
        return ABSENT
    status, out, _err = run([str(python), str(query), image])
    if status != 0 or not out.strip():
        return ABSENT
    rec: object = json.loads(out)
    if not isinstance(rec, dict):
        return ABSENT
    state: object = rec.get("state")
    found: object = rec.get("digest")
    if state == "answered" and isinstance(found, str) and found:
        return found
    return ABSENT


def main(argv: list[str] | None = None, lookup: Callable[[str], str] = digest) -> int:
    """Print the digest of the named image (default `paperkit-executor`).

    Returns:
        0.

    """
    args = sys.argv[1:] if argv is None else argv
    sys.stdout.write(lookup(args[0] if args else IMAGES[0]) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
