# `.claude/` — mtools' own harness

⚑⚑⚑ **mtools SHIPPED A HOOK AND DID NOT RUN IT.** `mikemol-hook-structural-query` is this
repo's only console script, and until this directory was filled nothing here consumed it. The
packager was not a user of its own package — the same shape as a warrant nothing reads, and the
same shape as a gate that reports itself installed while refusing nothing.

## Why the arming is in the COMMAND STRING and not only the `env` block

`settings.json` carries `STRUCT_HOOK_BLOCK` in `env` **and** repeats it inline on every hook
command. That duplication is deliberate and it is the load-bearing part.

⚑⚑ A session already running when `settings.json` changes **never re-reads that env block**, so a
hook armed only there keeps exiting 0 — detecting every violation and reporting none. It reads as
armed in review and is off in fact. Both cassian-observability and linux-sources reached this
independently after measuring it, and `payload.py`'s own docstring records it as the reason the
switch is read per-invocation rather than cached.

## What "armed" means here, at the level the harness actually reads

⚑ An advisory hook writes to **stderr**, which the harness ignores. Only a `permissionDecision:
deny` envelope on **stdout** refuses the call, and an **empty stdout is read as ALLOW** — so a
malformed envelope is a silently-inert gate. `hooks/tests/test_structural_query.py` pins both
directions, and this repo's own arming was verified the same way before the file was written:

    armed,   grep over README.md   -> deny envelope on stdout, names `mdstruct`
    unarmed, grep over README.md   -> stdout EMPTY, advisory on stderr
    armed,   ls -la findings/      -> allowed

⚑⚑ **THE SECOND AND THIRD ARMS ARE NOT DECORATION.** Without the unarmed arm, "the gate denies"
is indistinguishable from a gate that denies unconditionally; without the allow arm, a gate that
refuses every command in a real repo passes review and gets disabled within a day.

## The routing table

`skills/struct-tools/SKILL.md` is the gate's only source of claims, read from the repo being
EDITED rather than from the package's location. An absent table means the gate claims nothing and
refuses nothing — which is correct behaviour (inventing claims for a repo that declared none
applies a bar nobody chose) and is exactly why its absence must not be mistaken for a passing gate.
