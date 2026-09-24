<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-witness

The witness contract: a witness YIELDS rows. Each part is yielded as it is found, and the
verdict comes last. A verdict carries no size, because under one walk the count is what the
collector forwarded. An unknown state reads as open.

Moved from substrate (inbox/2026-09-24-substrate-witness-batch-letter.md): the row contract
(`witness_row`) and declared witness families (`witness_family`). The witness half of
substrate's warrant split follows.

Stdlib only; no runtime dependencies.
