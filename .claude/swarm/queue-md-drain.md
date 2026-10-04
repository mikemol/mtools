# queue.md drain audit (2026-10-04, read-only)

Method: queue.md read in full (928 lines); waypoint titles read from `--queue` (8 open: W579 W580 W581 W582 W319 W317 W576 W504; all others done);
coverage probed with `--scan-literal` and `--show`. Ledger-only hits do NOT count as coverage (the ledger is not a work tracker).
Open waypoints cover none of the items below (W317/W319/W504/W576 = repo split; W579-W582 = inbound-asks hook, lock refresh).

## Table

| item (queue.md line) | status | covering waypoint | proposed title / blocked_on / evidence (UNCOVERED only) |
|---|---|---|---|
| "OPEN: whether every distribution's dev deps include fence" (L14) | OPEN | UNCOVERED (scan "dev deps" 0 hits) | T: "Measure whether every distribution's dev deps include mikemol-fence, since mutate_runner keeps a local git filter only because fence imports only in fence's venv" / blocked_on none / evidence: b63b548 kept the local filter; W154 done |
| item 6 residue: "the arm skips under bazel" (L22) | OPEN | UNCOVERED (W155 done, landed e805eab) | T: "venv.bzl console-script preamble: the venv arm skips under bazel; measure why and either arm it or record the reason" / evidence: commitSB/e805eab |
| item 6 residue: preamble uses `readlink -f` (L23) | OPEN, re-verified | UNCOVERED | T: "rules_py/venv.bzl line 211 preamble calls readlink -f (GNU-only); decide portable form or record Linux-only" / evidence: rules_py/venv.bzl:211 at 8c4ed39 |
| item 6 residue: `_relative_path` has no callers (L23) | OPEN, re-verified (only the def at rules_py/venv.bzl:230) | UNCOVERED | T: "Delete rules_py/venv.bzl _relative_path, which has no callers" / evidence: grep of rules_py shows only the def line |
| item 7 AWAITING substrate parity result (L28) | DONE-with-evidence | W425 done, W429 done (parity reached, substrate pinned 6c242bb, repoint in progress), W427 peaks, W428 parity text, W143 done (2cfbdf7) | none; substrate's own repoint/`git rm` is substrate's. Possible residue: none |
| item 7 cosmetic: bash status prints "MB" (L252) | OBSOLETE | bash client retired (W426/W429, operator 2026-10-02) | none |
| item 8 AWAITING substrate repoint of Selftest.mk / delete scratch/transcriptstruct.py (L47-49) | OPEN (peer-side) | UNCOVERED (scan "Selftest.mk" 0 hits; W158/W170 done cover the port only) | T: "Confirm substrate repointed Selftest.mk and its 7 tmi_* tools to mikemol-transcriptstruct and deleted scratch/transcriptstruct.py" / blocked_on substrate:<its W33 card> (agent) / evidence: queue L47-49, port e571b02, substrate's W33 |
| item 8 `tool_result:tool_reference` 80 undecoded, "real" (L53) | OPEN | UNCOVERED (ledger-only hit) | T: "transcriptstruct: decode tool_result tool_reference blocks (80 undecoded on the measured transcript)" / evidence: queue L53; Stats.unknown_types ec95472 |
| item 8 TS1-c decoders for queue-operation/system/file-history (L40-46, L54) | DONE (decided no decoders, with reasons) | decision recorded in queue; no waypoint, but nothing owed | none (queue L54 "Open decisions: TS1-c" is stale vs the DECIDED text above it) |
| item 8 TS1-d invalid UTF-8 (L54, L413) | DONE 09151ef | no waypoint titled; evidence in ledger; closed by commit | none |
| item 9 census batch rows 1-7 (L65-71, L127-260) | DONE | W24 evidence lists 4f1afc2..f9f0789, 631cc60, b993e42, 09d0e2d..45c8d35, b8b3e41, 7196dc1, 7ebad9b | none |
| item 10 residue: no_verify's own shlex split; one parser for all hooks (L72) | OPEN | UNCOVERED (scan "shlex" 0 hits; W339/W318 only say test_no_verify stays in mtools' gate) | T: "no_verify keeps its own shlex split; move it onto cmdparse so every hook shares one parser" / evidence: 778acf7; cmdparse.separate_lines 274ed7e |
| item 10 N1 multi-line no_chaining (L73-78) | DONE | W145 done (n1-multiline), W157 done (sq-newline), 778acf7 | none |
| item 11 OPEN: mtools self-install of pre-push, post-commit auto-push interaction unmeasured (L86-87) | OPEN, re-verified (.githooks/ tracks only commit-msg, post-commit, pre-commit) | UNCOVERED (scan "pre-push" hits ledger only) | T: "Install mikemol-githook-pre-push in mtools' own .githooks and measure its interaction with the post-commit auto-push" / evidence: ec71fe7, .githooks listing |
| item 11 post-commit and prepare-commit-msg not ported (L87-88, L109) | OPEN | UNCOVERED (scan "prepare-commit-msg" 0 hits) | two waypoints: "Port substrate's post-commit git hook to mikemol-hooks as a console script" and "Port substrate's prepare-commit-msg git hook to mikemol-hooks as a console script" / blocked_on none (handover letter inbox/archive/2026-09-23-substrate-githooks-handover.md); note el-openglo's post-commit writes the marker |
| item 11 el-openglo notice (L86) | DONE | queue L408: delivered 2026-09-25, el-openglo-11 acked | none (their pre-push.local is their work) |
| item 11 roll-out (a) substrate, (c) mat230 (L98-103) | DONE / OBSOLETE | substrate switched L79-85; mat230 retired | none |
| FENCE WAIT-queue design / summit ask ask-membudget-hold-records-no-waiter (L267-282) | DONE | W30 (design), W38 (bash measured), W47 (WAIT parse), W182 (acquire head-of-line), W48 (letter to substrate), W49 (tell summit and amr-skills, closes the ask), W527 (declines cross-client harness: bash retired) | none. queue "not started" is stale |
| fence `run` nests under a parent from ANOTHER ledger (L471-472) | DONE 7ebad9b ("Yes, same rule", L415) | W29 evidence cites 7ebad9b | none |
| fence hold: whether the context limit counts desktop compute apps, so TOTAL varies (L492-494) | OPEN, consumer-side | UNCOVERED (scan "kwin" 0 hits) | T: "Ask amr-skills whether the CUDA context limit also counts desktop compute apps (kwin, VS Code), so the contexts ledger TOTAL varies" / blocked_on amr-skills (agent) / evidence: queue L492-494; hold b8b3e41 |
| pending NOTICE to amr-skills about `init --reset N --unit contexts` (L257-259) | DONE | queue L464 "DONE b8b3e41; amr-skills told" plus their cutover (L464-472) | none (delivery of the unit notice itself is not separately evidenced; low risk) |
| PYCHECK G1/G2, suppression gate, noqa admission, format-bar opt-out (L394-409, L496-520) | DONE | f328d38, 859a10b; opt-out RESIDUE ruled no-build (L505-508); W149/W167 done | none (opt-out stays residue; consider recording it as a dropped-with-reason waypoint) |
| pycodemod console script (W35?) (L283-303) | DONE | W35 done: 4a4162e | none |
| pycodemod differential vs substrate 407/408 (L293-295) | DONE | W36 done (155 of 168 reported to substrate and summit), W105-W110, W126-W127, W194-W226, W432-W463 | none |
| differential: "memo classifies as cache" origin FAIL, decide defect or not (L293-295) | OPEN? | W106 records the FAIL (case 225 memo-as-cache); no waypoint records the decision | T: "Decide whether origin's failing case 'a live hand-rolled memo classifies as a cache' is an origin defect, and record it in W36-differential.md" / low confidence: may already be in .claude/design/W36-differential.md (not read) |
| DO-NOT-PORT letter to substrate (L625-644, L716) | DONE | W37 done, letter sent 2026-09-26 (msg acba52a3) | none |
| DEFERRED relname/sql relation reader, second consumer (L672-675, L693) | OPEN (deferred by operator rule) | UNCOVERED as a live waypoint (W37 evidence only records it in a letter) | T: "pycodemod: port the SQL-string relation reader (sql_rel_roles, sql_relnames, sql_kind, sql_rw, relname_sites) when a second repo asks" / blocked_on: second-consumer ask (agent: any peer; or kind human) / evidence: W37, queue L672-675 |
| DEFERRED --split file-splitting writer (L710-711) | OPEN (deferred) | UNCOVERED as live (scan "--split" refused by argparse; W37 evidence names it in the letter) | T: "pycodemod: port --split (file-splitting codemod writer behind --apply) when a second repo asks" / blocked_on second-consumer ask / evidence: W37, queue L710-711 |
| placement `--form` flag declined (L764-766) | OPEN (no caller has asked) | UNCOVERED (scan "--form" refused by argparse; no hit proven) | T: "pycodemod placement: add a --form flag overriding ENTRY_FORMS and FIRST_WRITE_FORMS, once the origin's spelling is verified" / blocked_on a caller ask / evidence: queue L764-766 (W61-style slice 6, commit under W34) |
| placement.writes_store / binds_snapshot_at_entry track no skips (L756-759) | OPEN, "unmeasured whether reachable" | UNCOVERED (only W24 evidence narrates it) | T: "pycodemod placement: writes_store and binds_snapshot_at_entry report no skips; measure whether a store-write-only unparseable file reaches the banner" / evidence: queue L756-759 |
| core.escapes should carry a Skip per file (W86) (L798-799) | DONE | W86, W97, W98 done; W55 minted it | none |
| W65 residue: the real missing-extra import-failure path in cli.py is unexercised (L859-860) | OPEN | UNCOVERED (W65 done says only "funcnames mode wired under ImportError guard") | T: "pycodemod cli: exercise the real ImportError path for the missing sqlalchemy extra, not a monkeypatched _run_funcnames" / evidence: commit 4160ead; queue L859-860 |
| W67/W68/W76 happy-path tests assert only that a row appears (L871-878, L926) | DONE | W87 done (row content pinned for deps, crossings, literals) | none |
| W75 residue: digit-named keyword unaddressable (L919-921) | OBSOLETE | stated "no loss" (not a legal identifier) | none |
| W68 residue: `python -m mikemol.pycodemod.cli` prints nothing, no `__main__` (L877) | OPEN, minor | W35 evidence records the finding; no waypoint to add a `__main__` | T: "pycodemod cli: add a __main__ so python -m mikemol.pycodemod.cli runs main, or refuse with a message naming the console script" / evidence: W35 evidence, queue L877 |
| W54 stale docstring (ordering.py "funcnames NOT PORTED") (L793, L857) | DONE | corrected in W65 (4160ead) | none |
| W72 side finding: vacuous parametrize read as a skip (L902-904) | DONE | W88, W89, W90, W91 done | none |
| census C1-C6 (L607-650) | DONE | W24 evidence: 04b4eca, 215917b, 30d6a25, 158660e, 1c4f500, de104f6 | none |
| `--calls sys.path.insert` dotted zero "lives in the CLI/driver layer, re-check when the driver is ported" (L575-579) | OPEN? | W24 evidence repeats it; no waypoint says it was re-checked after the driver landed (W59/W61 callgraph/guarded; W33 calls) | T: "pycodemod calls mode: re-measure the dotted-target zero (`--calls sys.path.insert`) at the CLI layer and arm it" / evidence: queue L349-362, L575-579 |
| 6.7 bibkeys: "Revisit if D3 is ruled otherwise" (L420-427) | OPEN, conditional | UNCOVERED (scan "bibkeys" ledger only) | T: "ledger bibkeys: switch the caller-supplied entries argv to mikemol.witness raw_bib if D3 (bib->findings, never reverse) is ruled otherwise" / blocked_on D3 ruling (kind human) / evidence: queue L420-427 |
| N-h set equality of the 564 eager edges not diffed; 131 components not re-measured (L444-451) | OBSOLETE | stated "not needed for the current batches" | none (could be residue) |
| N-d paperkit half (L459-463) | DONE | W531/W532/W542-W575 paperkit tools migration done | none |
| host-load gate block 2026-09-24 (L523-526) | OBSOLETE | passed | none |
| item 1 leftovers (L7-8) | DONE | fixed in 01771e0 (item text) | none |
| items 2, 4, 5 | DONE | f7a4b80; 415d532+d55dbd6; 39d81b1 (also W139, W151, W153) | none |
| W34 slices 2-7 NEXT lists and W52-W85 umbrella (L718-927) | DONE | W34 done, W52-W85, W87 done | none |
| settings.json allowlist / struct-tools routing tables for the new spelling (OPERATOR-OWNED, L297-299) | OPEN? operator-owned | UNCOVERED (not verified either way); W529 applied a different settings grant | T (human): "Operator: add the mikemol-pycodemod allowlist entry and the structural-query / struct-tools routing rows" / blocked_on operator (kind human); check first, it may already be applied |
| tell linux-sources the entry point; their acceptance pair stale_gate_build / simultaneously (L381-383) | UNKNOWN | scan "stale_gate_build" 0 hits; W35 enables linux-sources:W40 (done) | T: "Run linux-sources' acceptance pair (stale_gate_build plain, simultaneously f-string) against mikemol-pycodemod literals" / low confidence: may be done under W36/W107, which are done |

