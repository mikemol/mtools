# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Draft a commit message from one waypoint (W493).

⚑ A DRAFT, NEVER A COMMIT: this prints text for a human or a tick to edit. The subject is the
title, the body carries caused_by, the latest evidence entry and the L2 fields (W492), and the
trailer names the waypoint. ⚑ A MISSING L2 FIELD IS SAID, NOT HIDDEN: each prints
`# thin: no <field>`, a line git strips from an edited message, so the gap is visible to the
writer and absent from the commit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward.model import strlist, text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json

L2_FIELDS = ("unchanged", "rejected", "consumers")
EVIDENCE_SEP = " | "


def latest_evidence(w: Json) -> str:
    """Read the newest entry of a waypoint's evidence.

    Returns:
        the text after the last separator, or "" when there is no evidence.

    """
    return text(w, "evidence").rsplit(EVIDENCE_SEP, 1)[-1].strip()


def draft(w: Json) -> str:
    """Draft the commit message for one waypoint.

    Returns:
        the message, ending in a newline.

    """
    body: list[str] = []
    cause = text(w, "caused_by")
    if cause:
        body.append(f"Caused by: {cause}")
    evidence = latest_evidence(w)
    if evidence:
        body.append(evidence)
    thin: list[str] = []
    for field in L2_FIELDS:
        items = strlist(w, field)
        if items:
            body.append("\n".join([f"{field.capitalize()}:", *(f"- {i}" for i in items)]))
        else:
            thin.append(f"# thin: no {field}")
    if thin:
        body.append("\n".join(thin))
    parts = [text(w, "title"), *body, f"Waypoint: {text(w, 'symbol')}"]
    return "\n\n".join(parts) + "\n"
