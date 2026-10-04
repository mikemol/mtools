<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-atomicwrite

paperkit's durable-write primitive, ported here (mtools:W555). A library: no console script.

| module | does |
|---|---|
| `mikemol.atomicwrite.durable` | `write_atomic(path, data)` writes a sibling temp and renames it over `path` |

The module keeps paperkit's name, so a caller repoints `from paperkit import durable` to
`from mikemol.atomicwrite import durable`.

Behaviour: the PATH is replaced, not the inode's contents (a hardlinked twin keeps its old bytes);
a reader sees the whole old or the whole new file; an existing target's permissions are preserved
while a new file gets the umask default; the sibling temp is removed if anything fails.
