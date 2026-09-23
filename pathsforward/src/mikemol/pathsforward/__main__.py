# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`python -m mikemol.pathsforward`: the console script, reachable without an entry point."""

import sys

from mikemol.pathsforward.cli import main

sys.exit(main())