## Summary

Items assessed: 52. Counts: DONE or OBSOLETE with evidence 28, OPEN or UNKNOWN 24 (of those, UNCOVERED by any waypoint: 22; the other 2 only have a done waypoint that records the finding).
Open waypoints (8) cover none of these.

UNCOVERED list, in suggested mint order (each one landable unit):
1. dev deps include fence (item 3), no blocker
2. venv.bzl: delete unused `_relative_path`, no blocker
3. venv.bzl: `readlink -f` preamble, decide or record
4. venv.bzl: arm skips under bazel, measure
5. no_verify own shlex split onto cmdparse
6. mtools self-install of githook pre-push, measure post-commit auto-push
7. port post-commit hook
8. port prepare-commit-msg hook
9. transcriptstruct tool_reference decode (80)
10. substrate repoint Selftest.mk and tmi_* tools (blocked_on substrate)
11. contexts-ledger TOTAL vs desktop compute apps (blocked_on amr-skills)
12. pycodemod relname SQL reader (deferred, blocked_on second consumer)
13. pycodemod --split (deferred, blocked_on second consumer)
14. pycodemod placement --form flag (blocked_on a caller ask)
15. placement.writes_store / binds_snapshot_at_entry skips
16. W65 real ImportError path test
17. `python -m mikemol.pycodemod.cli` no `__main__`
18. `--calls` dotted-target zero re-measure at the CLI layer
19. bibkeys revisit-if-D3 (blocked_on D3 ruling, human)
20. memo-as-cache differential decision (low confidence)
21. operator: allowlist and routing rows for mikemol-pycodemod (human; verify first)
22. linux-sources acceptance pair (low confidence; may be done)

Stale statements in queue.md that contradict later text (do not mint waypoints for these): FENCE WAIT "not started" (done W182), "OPEN residue: run nests under another ledger" (done 7ebad9b), "Open decisions: TS1-c/TS1-d" (decided), el-openglo notice "OPEN" (delivered).

Caveats: scan-literal cannot search for strings starting with `--` (argparse refuses), so the `--form` and `--split` coverage rests on W-title reading plus W37 evidence. I did not read .claude/design/W36-differential.md or the inbox letters. Counts are approximate because a few queue lines bundle several items.
