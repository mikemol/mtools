# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The alert expressions for a train stuck red or not landing, and their twins in code (W1748).

A 6 h red streak (2026-10-19, 29 identical failures) went unremarked because nothing watched the
series W1715 now records. The rule file is luthen's to host; this states the two expressions the
rule holds, in the metrics the store carries today, and the same predicates in code so the tests
can run them against recorded samples and a change to one cannot drift from the other.

    RED STREAK  N red rounds and no green one inside a window W:
        sum_over_time(mikemol.train.round{repo="R",verdict="red"}[W]) >= N
        unless sum_over_time(mikemol.train.round{repo="R",verdict="green"}[W]) > 0
    NO LAND     the newest landing is older than L seconds:
        time() - tlast_over_time(mikemol.commit.verdict{repo="R",verdict="COMMITTED"}[D]) > L

⚑ BOTH SERIES READ LIVE BEFORE THIS WAS WRITTEN (2026-10-21, `query-metrics`): `mikemol.train.round`
carries `repo` and `verdict` (green, red, and the others `trainround` names) with a sample per
round, and `mikemol.commit.verdict` carries `repo` and `verdict=COMMITTED` with a sample per
landing. The store's `tlast_over_time` answered with a sample's epoch seconds when W1602 checked it.

⚑ A WINDOW STANDS IN FOR 'CONSECUTIVE'. Prometheus cannot count the last N samples, so a red streak
is N reds with no green inside W; a streak that straddles a window's edge reads as a shorter one.
Choose W as about N rounds of the train's usual length.

⚑ NO SERIES IS NOT A LANDING GAP. `tlast_over_time` over a window with no sample returns nothing,
so the NO LAND expression is silent for a repo that has not landed in D at all; that case is the
freshness alert's (W1781), and the twin says the same by returning False for no landing at all.

⚑ THE LIMIT L IS A PARAMETER, NOT A NUMBER HERE. W1748 asks for a multiple of the gate median, and
no series of whole-gate duration exists yet (only per-target ones); the caller passes the seconds it
derived, and the derivation belongs beside the number in the rule file.
"""

from collections.abc import Sequence

RED = "red"
GREEN = "green"
ROUND = "mikemol.train.round"
LANDED = "mikemol.commit.verdict"


def red_streak_expr(repo: str, rounds: int, window: str) -> str:
    """Build the expression that fires when `rounds` red rounds and no green one fall in `window`.

    Returns:
        the PromQL text, `window` as a duration such as `6h`.

    """
    red = f'sum_over_time({ROUND}{{repo="{repo}",verdict="{RED}"}}[{window}])'
    green = f'sum_over_time({ROUND}{{repo="{repo}",verdict="{GREEN}"}}[{window}])'
    return f"{red} >= {rounds} unless {green} > 0"


def no_land_expr(repo: str, seconds: int, retention: str) -> str:
    """Build the expression that fires when the newest landing is older than `seconds`.

    Returns:
        the PromQL text; `retention` is how far back the newest landing is looked for.

    """
    newest = f'tlast_over_time({LANDED}{{repo="{repo}",verdict="COMMITTED"}}[{retention}])'
    return f"time() - {newest} > {seconds}"


GATE_RUN = "mikemol.gate.run.seconds"


def stale_expr(repo: str, seconds: int, retention: str) -> str:
    """Build the freshness expression: the gate series has no sample newer than `seconds` (W1781).

    ⚑ BOTH SILENCES FIRE. A series whose newest sample is old is one arm; a series with no sample at
    all in `retention` is the other, which `tlast_over_time` cannot see (it returns nothing), so
    `absent_over_time` is OR-ed in. A dead emitter and a day with no gate are different readings
    only by `mikemol.gate.run.emitted`, which this does not consult.

    Returns:
        the PromQL text over `mikemol.gate.run.seconds{repo}`.

    """
    series = f'{GATE_RUN}{{repo="{repo}"}}[{retention}]'
    return f"time() - tlast_over_time({series}) > {seconds} or absent_over_time({series})"


def stale_firing(samples: Sequence[int], now: int, seconds: int) -> bool:
    """Run the freshness predicate over recorded sample times (epoch seconds).

    Returns:
        True when there is no sample at all or the newest is more than `seconds` before `now`.

    """
    return not samples or now - max(samples) > seconds


def red_streak_firing(
    samples: Sequence[tuple[int, str]], rounds: int, window: tuple[int, int]
) -> bool:
    """Run the red-streak predicate over recorded (epoch seconds, verdict) round samples.

    `window` is (start, end) in epoch seconds, both ends inside.

    Returns:
        True when the window holds at least `rounds` red samples and no green one.

    """
    inside = [verdict for time, verdict in samples if window[0] <= time <= window[1]]
    return inside.count(RED) >= rounds and GREEN not in inside


def no_land_firing(landings: Sequence[int], now: int, seconds: int) -> bool:
    """Run the landing-gap predicate over recorded landing times (epoch seconds).

    Returns:
        True when the newest landing is more than `seconds` before `now`; False with no landing.

    """
    return bool(landings) and now - max(landings) > seconds
