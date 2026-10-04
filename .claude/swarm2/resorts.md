# W230 — resorts.rego re-timed under --result-cache (drafter resorts)

## Measured

The cache dir started empty: `/var/tmp/claude-1000/-home-mikemol-github-mtools/0709aae6-1dba-4fe5-bfbe-24d21edd31e0/scratchpad/rc`.
Both runs used the same command. Standing rule 13 refused a bare `pytest`, so the commands use the `timeout <n> python -m pytest -o faulthandler_timeout=` form.

```
timeout 900 env PYTHONPATH=/home/mikemol/github/substrate/scratch \
  /home/mikemol/github/mtools/pycodemod/differential/.venv/bin/python -m pytest \
  /home/mikemol/github/mtools/pycodemod/differential/resorts.rego --impl reference \
  --result-cache <scratch>/rc -q -p no:cacheprovider -o faulthandler_timeout=600
```

Run 1, with an empty cache:
```
pytestspec: differential/resorts.rego impl=reference admitted=4 denied=0 refused=0 withheld-expected=0 unmeasured=3 do-not-port=0 port-fix=0 declared-skipped=0 cached=5
4 passed, 3 xfailed in 322.87s (0:05:22)
```
Run 2, with the same cache:
```
pytestspec: ... admitted=4 ... unmeasured=3 ... cached=7
4 passed, 3 xfailed in 2.77s
```
After both runs, the cache dir holds only **2** entries (`bd0c78dc….json`, `fd54699b….json`).

## Finding

- The card's expectation holds. Run 2 hit the cache for all 7 cases (cached=7) and took 2.77 s wall-clock, against 585 s for the earlier uncached run. Verdicts did not change: 4 passed, 3 xfailed.
- Not anticipated by the card: run 1 already shows cached=5 and took 323 s, not about 585 s. The 7 cases collapse to 2 distinct keys, so the cache dedupes within a single run. Only 2 origin calls really ran, which roughly halves the cold cost.
- The residue is the cold run: 2 distinct calls still take about 320 s wall-clock, about 160 s each. This is now the floor for any cache miss, for example after a fixture or origin change. W230 does not try to lower it.

## Proposed landing units (operator or queue owner)

1. **Close W230 with evidence** (queue write only):
   `W230 done: resorts.rego twice with one --result-cache dir: run1 322.87s cached=5 (7 cases -> 2 keys, intra-run dedupe), run2 2.77s cached=7; verdicts unchanged 4 passed 3 xfailed; prior uncached 585s.`
2. **Optional new waypoint** (caused_by W230), with touches `resorts, result-cache`: "Profile the 2 cold resorts origin calls (~160s each). Is the cost the fixture rehome or the origin itself?" Mint it only if cold runs matter, for example in CI without a persisted cache.
