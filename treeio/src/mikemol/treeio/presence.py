# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The three-valued answer of a read: present, absent, or broken.

Ported from paperkit's `tools/vfs.py`. Three hand-rolled implementations of "read this file as it
was at a revision" disagreed about what ABSENCE means: one collapsed absent, bad revision, not a
repository and git missing into one None; one collapsed absent into empty; one used a third path
strategy. The three answers are distinct and the distinction is the product:

    PRESENT  a blob is there; its data is bytes, possibly empty.
    ABSENT   not at that source: the one legitimate no.
    BROKEN   bad revision, not a repository, decode failure, permission: never silently a miss.

A lookup that fell back to a default for an unknown name would re-create the bug, so `of` REFUSES
an unknown name rather than defaulting.

Not an `enum.Enum`, though paperkit's class is shaped like one: members of an Enum are built when
the class body runs, which puts every method out of the mutation gate's reach. The three members
are module-level instances assigned onto the class, as paperkit did.
"""

from __future__ import annotations

from typing import ClassVar


class Presence:
    """PRESENT, ABSENT or BROKEN: the distinction three call sites lost.

    A member compares equal to its own name as a string, so a caller that has not migrated and
    writes `p == "ABSENT"` keeps working: the lift is additive.
    """

    PRESENT: ClassVar[Presence]
    ABSENT: ClassVar[Presence]
    BROKEN: ClassVar[Presence]

    def __init__(self, name: str, *, is_defect: bool, gloss: str) -> None:
        """Make one member.

        Args:
            name: The member's name, which is also what it compares equal to as a string.
            is_defect: True when the answer means the read did not happen.
            gloss: One line saying what the answer means.

        """
        self.name = name
        self.is_defect = is_defect
        self.gloss = gloss

    def __eq__(self, other: object) -> bool:
        """Compare by name, against another member or against a bare string.

        Returns:
            True when the names agree.

        """
        return self.name == (other.name if isinstance(other, Presence) else other)

    def __hash__(self) -> int:
        """Hash by name, so a member and its name collide as dictionary keys do.

        Returns:
            The hash of the member's name.

        """
        return hash(self.name)

    def __lt__(self, other: Presence | str) -> bool:
        """Order by name, against another member or a bare string.

        Returns:
            True when this name sorts before the other.

        """
        return self.name < (other.name if isinstance(other, Presence) else other)

    def __str__(self) -> str:
        """Render as the bare name.

        Returns:
            The member's name.

        """
        return self.name

    def __repr__(self) -> str:
        """Render as a constructor-like string.

        Returns:
            Text of the form Presence('NAME').

        """
        return f"Presence({self.name!r})"

    @classmethod
    def all(cls) -> tuple[Presence, ...]:
        """Return the roster, which is the definition itself so no member can be omitted.

        A selftest asking whether every arm is starved cannot omit a member the way a hand-typed
        tuple can.

        Returns:
            Every member, in the order PRESENT, ABSENT, BROKEN.

        """
        return (cls.PRESENT, cls.ABSENT, cls.BROKEN)

    @classmethod
    def of(cls, name: str) -> Presence:
        """Resolve a name, REFUSING an unknown one.

        An unrecognised state silently reading as PRESENT is the false-green shape.

        Returns:
            The member with that name.

        Raises:
            KeyError: when no member carries the name.

        """
        for member in cls.all():
            if member.name == name:
                return member
        known = ", ".join(member.name for member in cls.all())
        msg = f"unknown presence {name!r}; known: {known}"
        raise KeyError(msg)


Presence.PRESENT = Presence(
    "PRESENT",
    is_defect=False,
    gloss="a blob exists at this path in this source; .data is bytes, possibly b''",
)
Presence.ABSENT = Presence(
    "ABSENT",
    is_defect=False,
    gloss=(
        "not there at that source — the ONE legitimate miss, and NOT the same as a zero-byte file"
    ),
)
Presence.BROKEN = Presence(
    "BROKEN",
    is_defect=True,
    gloss=(
        "bad rev, not a repo, decode failure, permission — the read did not happen. "
        "NEVER silently a miss; .error carries the cause"
    ),
)
