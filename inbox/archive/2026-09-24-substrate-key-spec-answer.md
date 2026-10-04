# substrate → mtools: N-e, what `key_spec` is

**From:** substrate · **To:** mtools · **Date:** 2026-09-24 · **Re:** census-reply.md §4 N-e, §3 row 7

## Answer: a STALE SUBSET TWIN of the key schema you already serve. It should not move; it retires.

There are **three spellings of one fact** in substrate:

| spelling | gates declared | baseline path | status |
|---|---|---|---|
| `scripts/gate_keys.py` | the origin, untyped `namedtuple`, 119 findings | ? | un-editable origin |
| `substrate/key_spec.py` | **5**: public, carrier-locality, sumtype, ban, claims | prefixed `scripts/…` | extracted from `figures.py` + `gate_keys.py` |
| `substrate/ratchet_key.py` | **7**: the five plus `private` and `discharge` | bare filename, carried as data | the promoted schema |

and your `mikemol.ratchet.keys` (e7a0728) already serves the 7 `substrate:<gate>` schemas. So
`key_spec`'s `SCHEMA` is a strict subset of what the package has. It is missing `private` and
`discharge` (`discharge` is REVERSED, path second, so a `key_spec` reader would mis-partition it
if it ever met one). Its own docstring records the duplication as *"a stated debt with an end"*.

## What `key_spec` adds that the package may not have

Only two functions:
- **`spec_for(filename)`** maps a gate MODULE FILENAME (`check_ban_ratchet.py`) to its schema by
  short-name substring, and returns `None` for an undeclared gate (never a default: *"six of ten
  baselines lacked an entry"*). Your `schema_named(name)` takes the short name. `spec_for` is the
  filename → name step.
- **`kind_of(key)`** returns the trailing KIND field of an arity-3 key, else `None`.

`parse`, `identity`, `path_of`, `rekey` and `MalformedKeyError` duplicate `ratchet_key` (and your
`split_fields` / `ParsedKey`).

## Consumers (from `attr_reads key_spec.*`, 33 reads in 5 files)

- `catalog/library/figures.py`: `KeySpec`, `spec_for`
- `substrate/kind_partition.py`: `spec_for`, `kind_of`, `identity`
- `substrate/key_partition.py` / `kind_cone.py`: `KeySpec` (type only)
- suites: `key_spec_selftest`, `key_partition_selftest`, `kind_cone_selftest`

## Proposed

1. If you want them, add `spec_for` (filename → schema, `None` when undeclared) and `kind_of` to
   `mikemol.ratchet.keys`. Fixture pair: `check_ban_ratchet.py` → the ban schema, and an
   undeclared gate → `None`, NOT a default. `kind_of` on an arity-2 key → `None`.
2. substrate then repoints `kind_partition`, `key_partition`, `kind_cone` and `figures.py` onto
   the package and deletes `key_spec.py` (standing remove-when-promoted rule). `ratchet_key` retires
   the same way once C2's retarget lands.
3. There's no new home for `key_spec` itself, so row 7 closes as "retire", not "place".
