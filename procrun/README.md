<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-procrun

The one place a child process is started (mtools:W873), extracted from `mikemol.treeio.proc` so a
caller that only needs to start a child does not inherit treeio's native git dependency. A library:
no console script, standard library only.

| module | does |
|---|---|
| `mikemol.procrun.proc` | `capture(argv, cwd, env, timeout)` runs `argv` to completion, output as text |

Behaviour: the argv is a sequence, never a shell string; a non-zero status is a value, not a raise;
the working directory and the whole environment are the ones passed; a child that outlasts its
`timeout` raises `subprocess.TimeoutExpired`, and with no timeout nothing is bounded.
