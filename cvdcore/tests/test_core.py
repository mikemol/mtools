# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the CVD core: the seven arms of el-openglo's selftest at 9a4be98, as tests."""

from __future__ import annotations

from mikemol.cvdcore import OKABE_ITO, VIEWS, reference_floor, reference_floors, rgb, worst_view_dE

_VERMILLION = (213, 94, 0)
_ORANGE = (230, 159, 0)
_BLUE = (0, 114, 178)
_VIEW_COUNT = 4
_EPSILON = 1e-9
_FLOOR = 10.970861586090177
_TOLERANCE = 1e-6
_NAVY_BLUE = 21.520282241768665


def test_the_measurement_can_see_a_collapse() -> None:
    """A vermillion and an orange are closer than a vermillion and a blue, so the minimum varies."""
    close, _ = worst_view_dE(_VERMILLION, _ORANGE)
    far, _ = worst_view_dE(_VERMILLION, _BLUE)
    assert close < far


def test_identical_colours_are_at_distance_zero() -> None:
    """The control: the same colour twice is no distance apart; the first view, trichromat, wins."""
    distance, view = worst_view_dE((1, 2, 3), (1, 2, 3))
    assert distance < _EPSILON
    assert view == "trichromat"


def test_a_pair_the_trichromat_view_collapses_is_measured_in_that_view() -> None:
    """A dark navy against a saturated blue is closest to the trichromat, not to a deficiency.

    Found by search (seed 1, 400 random pairs): the first of four whose worst view is the
    trichromat, which pins the plain sRGB1 conversion that the deficient views do not exercise.
    """
    distance, view = worst_view_dE((42, 39, 78), (29, 15, 207))
    assert view == "trichromat"
    assert abs(distance - _NAVY_BLUE) < _TOLERANCE


def test_the_okabe_ito_floor_is_the_value_the_original_computed() -> None:
    """Pinned against el-openglo's cvd_core at 9a4be98: orange and purple under tritanomaly."""
    distance, first, second, view = reference_floor()
    assert (first, second, view) == ("orange", "purple", "tritanomaly")
    assert abs(distance - _FLOOR) < _TOLERANCE


def test_four_views_are_read() -> None:
    """The trichromat and the three simulated deficiencies."""
    assert len(VIEWS) == _VIEW_COUNT
    assert VIEWS[0] is None


def test_the_collapsing_view_is_named() -> None:
    """The second value is the view that collapses the pair, a name and never an empty string."""
    _, view = worst_view_dE(_VERMILLION, _ORANGE)
    assert view in {"trichromat", "protanomaly", "deuteranomaly", "tritanomaly"}


def test_the_okabe_ito_floor_names_two_palette_members() -> None:
    """The tightest pair inside the palette is two of its members."""
    floor = reference_floor()
    assert (floor[1] in OKABE_ITO, floor[2] in OKABE_ITO) == (True, True)
    assert floor[1] != floor[2]


def test_the_floor_is_a_positive_distance_and_is_stable() -> None:
    """Positive, and the memoised second call returns the same tuple."""
    assert reference_floor()[0] > 0
    assert reference_floor() == reference_floor()


def test_the_per_class_floors_are_the_one_number_twice() -> None:
    """Both classes carry the single tightest distance, which is not the whole tuple."""
    floors = reference_floors()
    assert set(floors) == {"enforced", "surfaced"}
    assert len({*floors.values()}) == 1
    assert floors["enforced"] == reference_floor()[0]


def test_rgb_parses_a_comma_triple() -> None:
    """A comma-separated colour becomes its integers."""
    assert rgb("1,2,3") == (1, 2, 3)


def test_a_repeated_measurement_through_the_memo_is_unchanged() -> None:
    """The memoised conversions give the same answer on the second ask, after other asks."""
    before = worst_view_dE(_VERMILLION, _ORANGE)
    worst_view_dE(_BLUE, _ORANGE)
    assert worst_view_dE(_VERMILLION, _ORANGE) == before
