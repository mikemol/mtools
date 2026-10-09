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

def dist_checks(venv_data = [], venv_tags = []):
    """Declare `:venv` and `:suite` for the calling distribution's package.

    Args:
        venv_data: files the suite needs beyond tests/**/*.py when venv_check collects it (icsstruct
            stages its .ics fixtures and stubs). Declared here, so a difference stays visible in
            the caller's BUILD and is never normalised away (W376).
        venv_tags: tags for the `:venv` check. audiostruct passes ["exclusive"]: its venv holds
            the multi-GB GPU set, and concurrent sandbox copies overran /dev/shm's quota (W518).
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
        # ⚑ A GENEROUS TIMEOUT, NOT THE 60 s A SMALL TEST GETS (W838; operator: "I hate
        # wallclock-sensitive things"). This check COLLECTS the distribution's whole suite with the
        # built venv, so its time grows with the suite and with the load the gate puts on the box:
        # //hooks:venv timed out at 60.4 s while 24 actions ran beside it and refused a commit
        # (2026-10-06), though it passes alone. The same ruling as //<dist>:mypy.
        timeout = "long",
        tags = venv_tags,
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

    # W389: the ratchet atom's refusal check (W388): a copy of this distribution with a planted
    # finding must be REFUSED by name by the ratchet, so a lowered baseline is never a deletion
    # wearing a paydown's name. It was a test_bar_fires arm walking every distribution.
    py_test(
        name = "ratchet_refusal",
        srcs = ["@mikemol_check_ratchet//:refusal_check.py"],
        main = "@mikemol_check_ratchet//:refusal_check.py",
        args = [
            "$(location //ratchet:ratchet_cli)",
            "$(location @mikemol_check_ruff//:bin)",
            "$(location :pyproject.toml)",
        ],
        data = [
            "pyproject.toml",
            "ratchet-preview.txt",
            "//ratchet:ratchet_cli",
            "@mikemol_check_ruff//:bin",
        ] + native.glob(["src/**/*.py", "tests/**/*.py"], allow_empty = True),
        size = "small",
        # ⚑ The ratchet_cli it runs now carries a sibling (atomicwrite, W857): two source roots plus
        # legacy implicit `__init__.py` files make `mikemol` a regular package from the first root
        # and shadow the namespace (W566), so `mikemol.ratchet` stopped resolving.
        legacy_create_init = 0,
    )

    # W233: every requirements.txt pin (the `_deps` hub's input) agrees with uv.lock (the host
    # venv's and the `_dev` hub's), so the two resolvers cannot drift silently. W232 found hooks'
    # ast-serialize at 0.9.0 against 0.11.1 by hand; this makes that a red target.
    py_test(
        name = "reqs",
        srcs = ["@mikemol_rules_py//:reqs_check.py"],
        main = "@mikemol_rules_py//:reqs_check.py",
        args = [dist],
        data = ["requirements.txt", "uv.lock"],
        size = "small",
    )

    # W503: this distribution's test modules, for the root's //:vacuity_floor, which counts
    # population negatives over the union of every distribution (most hold none, so the floor
    # means nothing per distribution).
    native.filegroup(
        name = "test_modules",
        srcs = native.glob(["tests/test_*.py"], allow_empty = True),
        visibility = ["//:__pkg__"],
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
