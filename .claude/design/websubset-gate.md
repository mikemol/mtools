# The web-subset gate (mtools:W1070 and its children)

A module that will be transpiled to the web may not use what the transpiler cannot translate. The
gate is a pure check plus one declared list; nothing here takes a waiver.

| piece | where | card |
|---|---|---|
| allowlist: metaclass, eval/exec/compile, getattr family and `__dict__`, float `==`/`!=`, star-args | `hooks/src/mikemol/hooks/websubset.py` `check` | W1254 |
| required annotations: every def and parameter, `self`/`cls` exempt | same file, `unannotated` | W1255 |
| the one tracked list of portable modules, read whole or refused | `hooks/websubset-portable.txt`, `websubset_list.py` | W1256, W1075 |
| `mikemol-websubset --check-file PATH`, `--census ROOT [--jsonl F] [--counts F]` | `websubset_cli.py` | W1257, W1076 |
| card sync, one card per module with findings | recipe below, no new code | W1077 |

## Card sync (W1077): a recipe, because the machinery already existed

`mikemol-debtplan mint` already syncs one card per debt file (title `<prefix><file> (<n> findings)`,
`--touches` tags, retire when the row leaves the ledger, a card being worked keeps its status), and
takes `--prefix` and `--touches` as values. The census writes the per-file ledger it reads, so no
second card generator exists:

    python3 -m mikemol.hooks.websubset_cli --census ROOT --counts LEDGER.json
    mikemol-debtplan mint --root ROOT --ledger LEDGER.json --state ROOT/.claude/paths-forward.json \
        --prefix "websubset: " --touches portable-subset

Run 2026-10-15 over mtools with the list empty: census `0 module(s), 0 finding(s)`, mint
`added 0, rewrote 0, retired 0`. That proves the two tools agree on the ledger shape end to end; a
non-empty run waits for the first module to be put on the list (a reviewed edit of
`hooks/websubset-portable.txt`, the first consumer being gcalculus per W1076's ruling).

## What is not built

- The list is empty: nothing is opted in, so the gate guards nothing yet.
- `mikemol-websubset` is not in the commit gate; wiring it in is a separate decision once a module
  is listed.
- The transpile step itself is W1071 (py2many), unrelated to this check.
