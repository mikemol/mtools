<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-pycodemod

Structural queries over Python source: where a name is called, read, bound or asserted. It is the
tool the structural-query hook and the struct-tools skill route textual questions to.

This is a cleanroom rebuild of substrate's `scratch/pycodemod.py` and its siblings
(inbox/2026-09-25-substrate-pycodemod-port-letter.md), done module by module against a differential
with the origin. Its organising rule: every query distinguishes **found none** from **could not
look**. The origin returned a confident zero in at least four shapes: an f-string's text, an
unreadable file, a missing libcst, and a dotted `--calls` target.

The tree a query reads is always an operand. There is no module-level root.
