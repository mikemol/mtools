# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A pre-commit gate as a list of named python stages, each one py_test (mtools:W804).

rosettapkg:W122 and gcalculus:W91 each hand-wrote the same loop: one py_test per gate script, every
tracked file named as its data, `legacy_create_init = 0`, and a `:precommit` test_suite for the hook
to run. substrate:W300's hook is thirty-odd more of the same shape. This is that loop, once.

    load("@mikemol_rules_py//:gate.bzl", "gate_stages")
    load("@mikemol_rules_py//:tracked.bzl", "select_tracked")
    load("@tracked//:manifest.bzl", "TRACKED")

    gate_stages(
        stages = {
            "no_noqa_we_own": ("scripts/noqa_census.py", ["--quiet"]),
            "census": ("scripts/census.py", ["--population=$(rootpath @tracked//:tracked.txt)"],
                       ["@tracked//:tracked.txt"]),
        },
        data = select_tracked(TRACKED),
    )

- A stage is `(script, args)` or `(script, args, extra_data)`: `extra_data` is for a label the args
  name through `$(rootpath ...)`, which must also be a declared input.
- Inputs are named files, never a glob and never a directory (operator 2026-10-06): the caller
  passes the named list, usually from `select_tracked`.
- The script is the stage's `main` and its only `srcs`: the script finds its inputs relative to
  itself, as it does under the hook, so the files stay in the caller's own package.
- A stage whose name collides with another rule in the package fails at load, naming the stage.
"""

load("@rules_python//python:py_test.bzl", "py_test")

def gate_stages(stages, data, suite = "precommit"):
    """Declare one py_test per stage and a test_suite running them all.

    Args:
        stages: {name: (script, args)} or {name: (script, args, extra_data)}, in the order the
            hook ran them.
        data: the named input files every stage sees.
        suite: the test_suite's name, which the hook invokes as `bazel test //:<suite>`.

    Returns:
        The labels of the declared tests, in stage order.
    """
    if not stages:
        fail("gate_stages: no stages: an empty gate would pass without checking anything")
    labels = []
    for name, spec in stages.items():
        if len(spec) not in (2, 3):
            fail("gate_stages: stage %r is %d-tuple; want (script, args) or (script, args, extra_data)" % (name, len(spec)))
        script = spec[0]
        args = spec[1]
        extra = spec[2] if len(spec) == 3 else []
        py_test(
            name = name,
            srcs = [script],
            args = args,
            data = data + extra,
            legacy_create_init = 0,
            main = script,
        )
        labels.append(":" + name)
    native.test_suite(name = suite, tests = labels)
    return labels
