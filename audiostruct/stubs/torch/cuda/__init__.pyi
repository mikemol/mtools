# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑ The one torch call audiostruct makes: gpu.release's second step, after gc.collect (W269).

def empty_cache() -> None: ...
