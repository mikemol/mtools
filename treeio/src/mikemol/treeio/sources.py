# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The two places a read can be addressed: the working tree, and a git revision.

Ported from paperkit's `tools/vfs.py`. A source is a PARAMETER, not a mode name: a tool takes a
source object and every read in it is uniformly addressed, which is what turns a mode such as
"read at HEAD" into one argument. The working tree is the only WRITABLE source.

A Rev resolves its revision EAGERLY and separately from any path lookup, and that separation is the
whole design. pygit2 raises KeyError for a bad revision and for a missing path alike (measured), so
if the revision were resolved lazily inside the path lookup, one except clause would serve both and
a mistyped sha would report as ABSENT. Resolving first means that by the time a tree lookup runs
the revision is known-good, so a KeyError there can only mean the path. The split is in the order
of operations, not in the exception types.

Unlike paperkit's module, the default root is the current directory at construction, not the
directory above the module: this package has no checkout of its own to default to.
"""

from __future__ import annotations

from pathlib import Path

import pygit2


class WorkingTree:
    """The filesystem as it is right now. The only WRITABLE source."""

    writable = True

    def __init__(self, root: str | Path | None = None) -> None:
        """Fix the directory every relative path is read against.

        Args:
            root: The tree's root; the current directory when omitted.

        """
        self.root = Path(root or Path.cwd()).absolute()

    def __repr__(self) -> str:
        """Render the root, so a refusal naming this source says where it points.

        Returns:
            Text of the form WorkingTree('root').

        """
        return f"WorkingTree({str(self.root)!r})"

    def __str__(self) -> str:
        """Render the plain-language name used in result lines.

        Returns:
            The text working tree.

        """
        return "working tree"


class Rev:
    """A git revision such as HEAD, a sha, or HEAD~3. READ-ONLY BY CONSTRUCTION.

    There is deliberately NO write to a Rev. Git history is not writable, and an API that
    accepted a source on write would be a lie in the type: it would typecheck, read as supported,
    and either silently write to the working tree or rewrite history.
    """

    writable = False

    def __init__(self, rev: str = "HEAD", root: str | Path | None = None) -> None:
        """Name the revision and the repository to resolve it in; nothing is resolved yet.

        Args:
            rev: Any revision spelling pygit2 can parse.
            root: The repository directory; the current directory when omitted.

        """
        self.rev = rev
        self.root = Path(root or Path.cwd()).absolute()
        self._tree: pygit2.Tree | None = None
        self._err: Exception | None = None

    def __repr__(self) -> str:
        """Render the revision spelling.

        Returns:
            Text of the form Rev('spelling').

        """
        return f"Rev({self.rev!r})"

    def __str__(self) -> str:
        """Render the plain-language name used in result lines.

        Returns:
            The text rev followed by the spelling.

        """
        return f"rev {self.rev}"

    def _find(self) -> tuple[pygit2.Tree | None, Exception | None]:
        """Resolve the revision to a tree, uncached.

        A bad revision is BROKEN, not ABSENT: this is the arm the old at_revision collapsed into
        None and the old head-text helper collapsed into an empty string.

        Returns:
            The tree and None, or None and the error that says why it could not be had.

        """
        try:
            repo = pygit2.Repository(str(self.root))
        except (pygit2.GitError, OSError) as e:
            return None, RuntimeError(f"not a git repository at {self.root}: {e}")
        try:
            obj = repo.revparse_single(self.rev)
        except KeyError as e:
            return None, ValueError(f"bad revision {self.rev!r} in {self.root}: {e}")
        except (pygit2.GitError, ValueError) as e:
            return None, RuntimeError(f"cannot resolve {self.rev!r}: {e}")
        try:
            return obj.peel(pygit2.Tree), None
        except (pygit2.GitError, ValueError) as e:
            return None, ValueError(f"revision {self.rev!r} does not name a tree: {e}")

    def resolve(self) -> tuple[pygit2.Tree | None, Exception | None]:
        """Resolve the revision eagerly, once, and cache the answer.

        Returns:
            The tree and None when the revision is good, otherwise None and the error.

        """
        if self._tree is None and self._err is None:
            self._tree, self._err = self._find()
        return self._tree, self._err


type Source = WorkingTree | Rev
