# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The refusals a mutation contract raises, derived from BaseException on purpose.

Ported from paperkit's `tools/edit_snapshot.py`. The rule a reader applies, stated once: every
refusal reachable from a def another module IMPORTS raises a subclass of `MutationContractError`;
`sys.exit` survives only at a command-line entry point, where the process genuinely is that
script's to end. The dividing line is not "is it dangerous", it is WHO OWNS THE PID: no script
should assume it is the sole owner of the current pid.
"""

from __future__ import annotations


class MutationContractError(BaseException):
    """The base of every refusal this package RAISES rather than exits on.

    It derives from BaseException, and that is a measurement, not a preference. The obvious cut,
    deriving from Exception so a caller's existing handlers can contain it, was written and then
    reverted against a census: thirty-one callers wrapped the snapshot guard in the shape

        try:
            guard(label, [path], intent="apply")
        except Exception as e:
            report that the snapshot is unavailable and name the error
        # ... and the tool then WRITES ANYWAY

    Those handlers mean "a snapshot is best-effort" and are right about that. But a mutation
    contract refusal is not a failed snapshot, and an Exception subclass is indistinguishable from
    one at that handler. Deriving from Exception would convert a hard refusal into an advisory
    print with the write still happening.

    The two properties of SystemExit are separable, and only one was ever the defect. It unwinds
    the whole interpreter, killing a caller's process: THE DEFECT. It is invisible to an except
    clause for Exception, so a fail-closed refusal stays closed: LOAD-BEARING. Deriving from
    BaseException keeps the second and drops the first: the refusal propagates as an ordinary
    exception a frame can catch BY NAME, and never ends a pid this package does not own.

    Containment is available, it just has to be stated: an except clause for this class (or for
    BaseException) catches it, an except clause for Exception deliberately does not.
    """


class AmbientVocabError(MutationContractError):
    """An out-of-vocabulary value offered to an ambient's `set`.

    It is not also a ValueError, though it reads like one. ValueError derives from Exception, and
    Python resolves a handler by the MRO, so a dual base would be caught by the best-effort
    handlers above and re-open the hole the base class exists to close. The kind is chosen by WHO
    MUST BE ABLE TO CATCH IT, not by what it resembles.
    """
