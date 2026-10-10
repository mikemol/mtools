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

def paperkit_gate(name, project, engine_repo, engine_files, data, flags = [], env = {}):
    """Declare one test that runs the paperkit gate over `project` with the engine pinned (mtools:W843).

    The engine is the files of a `pinned_files` repository, so the verdict is about a recorded commit
    and never about a sibling's working tree. The project's files are the caller's own named list.

        load("@mikemol_rules_py//:gate.bzl", "paperkit_gate")
        load("@paperkit_engine//:manifest.bzl", "FILES")

        paperkit_gate(name = "library", project = "library", engine_repo = "paperkit_engine",
                      engine_files = FILES, data = select_tracked(TRACKED, prefix = "library/"))

    Args:
        name: the test's name.
        project: the project directory (relative to this package) holding `paper.toml`, or "." for
            a project at the package root.
        engine_repo: the pinned repository's name, as MODULE.bazel gave it.
        engine_files: the FILES list of that repository's manifest.bzl.
        data: the project's named files; `<project>/paper.toml` must be among them.
        flags: extra flags for `paperkit.gate` (for example `--safe`).
        env: extra environment for the gate. paperkit's clean_env carries only `PAPERKIT_*` names into
            a check, so a variable a check must see is spelled that way (`PAPERKIT_TIER = "commit"`).

    Returns:
        The test's label.
    """
    # A project at the package root is spelled "." and its paper.toml has no directory part.
    toml = "paper.toml" if project in ("", ".") else project + "/paper.toml"

    # ⚑ A TEST NAMED LIKE ITS PROJECT DIRECTORY BURIES IT: py_test puts its own executable at
    # `<runfiles>/_main/<name>`, which replaces the data directory of that name, so the project is a
    # file and the gate answers "not a declared input" (measured on resumes, 2026-10-06).
    if name == project.split("/")[0]:
        fail("paperkit_gate: the test %r is named like its project directory; name it gate_%s" % (name, name))
    if toml not in data:
        fail("paperkit_gate: %s names no %s among its data" % (name, toml))
    if "paperkit/gate.py" not in engine_files:
        fail("paperkit_gate: %s: the pinned engine holds no paperkit/gate.py" % name)
    py_test(
        name = name,
        srcs = [
            "@mikemol_rules_py//:paperkit_gate_main.py",
            "@mikemol_rules_py//:engine_env.py",
        ],
        args = [
            "--engine=$(rootpath @%s//:paperkit/gate.py)" % engine_repo,
            "--project=$(rootpath %s)" % toml,
        ] + flags,
        data = data + ["@%s//:%s" % (engine_repo, p) for p in engine_files],
        env = env,
        legacy_create_init = 0,
        main = "@mikemol_rules_py//:paperkit_gate_main.py",
    )
    return ":" + name

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
