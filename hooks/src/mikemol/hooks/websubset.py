# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The web-subset allowlist: what a module marked web-portable may not contain (mtools:W1254).

⚑ A MODULE THAT WILL BE TRANSPILED CANNOT USE WHAT THE TRANSPILER CANNOT TRANSLATE. This is the
pure half of the gate: it reads one module's source and returns every construct on the refusal list,
with its line. No file, no policy, no waiver: a finding is fixed by changing the module, never by
marking the finding. (The list of which modules are portable is W1256, the annotation rule W1255,
the command line W1257.) The name avoids pycodemod's `portable` mode, which is about SQL literals.

The refusal list, each a rule id that a test plants beside a clean control:

    metaclass          a `metaclass=` keyword on a class
    eval-exec          a call to `eval`, `exec` or `compile`
    dynamic-attribute  a call to `getattr`, `setattr`, `delattr`, `vars`, `globals` or `locals`,
                       or a use of `__dict__`
    float-equality     `==` or `!=` with a float literal on either side
    star-args          `*args` or `**kwargs` in a definition, or `*x` / `**x` at a call

⚑ SYNTAX THAT DOES NOT PARSE IS A FINDING, NOT AN EXCEPTION: a module the gate cannot read is not
portable, and the caller should see a row, not a traceback.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

_EVAL = frozenset({"eval", "exec", "compile"})
_DYNAMIC = frozenset({"getattr", "setattr", "delattr", "vars", "globals", "locals"})
_TODAY = frozenset({"metaclass", "eval-exec", "dynamic-attribute", "float-equality", "star-args"})
DEFAULT_TARGET = "py2many"

# ⚑ ONE REFUSAL LIST PER TRANSPILE TARGET (mtools:W1322): what py2many cannot translate and what
# Codon cannot compile are different sets. Both start on today's five rules; a target's list is
# narrowed or widened by editing its own row, and a rule removed from one still fires for the other.
# `syntax` is no rule of a target: a module that does not parse is refused by every target.
RULES: dict[str, frozenset[str]] = {DEFAULT_TARGET: _TODAY, "codon": _TODAY}


@dataclass(frozen=True)
class Finding:
    """One refused construct: where, which rule, and what to do about it."""

    line: int
    rule: str
    message: str

    def render(self) -> str:
        """Render the finding as one line.

        Returns:
            `line: rule: message`.

        """
        return f"{self.line}: {self.rule}: {self.message}"


def _name(node: ast.expr) -> str | None:
    return node.id if isinstance(node, ast.Name) else None


def _float(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, float)


def _call(node: ast.Call) -> list[Finding]:
    """Name the refusals a call carries.

    Returns:
        the findings for an eval-family or dynamic-attribute call and for starred arguments.

    """
    found: list[Finding] = []
    name = _name(node.func)
    if name in _EVAL:
        found.append(Finding(node.lineno, "eval-exec", f"`{name}` runs code built at run time"))
    if name in _DYNAMIC:
        text = f"`{name}` names members at run time"
        found.append(Finding(node.lineno, "dynamic-attribute", text))
    starred = any(isinstance(arg, ast.Starred) for arg in node.args)
    if starred or any(kw.arg is None for kw in node.keywords):
        found.append(Finding(node.lineno, "star-args", "a starred argument has no static shape"))
    return found


def _definition(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    """Name the refusals a function definition carries.

    Returns:
        a star-args finding for `*args` or `**kwargs`.

    """
    if node.args.vararg is not None or node.args.kwarg is not None:
        return [Finding(node.lineno, "star-args", f"`{node.name}` takes *args or **kwargs")]
    return []


def _compare(node: ast.Compare) -> list[Finding]:
    operands = [node.left, *node.comparators]
    equality = any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops)
    if equality and any(_float(operand) for operand in operands):
        return [Finding(node.lineno, "float-equality", "equality against a float literal")]
    return []


def _order(finding: Finding) -> tuple[int, str]:
    return finding.line, finding.rule


def check(source: str, target: str = DEFAULT_TARGET) -> list[Finding]:
    """List every construct of one module's source that `target` refuses.

    Returns:
        the findings in line order; a single `syntax` finding when the source does not parse.

    """
    refused = RULES[target]
    return [f for f in _scan(source) if f.rule == "syntax" or f.rule in refused]


def _scan(source: str) -> list[Finding]:
    """Find every construct on the full refusal list, whatever the target.

    Returns:
        the findings in line order; a single `syntax` finding when the source does not parse.

    """
    try:
        tree = ast.parse(source)
    except SyntaxError as fault:
        return [Finding(fault.lineno or 0, "syntax", "the module does not parse")]
    found: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and any(kw.arg == "metaclass" for kw in node.keywords):
            found.append(Finding(node.lineno, "metaclass", f"`{node.name}` names a metaclass"))
        elif isinstance(node, ast.Call):
            found += _call(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found += _definition(node)
        elif isinstance(node, ast.Compare):
            found += _compare(node)
        elif isinstance(node, ast.Attribute) and node.attr == "__dict__":
            found.append(Finding(node.lineno, "dynamic-attribute", "`__dict__` is a dynamic view"))
    return sorted(found, key=_order)


def _missing(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    """Name the missing annotations of one definition.

    ⚑ `self` AND `cls` ARE THE ONE EXEMPTION, as a type checker treats them: their type is the
    class they sit in. Every other parameter, positional or keyword-only, and the return, is named.

    Returns:
        one finding for a missing return and one per unannotated parameter.

    """
    found: list[Finding] = []
    if node.returns is None:
        found.append(Finding(node.lineno, "unannotated", f"`{node.name}` has no return type"))
    args = node.args
    for param in [*args.posonlyargs, *args.args, *args.kwonlyargs]:
        if param.annotation is None and param.arg not in {"self", "cls"}:
            text = f"parameter `{param.arg}` of `{node.name}` has no type"
            found.append(Finding(param.lineno, "unannotated", text))
    return found


def unannotated(source: str) -> list[Finding]:
    """List every definition of one module that lacks a type annotation.

    ⚑ A TRANSPILER TYPES FROM THE ANNOTATIONS, so an unannotated parameter has no target type. A
    lambda has no annotation syntax and is not a definition here: its parameters are the dynamic
    kind this module's allowlist is about, not this rule.

    Returns:
        the findings in line order; a single `syntax` finding when the source does not parse.

    """
    try:
        tree = ast.parse(source)
    except SyntaxError as fault:
        return [Finding(fault.lineno or 0, "syntax", "the module does not parse")]
    found: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found += _missing(node)
    return sorted(found, key=_order)
