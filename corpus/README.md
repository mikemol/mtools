<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-corpus

Which Python files are a tree's corpus, asked of the tree the caller names.

Moved from substrate (inbox/2026-09-24-substrate-corpus-batch-letter.md). One design change came
with the move: substrate found its root from the module's own location, which, installed, is the
virtualenv. Here every function that walks a tree takes that tree as an argument, with no
default, so an installed copy cannot silently census itself.

Stdlib only; no runtime dependencies.
