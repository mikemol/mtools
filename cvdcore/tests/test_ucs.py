# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the public CAM02-UCS conversion (mtools:W1349, for el-openglo:W544).

⚑ THE CONTROLS ARE THE TWO SHAPES AND THE TWO VIEWS: a batch is (N, 3) and its lightness is (N,),
one colour is (3,); the trichromat and a deficiency view disagree about a red, so the view
argument is read and not ignored.
"""

from __future__ import annotations

import numpy as np

from mikemol.cvdcore import ucs, ucs_lightness

_RED = [220.0, 30.0, 40.0]
_BLUE = [20.0, 60.0, 200.0]
_BATCH = np.asarray([_RED, _BLUE])


def test_one_colour_is_three_numbers_and_a_batch_is_n_by_three() -> None:
    """A triple converts to shape (3,); two rows convert to (2, 3)."""
    assert ucs(_RED, None).shape == (3,)
    assert ucs(_BATCH, None).shape == (2, 3)


def test_lightness_is_the_first_column_of_the_conversion_row_by_row() -> None:
    """The batch lightness is (2,) and matches the J' of each colour converted alone."""
    batch = ucs_lightness(_BATCH, "deuteranomaly")
    assert batch.shape == (2,)
    expected = [ucs(_RED, "deuteranomaly").tolist()[0], ucs(_BLUE, "deuteranomaly").tolist()[0]]
    assert batch.tolist() == expected


def test_the_view_argument_changes_the_answer_for_a_red() -> None:
    """The trichromat and a protan view read a red at different lightness."""
    assert ucs_lightness(_BATCH, None).tolist() != ucs_lightness(_BATCH, "protanomaly").tolist()
