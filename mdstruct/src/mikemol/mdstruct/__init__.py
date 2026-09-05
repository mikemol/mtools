# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Structural reading and writing of markdown — spans, tables, cells, and section rewrites.

⚑⚑ A `#` INSIDE A FENCE IS NOT A HEADER, WHICH IS THE WHOLE REASON THIS PACKAGE EXISTS. A
`grep '^#'` gets a document's section skeleton MOSTLY right and fails exactly where it matters:
a shell fence full of `#` comments reports phantom headings, and a setext header (`===`
underline) is a header with no leading `#` at all. Every reader here works from pandoc's parsed
document rather than from the lines.

⚑⚑ AND THE SPAN IS THE UNIT, NOT THE LINE. `grep -n` gives a line number and no structure, so a
reader must work out which section it is in before editing safely; a bare structural reader gives
structure and no coordinates, so they must then hunt for the lines. The pair — a header path AND
its line range — is what makes an answer one-shot, and it is the same address the write modes act
on.

⚑ ONE MODULE PER CONCERN, WHICH IS A PACKAGING DECISION AS WELL AS A DESIGN ONE. The subprocess
exemption a linter grants is per FILE, so a module that both ran pandoc and parsed its output
would extend that exemption over both. The split is what keeps each grant honest.

This package was extracted from a 2,526-line single-file tool in another repo, which several
peers had adopted by SYMLINK — an arrangement that broke silently the moment the tool derived its
own root with a call that does not resolve symlinks. A published distribution ends that class of
problem: an installed package knows where it lives.
"""

from __future__ import annotations

import warnings

# ⚑⚑ THE PARSER EMITS A `SyntaxWarning` FROM ITS OWN DOCSTRINGS, ON EVERY IMPORT. panflute's
# `io.py` documents a signature containing `\*\*kwargs` in a non-raw docstring, which Python
# reports as an invalid escape sequence. It is a defect in a dependency's source, not in
# anything a consumer wrote, and nothing a consumer can fix.
#
# ⚑⚑⚑ AND SUPPRESSING IT IS A CORRECTNESS REQUIREMENT HERE, NOT TIDINESS. This package's modes
# are READ BY PROGRAMS — a structural grep's output is parsed, a span list feeds a section
# rewrite — and a warning on stderr rides along with them. A caller capturing both streams gets
# a third-party warning interleaved with the answer.
#
# ⚑ SCOPED TO THE ONE CATEGORY AND THE ONE MODULE, never a blanket. A bare `ignore` would hide a
# `SyntaxWarning` this package's OWN code earns — which is exactly the finding a warning exists
# to deliver, and exactly what a wide suppression would cost.
warnings.filterwarnings("ignore", category=SyntaxWarning, module="panflute.*")
