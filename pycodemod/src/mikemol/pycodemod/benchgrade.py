# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W2113: grade `narrowing` against a hand-annotated file, parameter by parameter.

    grade(before_source, after_source)   # {"f.cfg": "exact", "f.n": "none", ...}
    totals(grades)                       # {"exact": 17, "narrower": 14, "none": 82, "differ": 4}

⚑ THE WITNESS FOR W2111 AND W2112 (el-openglo's benchmark, graded at W1925): the BEFORE file has
no annotations, the AFTER file is the hand-annotated one. For each parameter the after file
annotates, `narrowing.uses_of(before)` gives the form the body supports, and the annotation's
head name is compared with it:

    exact       the annotation is the form narrowing named
    narrower    narrowing named a Protocol and the hand annotation is a concrete class
    none        narrowing showed nothing (`unconstrained`)
    differ      anything else

A parameter missing from the before file is not graded. This module reads sources; fetching them
by sha is the caller's work, so the grader stays a pure function.
"""

import ast

from mikemol.pycodemod import narrowing

GRADES = ("exact", "narrower", "none", "differ")
_CONCRETE = frozenset(
    {"str", "int", "float", "bool", "bytes", "list", "dict", "set", "tuple", "frozenset", "Path"}
)
_NAMED = frozenset({"protocol", "typeddict"})
_HEADS = {
    "str": frozenset({"str"}),
    "ndarray": frozenset({"NDArray", "ndarray"}),
    "mapping": frozenset({"Mapping", "MutableMapping", "dict"}),
    "sequence": frozenset({"Sequence", "list", "tuple"}),
    "iterable": frozenset({"Iterable", "Iterator", "Collection", "Sequence", "list"}),
    "sized": frozenset({"Sized", "Collection", "Sequence", "list", "dict"}),
    "callable": frozenset({"Callable"}),
}


def head(annotation: ast.expr) -> str:
    """Name an annotation by its outermost name.

    Returns:
        `NDArray` for `NDArray[np.float64]`, `str` for `str`, `X` for `"X"`; empty if none fits.

    """
    node = annotation.value if isinstance(annotation, ast.Subscript) else annotation
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.split("[")[0].split(".")[-1]
    if isinstance(node, ast.Attribute):
        return node.attr
    return node.id if isinstance(node, ast.Name) else ""


def classify(form: narrowing.Narrowed, name: str) -> str:
    """Compare the form narrowing named with a hand annotation's head name.

    Returns:
        `exact`, `narrower`, `none` or `differ`.

    """
    if form.kind == "unconstrained":
        return "none"
    if name in _HEADS.get(form.kind, frozenset()):
        return "exact"
    if form.kind in _NAMED and name not in _CONCRETE and name[:1].isupper():
        return "exact"
    if form.kind == "protocol" and name in _CONCRETE:
        return "narrower"
    return "differ"


def annotations_of(source: str) -> dict[str, dict[str, str]]:
    """Read each function's annotated parameters, keyed like `narrowing.uses_of`.

    Returns:
        `{"Class.method": {"param": head}}`, only parameters that carry an annotation.

    """
    found: dict[str, dict[str, str]] = {}

    def walk(body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                walk(node.body, f"{prefix}{node.name}.")
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                args = node.args
                every = [*args.posonlyargs, *args.args, *args.kwonlyargs]
                found[f"{prefix}{node.name}"] = {
                    a.arg: head(a.annotation) for a in every if a.annotation is not None
                }

    walk(ast.parse(source).body, "")
    return found


def grade(before: str, after: str) -> dict[str, str]:
    """Grade every parameter the after file annotates and the before file has.

    Returns:
        `{"function.param": grade}`.

    """
    uses = narrowing.uses_of(before)
    graded: dict[str, str] = {}
    for function, params in annotations_of(after).items():
        for param, name in params.items():
            use = uses.get(function, {}).get(param)
            if use is not None:
                graded[f"{function}.{param}"] = classify(narrowing.narrow(use), name)
    return graded


def totals(grades: dict[str, str]) -> dict[str, int]:
    """Count the grades.

    Returns:
        how many parameters earned each of the four grades.

    """
    return {g: sum(1 for v in grades.values() if v == g) for g in GRADES}
