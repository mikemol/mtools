# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The house mypy flags, handed as a flag set rather than read from each project's config (W1536).

⚑ THE OPERATOR RULED ON 2026-10-17 that typing debt is measured against the house flags (strict plus
`disallow_any_*`), over each project's own config, and that a project's gate may still gate on its
own. The census (`pycheck_census`) judges a file by the edit gate's verdict, which uses the
project's config, so a repo with a weaker config than the house standard (el-openglo: 36,933
findings in 193 files under these flags, none under its own) reads as having no debt.

⚑ THE SET IS THE ROOT `pyproject.toml` `[tool.mypy]` HOUSE BLOCK, written out as argv words, so a
checkout with no mtools root beside it (an adopter) still has it. `MYPY_HOUSE_KEYS` names the keys
the block sets, and a test compares the argv words to them, so the two cannot drift silently.
CONSUMED BY: `pycheck` (the optional mypy flag set) and `pycheck_cli` (`--census --house`).
"""

MYPY_HOUSE_KEYS = (
    "strict",
    "extra_checks",
    "strict_equality",
    "disallow_any_decorated",
    "disallow_any_explicit",
    "disallow_any_expr",
    "warn_unused_ignores",
    "warn_unreachable",
)

ERROR_CODES = ("ignore-without-code", "redundant-expr", "truthy-bool")


def mypy_flags() -> tuple[str, ...]:
    """Return the house mypy flags as argv words, in a fixed order.

    Returns:
        one `--flag` word per boolean key, then one `--enable-error-code` pair per code.

    """
    booleans = tuple("--" + key.replace("_", "-") for key in MYPY_HOUSE_KEYS)
    codes = tuple(word for code in ERROR_CODES for word in ("--enable-error-code", code))
    return (*booleans, *codes)
