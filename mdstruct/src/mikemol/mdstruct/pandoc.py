# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run pandoc — the ONE conversion point, and the only subprocess in this package.

⚑⚑ THIS IS ITS OWN MODULE BECAUSE RUNNING PANDOC IS ONE RESPONSIBILITY. The `S603` exemption a
subprocess needs is granted per FILE, so a module that also parsed, or read sections, or rendered
results would extend that exemption over every one of them. The argv here is `pandoc` plus format
names from a fixed vocabulary — the document travels on stdin as data and never becomes a word in
the command.

⚑⚑ RE-ATTACHING FRONTMATTER IS CORRECT ONLY FOR A MARKDOWN WRITER, and doing it unconditionally
broke EVERY AST mode on any `---`-fenced document for the life of the original tool: `-t json`
got the YAML head prepended, so the parser read a document opening with `---` and died at char
0 — the header, table, row, item and coherence modes all blind to frontmatter'd markdown, which
in practice is every governed document.

⚑ DIAGNOSED BY A CONSUMER, NOT BY THE OWNER. A downstream repo reported it and deliberately did
NOT patch their own copy, because they had adopted the tool by symlink and a local fix would have
forked the body silently. The owner is the party who can fix it, and the owner could not see it
from inside — which is one of the reasons this is a published package now rather than a file
peers symlink.

⚑ `pandoc` IS A SYSTEM BINARY, NOT A WHEEL. It cannot be a declared dependency, so every consumer
needs it installed; the tests report a DECLARED SKIP when it is absent rather than passing
silently, and this module raises rather than returning an empty string.
"""

from __future__ import annotations

import os
import subprocess

from mikemol.mdstruct import frontmatter

# ⚑ THE WRITERS THAT READ BACK AS MARKDOWN — the predicate this re-attaches on. A PREFIX tuple,
# not an equality set: callers pass a bare family name, but pandoc accepts `markdown_strict`,
# `commonmark_x`, and `+ext`/`-ext` suffixes on any of them. An equality check would silently
# stop preserving frontmatter the first time someone asked for a dialect.
MD_WRITERS = ("markdown", "commonmark", "gfm")

# How much of pandoc's stderr to carry into a raised error: enough to name the failure, bounded
# so a malformed document cannot flood a caller's context.
_ERR_CHARS = 400


def convert(src: str, to: str, frm: str = "markdown") -> str:
    """Convert `src` with pandoc; `to` may carry writer FLAGS after the format name.

    ⚑ THE WRAPPING FLAGS DECIDE IDEMPOTENCE for a table-dense document, so they must be
    reachable from the caller. Passing the whole string as one `-t` argument makes pandoc read
    `--columns=999` as an extension name and refuse.

    ⚑ A FAILED CONVERSION RAISES RATHER THAN RETURNING EMPTY. An empty return reads as an empty
    document, and a caller writing that back would truncate the file it was converting.
    """
    head, body = frontmatter.split(src)
    parts = (to or "markdown").split()
    # ⚑⚑ A DECLARED BINARY WINS OVER PATH. Under bazel `PANDOC_BIN` names a hash-pinned input
    # staged into the sandbox; unset, PATH answers as before. Reading PATH first would let a
    # hermetic action quietly use a host binary nobody declared — the sandbox escape this repo
    # already refuses for editable installs, one layer down.
    binary = os.environ.get("PANDOC_BIN") or "pandoc"
    cmd = [binary, "-f", frm, "-t", parts[0], *parts[1:]]
    proc = subprocess.run(cmd, input=body, capture_output=True, text=True, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip()[:_ERR_CHARS])
    stdout: str = proc.stdout
    return (head + stdout) if parts[0].startswith(MD_WRITERS) else stdout
