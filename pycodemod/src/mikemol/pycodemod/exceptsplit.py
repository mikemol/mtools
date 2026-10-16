# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`except (A, B):` rewritten as one handler per exception, each with the same body.

⚑⚑ CODON REJECTS A TUPLE IN AN `except` (probed on 0.20.3, mtools:W1342), AND ACCEPTS SEPARATE
CLAUSES. 104 modules of this tree carry one. The split is exact: Python runs the first clause that
matches and the body of each clause is the original body, so the same exceptions reach the same
code.

    except (OSError, ValueError) as exc:      except OSError as exc:
        log(exc)                          ->      log(exc)
                                              except ValueError as exc:
                                                  log(exc)

⚑ WHAT IT DOES NOT TOUCH: a tuple that is not a plain tuple of names or dotted names (a starred
element, a call, a variable naming a tuple) is listed with its line, since splitting it is no
longer a text move. A bare `except:` and an `except A:` are already the target spelling.

⚑ THE BODY IS DUPLICATED, NOT REFACTORED: a long handler repeated per exception is longer code,
and a caller who minds writes a helper by hand; this verb does not guess one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

_KEPT = "an except tuple with an element that is not a plain name is left as it is"


@dataclass(frozen=True, slots=True)
class Planned:
    """The rewritten text, how many handlers were split, and those left."""

    text: str
    split: int
    kept: tuple[tuple[int, str], ...]


def _plain(element: cst.BaseExpression) -> bool:
    # A name or a dotted name: `ValueError`, `json.JSONDecodeError`.
    if isinstance(element, cst.Name):
        return True
    return isinstance(element, cst.Attribute) and _plain(element.value)


class _Splitter(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.split = 0
        self.kept: list[tuple[int, str]] = []

    def _members(self, handler: cst.ExceptHandler) -> list[cst.BaseExpression] | None:
        # The tuple's elements when the handler's type is a plain tuple, else None.
        kind = handler.type
        if not isinstance(kind, cst.Tuple):
            return None
        elements = [element.value for element in kind.elements]
        if all(_plain(element) for element in elements) and not any(
            isinstance(element, cst.StarredElement) for element in kind.elements
        ):
            return elements
        line = self.get_metadata(PositionProvider, handler).start.line
        self.kept.append((line, _KEPT))
        return None

    @override
    def leave_Try(self, original_node: cst.Try, updated_node: cst.Try) -> cst.Try:
        """Split each tuple handler of a `try` into one handler per exception.

        Returns:
            the `try` with its handlers expanded.

        """
        handlers: list[cst.ExceptHandler] = []
        for before, after in zip(original_node.handlers, updated_node.handlers, strict=True):
            members = self._members(before)
            if members is None:
                handlers.append(after)
                continue
            self.split += 1
            handlers.extend(after.with_changes(type=member) for member in members)
        return updated_node.with_changes(handlers=handlers)


def plan(text: str) -> Planned:
    """Split every plain `except (A, B):` in `text` into one handler per exception.

    Returns:
        the Planned text; unchanged with `split` 0 when there is none.

    """
    splitter = _Splitter()
    changed = MetadataWrapper(cst.parse_module(text)).visit(splitter)
    if not splitter.split:
        return Planned(text, 0, tuple(sorted(splitter.kept)))
    return Planned(changed.code, splitter.split, tuple(sorted(splitter.kept)))
