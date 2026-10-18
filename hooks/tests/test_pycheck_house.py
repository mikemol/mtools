# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The house mypy flag set is complete, ordered and spelled as mypy takes it (W1536)."""

from mikemol.hooks import pycheck_house

_FLAG_COUNT = 14


def test_every_house_key_is_one_double_dash_word() -> None:
    """Each boolean key becomes its own flag, with underscores as hyphens."""
    words = pycheck_house.mypy_flags()
    for key in pycheck_house.MYPY_HOUSE_KEYS:
        assert "--" + key.replace("_", "-") in words
    assert "--disallow-any-expr" in words
    assert "--strict" in words


def test_each_error_code_follows_its_enable_flag() -> None:
    """An error code is passed as a pair, so no code is read as a flag of its own."""
    words = pycheck_house.mypy_flags()
    for code in pycheck_house.ERROR_CODES:
        at = words.index(code)
        assert words[at - 1] == "--enable-error-code"


def test_the_set_is_stable_and_has_no_repeats() -> None:
    """The same call gives the same words in the same order, and none twice but the flag name."""
    first = pycheck_house.mypy_flags()
    assert first == pycheck_house.mypy_flags()
    booleans = [word for word in first if word != "--enable-error-code"]
    assert len(booleans) == len(set(booleans))
    assert len(first) == _FLAG_COUNT
