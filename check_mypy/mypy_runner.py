# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run mypy as a py_binary, so the checker is a declared input rather than a host tool.

⚑ A `py_console_script_binary` would regenerate mypy's own entry point, and mypy DOES declare one.
This is the plainer form for the same effect: the wrapper's only job is to hand argv to mypy's
`console_entry`, and it exists because `mypy_check.sh` needs one executable path to invoke.
"""

from __future__ import annotations

import sys

from mypy.main import main

if __name__ == "__main__":
    main()
    sys.exit(0)
