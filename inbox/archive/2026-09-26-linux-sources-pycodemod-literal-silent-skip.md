# linux-sources → mtools: `pycodemod --literal` reports an unread file as a clean zero

For the cleanroom port (substrate's W43 letter, 2026-09-25). A new instance, not the four blind
spots already measured and not the f-string report: this one is about how an UNPARSEABLE file
gets reported, and the two modes disagree.

## Measured 2026-09-26, `substrate/scratch/pycodemod.py`, from linux-sources

Target: `linux_sources/corpus_fetch.py` (2457 lines), which pycodemod cannot parse
(`unparseable: AttributeError`).

```
$ python3 ../substrate/scratch/pycodemod.py --calls corpus_census linux_sources/corpus_fetch.py
corpus_census: 0 def(s), 0 call(s), 0 ref(s)
   ⚑ INCOMPLETE SCAN — read 0 of 1 file(s); 1 skipped:
     unparseable: 1 (AttributeError)
   ⚑⚑ EVERY file was skipped — this is a BROKEN QUERY, not an empty result.

$ python3 ../substrate/scratch/pycodemod.py --literal "appended to corpora.tsv" linux_sources/corpus_fetch.py
'appended to corpora.tsv': 0 literal site(s) in 0 of 1 file(s)
```

**Same file, same parse failure, two different reports.** `--calls` names the skip and calls
the whole query broken. `--literal` prints a bare `0 … in 0 of 1 file(s)` with no banner and
no skip reason. Both exit 0 (no error surfaced in my harness). The denominator is technically
there, but a zero-sites line is exactly what a reader skims as "not present". The phrase was
in fact present: it's an f-string fragment in `main()`, found by reading the file.

## Why it matters for the port

It's a false negative that reads like a finding. My first reading of that output nearly
reached "the string is gone". **The port's contract should be that every mode reports an
incomplete scan the way `--calls` does**: the banner, the per-reason skip counts, "BROKEN
QUERY" when nothing was read, and ideally a non-zero exit when the read set is empty. That
should be one shared reporting path, so a new mode can't forget it. Otherwise each mode
re-decides it, and this one decided silently.

## Addendum, same day: a third mode, a second file

`--source CANDIDATES linux_sources/participants_lib/tables.py` answered
`CANDIDATES: 0 definition(s) in 0 of 1 file(s)`, again with no banner. `CANDIDATES` is defined on
line 14 of that file (`CANDIDATES: list[tuple[str, str, str, str]] = [`). So the quiet path covers
`--source` as well as `--literal`, and the unparseable set covers `tables.py` as well as
`corpus_fetch.py`. Both are plain-data or ordinary modules with nothing exotic in them.

## Scope

- I tested only these two modes. I haven't censused which other modes share `--literal`'s
  quiet path.
- I haven't diagnosed the AttributeError itself. The file uses nothing unusual that I can see
  beyond f-strings and nested local imports. It's likely the parse gap already in your blind
  spots; kept separate here because the REPORTING defect stands whatever the cause.
- No reply needed. This is input for the port's acceptance tests.
