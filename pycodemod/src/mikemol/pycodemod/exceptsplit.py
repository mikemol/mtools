# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`except (A, B):` rewritten into a spelling Codon accepts, by one of two exact forms.

⚑⚑ CODON REJECTS A TUPLE IN AN `except` (probed on 0.20.3, mtools:W1342), AND ACCEPTS BOTH FORMS
BELOW. 104 modules of this tree carry one.

    except (OSError, ValueError) as exc:      LAST HANDLER: one clause, the test moved inside
        log(exc)                          ->      except Exception as exc:
                                                      if not isinstance(exc, (OSError, ValueError)):
                                                          raise
                                                      log(exc)

    except (A, B):  (not the last handler)    NOT LAST: one clause per exception, the body repeated
        body                              ->      except A: body
                                                  except B: body

⚑ WHY TWO FORMS. Repeating a body per exception is always exact, but it multiplies branches and
returns (a five-exception tuple around `return key` became seven returns and tripped ruff's limit,
measured on ratchet). The one-clause form keeps the body once, but `except Exception` would take
an exception that a LATER sibling clause meant to catch, so it is used only for the LAST handler of
its `try`, where nothing follows to be starved. A tuple that names a `BaseException`-only class
(`KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, `CancelledError`, `BaseException`) catches
`BaseException` in the one-clause form, so it is not narrowed.

⚑ WHAT IT DOES NOT TOUCH: a tuple that is not a plain tuple of names or dotted names (a starred
element, a call, a variable naming a tuple) is listed with its line, since splitting it is no
longer a text move. A bare `except:` and an `except A:` are already the target spelling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

_KEPT = "an except tuple with an element that is not a plain name is left as it is"
_BASE_ONLY = frozenset(
    {"BaseException", "KeyboardInterrupt", "SystemExit", "GeneratorExit", "CancelledError"}
)
_FALLBACK = "caught"


@dataclass(frozen=True, slots=True)
class Planned:
    """The rewritten text, how many handlers were rewritten, and those left."""

    text: str
    split: int
    kept: tuple[tuple[int, str], ...]


def _plain(element: cst.BaseExpression) -> bool:
    # A name or a dotted name: `ValueError`, `json.JSONDecodeError`.
    if isinstance(element, cst.Name):
        return True
    return isinstance(element, cst.Attribute) and _plain(element.value)


def _last_name(element: cst.BaseExpression) -> str:
    if isinstance(element, cst.Attribute):
        return element.attr.value
    return element.value if isinstance(element, cst.Name) else ""


def _one_clause(handler: cst.ExceptHandler, kind: cst.Tuple) -> cst.ExceptHandler:
    # `except Exception as exc:` with the membership test as the body's first statement.
    names = [_last_name(element.value) for element in kind.elements]
    broad = "BaseException" if _BASE_ONLY & set(names) else "Exception"
    bound = (
        handler.name.name.value
        if handler.name and isinstance(handler.name.name, cst.Name)
        else None
    )
    name = bound or _FALLBACK
    shown = cst.Module(body=[]).code_for_node(kind)
    guard = cst.parse_statement(f"if not isinstance({name}, {shown}):\n    raise\n")
    body = handler.body
    inner: list[cst.BaseStatement] = (
        [guard, *body.body] if isinstance(body, cst.IndentedBlock) else []
    )
    named = handler.name or cst.AsName(
        name=cst.Name(name), whitespace_before_as=cst.SimpleWhitespace(" ")
    )
    return handler.with_changes(
        type=cst.Name(broad), name=named, body=body.with_changes(body=inner)
    )


class _Splitter(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.split = 0
        self.kept: list[tuple[int, str]] = []

    def _plain_tuple(self, handler: cst.ExceptHandler) -> cst.Tuple | None:
        # The handler's tuple when it is a plain one (names only, no star), else None.
        kind = handler.type
        if not isinstance(kind, cst.Tuple):
            return None
        starred = any(isinstance(element, cst.StarredElement) for element in kind.elements)
        if not starred and all(_plain(element.value) for element in kind.elements):
            return kind
        line = self.get_metadata(PositionProvider, handler).start.line
        self.kept.append((line, _KEPT))
        return None

    @override
    def leave_Try(self, original_node: cst.Try, updated_node: cst.Try) -> cst.Try:
        """Rewrite each plain tuple handler of a `try`, by the form its position allows.

        Returns:
            the `try` with its tuple handlers rewritten.

        """
        handlers: list[cst.ExceptHandler] = []
        last = len(original_node.handlers) - 1
        pairs = zip(original_node.handlers, updated_node.handlers, strict=True)
        for index, (before, after) in enumerate(pairs):
            kind = self._plain_tuple(before)
            if kind is None:
                handlers.append(after)
                continue
            self.split += 1
            if index == last:
                handlers.append(_one_clause(after, kind))
            else:
                handlers.extend(after.with_changes(type=member.value) for member in kind.elements)
        return updated_node.with_changes(handlers=handlers)


def plan(text: str) -> Planned:
    """Rewrite every plain `except (A, B):` in `text`, one exact form per position.

    Returns:
        the Planned text; unchanged with `split` 0 when there is none.

    """
    splitter = _Splitter()
    changed = MetadataWrapper(cst.parse_module(text)).visit(splitter)
    if not splitter.split:
        return Planned(text, 0, tuple(sorted(splitter.kept)))
    return Planned(changed.code, splitter.split, tuple(sorted(splitter.kept)))
