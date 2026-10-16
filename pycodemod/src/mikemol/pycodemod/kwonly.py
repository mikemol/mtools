# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""A bare `*,` marker dropped, so keyword-only parameters become positional-or-keyword.

⚑⚑ CODON REJECTS A BARE `*,` IN A SIGNATURE (probed on 0.20.3, mtools:W1340), AND ACCEPTS THE
PARAMETERS BEHIND IT AS ORDINARY ONES. 87 modules of this tree carry the marker.

    def run(path, *, write, root=None):    ->    def run(path, write, root=None):

⚑ THE REWRITE IS A SUPERSET OF THE CALLS: a call that passed those parameters by keyword still
binds, and a positional call that was an error now binds. What is lost is the enforcement that they
be named, which a call site that matters can restore by naming them. A caller that wants the
enforcement kept does not run this verb on that signature.

⚑ A PARAMETER WITHOUT A DEFAULT MAY NOT FOLLOW ONE WITH A DEFAULT, and keyword-only parameters
may; so `def f(a, b=1, *, c)` has no plain spelling. Such a signature is listed with its line and
left. A `*args` marker is not bare and is never touched; `**kwargs` stays last.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

_KEPT = "a keyword-only parameter without a default follows one with a default: left as it is"


@dataclass(frozen=True, slots=True)
class Planned:
    """The rewritten text, how many signatures lost the marker, and those left."""

    text: str
    dropped: int
    kept: tuple[tuple[int, str], ...]


def _orderable(parameters: cst.Parameters) -> bool:
    # True when positional-only, ordinary and keyword-only parameters in one row keep every
    # default-less parameter ahead of the first defaulted one.
    row = [*parameters.posonly_params, *parameters.params, *parameters.kwonly_params]
    seen = False
    for param in row:
        if param.default is not None:
            seen = True
        elif seen:
            return False
    return True


class _Dropper(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.dropped = 0
        self.kept: list[tuple[int, str]] = []

    @override
    def leave_Parameters(
        self, original_node: cst.Parameters, updated_node: cst.Parameters
    ) -> cst.Parameters:
        """Merge the keyword-only parameters into the ordinary ones when the marker is bare.

        Returns:
            the parameters without the marker, or unchanged when it is not bare or cannot go.

        """
        bare = isinstance(updated_node.star_arg, cst.ParamStar) and updated_node.kwonly_params
        if not bare:
            return updated_node
        if not _orderable(updated_node):
            line = self.get_metadata(PositionProvider, original_node).start.line
            self.kept.append((line, _KEPT))
            return updated_node
        self.dropped += 1
        merged: list[cst.Param] = [*updated_node.params, *updated_node.kwonly_params]
        no_keyword_only: list[cst.Param] = []
        return updated_node.with_changes(
            params=merged, star_arg=cst.MaybeSentinel.DEFAULT, kwonly_params=no_keyword_only
        )


def plan(text: str) -> Planned:
    """Drop every bare `*,` marker in `text` that can go.

    Returns:
        the Planned text; unchanged with `dropped` 0 when there is none.

    """
    dropper = _Dropper()
    changed = MetadataWrapper(cst.parse_module(text)).visit(dropper)
    if not dropper.dropped:
        return Planned(text, 0, tuple(sorted(dropper.kept)))
    return Planned(changed.code, dropper.dropped, tuple(sorted(dropper.kept)))
