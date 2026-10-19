# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The --update-many help names every selector the writer accepts, so no session builds a list."""

import pytest

from mikemol.pathsforward import bulkblock, cli


def test_the_help_names_each_selector_the_writer_accepts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A selector the writer takes but the help omits is a hand-built list waiting to happen."""
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    flat = " ".join(capsys.readouterr().out.split())
    for selector in (bulkblock.UNSCORED, bulkblock.UNMANIFESTED, bulkblock.OPEN):
        assert f"`{selector}`" in flat
