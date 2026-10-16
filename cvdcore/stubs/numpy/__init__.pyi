# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# The numpy surface cvdcore uses: asarray, the array's shape, copy, subtraction and division.

from numpy import linalg as linalg

class ndarray:
    shape: tuple[int, ...]
    def copy(self) -> ndarray: ...
    def tolist(self) -> list[float]: ...  # one-dimensional arrays only, as cvdcore uses it
    def __sub__(self, other: ndarray) -> ndarray: ...
    def __truediv__(self, other: float) -> ndarray: ...

def asarray(a: object, dtype: type[float] = ...) -> ndarray: ...
