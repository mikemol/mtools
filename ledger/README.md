<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-ledger

A findings ledger whose rows are witnessed by commands. Each finding is OPEN, CLOSED or
UNRUNNABLE. Those three stay distinct: a command that never started is not a command that failed.

Moved from substrate (inbox/2026-09-24-substrate-findings-letter.md): the `finding_*` cluster.
There is no module-level root. Every witness runs in a working directory its caller names.

Stdlib only; no runtime dependencies.
