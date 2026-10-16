# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# The one colorspacious name cvdcore uses: cspace_convert.

from numpy import ndarray

def cspace_convert(
    arr: ndarray, start: str | dict[str, object], end: str | dict[str, object]
) -> ndarray: ...
