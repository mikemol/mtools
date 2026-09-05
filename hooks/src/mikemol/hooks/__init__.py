# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""PreToolUse hooks: refuse the query, the mutation, the composition, the un-linted edit.

⚑⚑ A HOOK THAT CANNOT LOAD IS A HOOK THAT ALLOWS EVERYTHING, and the harness cannot tell the
difference. Emitting nothing reads as permission granted — so every module here fails LOUD: it
says what it could not import, states that it is checking nothing, and exits non-blocking rather
than vanishing. That failure mode was found by an ADOPTER, not by review.

⚑⚑⚑ AND THAT IS WHY THIS IS A PACKAGE RATHER THAN A DIRECTORY OF SCRIPTS. These hooks were
adopted across repos by SYMLINK, and a symlinked script derives its own root from `__file__` —
which `abspath` does not resolve, so the root became the CONSUMER's repo. A peer's adopted tool
failed on every invocation, and the cause was neither their code nor a refactor but a latent
property of being reached through a link. An installed package knows where it lives and declares
what it needs; neither is available to a file someone linked.

⚑ WHAT EACH HOOK REFUSES, and each refusal names its successor rather than merely denying:

    structural_query   a textual query over a structured artifact — naming the owning tool
    no_chaining        a shell composition where one tool call belongs
    shellcheck         a shell edit with findings, with no suppression path
    pycheck            a Python edit that would leave the file dirty

⚑ THE CONFIG FOLLOWS THE EDITED FILE, NOT THE HOOK. A checker resolves its rules by walking up
from the file it is handed, so a hook that names its OWN project applies one repo's bar to
another repo's code — invisible while a session edits one tree, wrong in both directions the
moment it edits two.
"""

from __future__ import annotations
