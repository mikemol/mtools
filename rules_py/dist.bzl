# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The per-distribution checks, declared together so a distribution cannot carry one without the other.

W373: `:venv` (W342) and `:suite` (W362) were hand-copied blocks in each distribution's BUILD, so
nothing stopped a distribution having one and not the other, and the count of wired distributions
was something to grep for rather than something declared. The model is `test_bar_fires`'
`_distributions()`: a distribution is a directory carrying a `pyproject.toml`. Each one calls this
macro once, and the pair comes with it.

⚑ The distribution name is `native.package_name()`, never an argument: a hand-typed name is how
W370's first draft passed a literal `{dist}` to all nine suite checks.
"""

load("@rules_python//python:defs.bzl", "py_test")

def dist_checks(venv_data = []):
    """Declare `:venv` and `:suite` for the calling distribution's package.

    Args:
        venv_data: files the suite needs beyond tests/**/*.py when venv_check collects it (icsstruct
            stages its .ics fixtures and stubs). Declared here, so a difference stays visible in
            the caller's BUILD and is never normalised away (W376).
    """
    dist = native.package_name()

    # W342: the built venv, checked by venv_check. The tests are staged too, because the check
    # collects the distribution's own suite with the venv.
    native.sh_test(
        name = "venv",
        srcs = ["@mikemol_rules_py//:venv_check.sh"],
        args = [
            "$(location :pyproject.toml)",
            "$(location @mikemol_rules_py//:venv_check.py)",
        ],
        data = [
            "pyproject.toml",
            ":.venv",
            "@mikemol_rules_py//:venv_check.py",
        ] + native.glob(["tests/**/*.py"]) + venv_data,
        size = "small",
    )

    # W386: the ruff atom's two config checks (W384, W385), run over this distribution with the
    # pinned ruff. They were test_bar_fires arms walking every distribution from the root, and
    # the suppression arm read hooks/tests alone.
    py_test(
        name = "ruff_selector",
        srcs = ["@mikemol_check_ruff//:selector_check.py"],
        main = "@mikemol_check_ruff//:selector_check.py",
        args = [
            "$(location @mikemol_check_ruff//:bin)",
            "$(location :pyproject.toml)",
        ],
        data = ["pyproject.toml", "@mikemol_check_ruff//:bin"],
        size = "small",
    )
    py_test(
        name = "ruff_suppression",
        srcs = ["@mikemol_check_ruff//:suppression_check.py"],
        main = "@mikemol_check_ruff//:suppression_check.py",
        args = ["$(location @mikemol_check_ruff//:bin)", dist],
        # ⚑ src/ AND tests/, never `**`: a source-tree `.venv` would be swept as the package.
        data = [
            "pyproject.toml",
            "@mikemol_check_ruff//:bin",
        ] + native.glob(["src/**/*.py", "tests/**/*.py"], allow_empty = True),
        size = "small",
    )

    # W362: the BUILD names pytest as every py_test's main, and no test resolves __file__ out of
    # the sandbox.
    py_test(
        name = "suite",
        srcs = ["@mikemol_rules_py//:suite_check.py"],
        main = "@mikemol_rules_py//:suite_check.py",
        args = [dist],
        data = ["BUILD.bazel"] + native.glob(["tests/test_*.py"]),
        size = "small",
    )
