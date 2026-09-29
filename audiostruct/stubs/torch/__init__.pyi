# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑ EMPTY ON PURPOSE, and it SHADOWS the real torch for mypy (W284). torch ships py.typed, but
# under the strict block its annotations carry Any throughout, and the light mypy environment has no
# torch at all. audiostruct calls exactly one torch function, `torch.cuda.empty_cache`, declared in
# cuda/__init__.pyi and held to the real torch by tests/test_stub_authority.py.
