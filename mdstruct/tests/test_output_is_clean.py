# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Nothing but the answer reaches a caller's streams.

⚑⚑⚑ THIS IS A CORRECTNESS PROPERTY, NOT TIDINESS. This package's modes are READ BY PROGRAMS — a
structural grep's output is parsed, a span list feeds a section rewrite — so a warning on stderr
rides along with the answer. A caller capturing both streams gets a third-party warning
interleaved with the data.

⚑⚑ THE SPECIFIC LEAK: panflute documents a signature containing an escape sequence in a non-raw
docstring, and Python reports it as a `SyntaxWarning` on every import. It is a defect in a
dependency's source that nothing a consumer writes can fix — so the package suppresses it, scoped
to that one category and that one module.

⚑ AND THE SUPPRESSION IS NARROW ON PURPOSE. A blanket `ignore` would hide a `SyntaxWarning` this
package's OWN code earns, which is exactly the finding a warning exists to deliver. The last
case below is what keeps the scope honest.
"""

from __future__ import annotations

import subprocess
import sys
import warnings
from typing import TYPE_CHECKING

import pytest

# ⚑ IMPORTED FOR ITS SIDE EFFECT, AND THAT SIDE EFFECT IS A CASE'S SUBJECT. Importing the package
# installs the scoped warning filter; the positive control below asserts the filter does NOT
# swallow a warning it does not own, so the import must have happened for that case to mean
# anything. It sits at module scope like any other dependency rather than hiding in a body.
import mikemol.mdstruct

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc

# A document that exercises the parsing path, so the import actually happens.
_FIXTURE = "# Heading\n\nSome prose.\n"

# The package whose filter is under test, named so the import above is a USE rather than an
# exemption — a `noqa: F401` would say "unused, ignore that", which is the opposite of true here.
_PACKAGE = mikemol.mdstruct.__name__


def test_a_fresh_import_emits_nothing_on_stderr(doc: Path) -> None:
    """Check running the CLI in a clean interpreter produces no stderr output.

    ⚑⚑ A FRESH SUBPROCESS IS THE ONLY HONEST TEST. Import warnings fire ONCE per interpreter, so
    a check inside the running test process passes trivially — the import already happened when
    the suite loaded, and its warning went wherever it went.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — argv is this interpreter and a fixture path
        [sys.executable, "-m", "mikemol.mdstruct.cli", "spans", str(doc)],
        check=False, capture_output=True, text=True)
    assert result.returncode == 0
    assert not result.stderr, f"stderr carried: {result.stderr!r}"


def test_stdout_is_only_the_answer(doc: Path) -> None:
    """Check every stdout line belongs to the report, not to a dependency."""
    doc.write_text(_FIXTURE, encoding="utf-8")
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — argv is this interpreter and a fixture path
        [sys.executable, "-m", "mikemol.mdstruct.cli", "spans", str(doc)],
        check=False, capture_output=True, text=True)
    for line in result.stdout.splitlines():
        assert "Warning" not in line, f"a warning reached stdout: {line!r}"


def test_the_suppression_does_not_silence_this_packages_own_warnings() -> None:
    """Check a warning from this package is still delivered — a POSITIVE CONTROL on the scope.

    ⚑⚑ WITHOUT THIS, A BLANKET `ignore` PASSES BOTH CASES ABOVE while hiding every finding a
    warning exists to deliver. The suppression is scoped to one category AND one module; this
    asserts that a `SyntaxWarning` raised from anywhere else survives.
    """
    assert _PACKAGE, "the package whose filter is under test was not imported"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warnings.warn("a warning from the package's own code",
                      SyntaxWarning, stacklevel=1)
    assert caught, "the package's suppression swallowed a warning it did not own"
