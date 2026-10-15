# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the web-subset allowlist (mtools:W1254): each refusal beside its clean control.

⚑ A RULE THAT FIRES ON EVERYTHING PASSES EVERY PLANT, so each rule is also shown NOT firing on the
nearest legitimate construct: a plain keyword on a class, a method named like a builtin, a float
compared with `<`, a definition with ordinary parameters.
"""

from __future__ import annotations

from mikemol.hooks import websubset

_EVALS = ["eval(x)", "exec(y)", "compile(z, 'f', 'exec')"]
_DYNAMICS = [
    "getattr(o, n)",
    "setattr(o, n, v)",
    "delattr(o, n)",
    "vars(o)",
    "globals()",
    "locals()",
    "o.__dict__",
]
_STARS = ["def f(*args):\n    pass", "def f(**kw):\n    pass", "async def f(*a):\n    pass"]


def _rules(source: str) -> list[str]:
    return [finding.rule for finding in websubset.check(source)]


def test_a_metaclass_keyword_is_refused_and_another_class_keyword_is_not() -> None:
    """`metaclass=` is refused; `flag=1` on a class is an ordinary keyword."""
    assert _rules("class A(B, metaclass=M):\n    pass\n") == ["metaclass"]
    assert _rules("class A(B, flag=1):\n    pass\n") == []


def test_eval_exec_and_compile_calls_are_refused_and_a_method_of_that_name_is_not() -> None:
    """The bare builtin is run-time code; `obj.eval()` is a method and says nothing."""
    assert _rules("\n".join(_EVALS)) == ["eval-exec"] * len(_EVALS)
    assert _rules("obj.eval(x)\nobj.exec(y)\n") == []


def test_dynamic_attribute_calls_and_dunder_dict_are_refused_and_plain_access_is_not() -> None:
    """The getattr family and `__dict__` are refused; `obj.name` is static."""
    assert _rules("\n".join(_DYNAMICS)) == ["dynamic-attribute"] * len(_DYNAMICS)
    assert _rules("o.name\no.method()\n") == []


def test_float_equality_is_refused_on_either_side_and_ordering_is_not() -> None:
    """`x == 1.5`, `1.5 != x` and a chained equality are refused; `<`, `>=` and int `==` pass."""
    assert _rules("x == 1.5\n") == ["float-equality"]
    assert _rules("1.5 != x\n") == ["float-equality"]
    assert _rules("a == b == 2.0\n") == ["float-equality"]
    assert _rules("x < 1.5\nx >= 2.5\nx == 2\n") == []


def test_star_args_in_a_definition_or_a_call_are_refused_and_ordinary_ones_are_not() -> None:
    """`*args`, `**kwargs`, `f(*xs)`, `f(**kw)` and an async def are refused; fixed shapes pass."""
    for source in _STARS:
        assert _rules(source) == ["star-args"]
    assert _rules("f(*xs)\n") == ["star-args"]
    assert _rules("f(**kw)\n") == ["star-args"]
    assert _rules("def f(a, b=1, *, c=2):\n    pass\nf(1, b=2, c=3)\n") == []


def test_source_that_does_not_parse_is_one_syntax_finding_not_an_exception() -> None:
    """The caller gets a row with a line, never a traceback."""
    found = websubset.check("def broken(:\n")
    assert [(f.rule, f.line) for f in found] == [("syntax", 1)]


def test_findings_come_back_in_line_order_and_render_as_one_line() -> None:
    """Two refusals on different lines sort by line; `render` is `line: rule: message`."""
    found = websubset.check("getattr(o, n)\nx = 1\neval(a)\n")
    assert [(f.line, f.rule) for f in found] == [(1, "dynamic-attribute"), (3, "eval-exec")]
    assert found[1].render() == "3: eval-exec: `eval` runs code built at run time"


def test_a_missing_return_or_parameter_type_is_unannotated_and_a_full_signature_is_not() -> None:
    """Each missing annotation is its own finding; a fully annotated def and a lambda are clean."""
    both = websubset.unannotated("def f(a, b: int):\n    pass\n")
    assert [(f.line, f.rule) for f in both] == [(1, "unannotated"), (1, "unannotated")]
    assert [f.message for f in both] == [
        "`f` has no return type",
        "parameter `a` of `f` has no type",
    ]
    assert websubset.unannotated("def f(a: int, *, b: str) -> None:\n    pass\n") == []
    assert websubset.unannotated("g = lambda x: x\n") == []


def test_keyword_only_and_positional_only_parameters_are_checked_and_receivers_are_not() -> None:
    """`self` and `cls` are exempt; a bare keyword-only or positional-only parameter is not."""
    source = (
        "class A:\n"
        "    def m(self, x: int, /, y, *, z) -> None:\n"
        "        pass\n"
        "    @classmethod\n"
        "    def c(cls, w: int) -> None:\n"
        "        pass\n"
    )
    found = websubset.unannotated(source)
    assert [f.message for f in found] == [
        "parameter `y` of `m` has no type",
        "parameter `z` of `m` has no type",
    ]


def test_an_async_def_is_checked_and_unparsable_source_is_one_syntax_finding() -> None:
    """The same rule applies to `async def`; a module that does not parse is a row, not a raise."""
    assert [f.rule for f in websubset.unannotated("async def f(a):\n    pass\n")] == [
        "unannotated",
        "unannotated",
    ]
    assert [(f.rule, f.line) for f in websubset.unannotated("def broken(:\n")] == [("syntax", 1)]


def test_a_clean_module_has_no_findings() -> None:
    """The overall control: annotated, static, integer-comparing code passes untouched."""
    source = "def add(a: int, b: int) -> int:\n    return a + b if a == b else a - b\n"
    assert websubset.check(source) == []
