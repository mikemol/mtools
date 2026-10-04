# `--ledger -- …` is unreachable through argparse

From: luthen-observability, 2026-09-27

`mikemol-paths-forward --ledger SYMBOL OUTCOME MECHANISM NOTE` accepts `--` as the
no-waypoint symbol, but argparse consumes a bare `--` (and rejects `--ledger=--`), so the
call dies with "expected 4 arguments". Any other spelling is REFUSED ("neither --, W<n> nor
repo:W<n>"). As a result, an untied tick (for example an alert fix with no waypoint) cannot be
ledgered through the sole writer.

Reproduce: `$PF --ledger -- advanced unblock "x"` → exit 2.
Suggest: accept `-` or `none` as aliases for the no-waypoint symbol.

## Retraction of the motivating case (same day)

The operator pointed out that untied work gets a synthesized waypoint (`--add`) and is ledgered
against it. I did that (luthen W142), so my "cannot be ledgered" case was my own error, not a
tool gap. The only remaining defect is cosmetic: argparse makes the `--` symbol unreachable.
Low priority. If the no-waypoint symbol is meant to exist, fix it; otherwise drop it and REFUSE
with a hint to `--add`.
