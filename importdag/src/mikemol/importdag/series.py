# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read luthen's per-target gate CPU series into the cost table (W1997).

luthen's recording rules (`alerts/vmalert-records.rules.json`) publish, per `(repo, target)`:
`gate:luthen_gate_target_cpu_seconds:median7d`, `...:p90_7d` and
`gate:luthen_gate_target_cpu_samples:count7d`. This module turns the three instant-query responses
(Prometheus JSON, `data.result[].{metric, value}`) into the `Measured` table `cost.price` reads,
keyed by the test path the graph names.

⚑ A TARGET IS PAIRED ONLY WHEN ALL THREE SERIES NAME IT: a target with a median and no sample
count is not measured, it is left out and `price` lists it as unknown (nemik W1056).
⚑ A target that is not `//<package>:test_<name>` maps to no test path and is left out.
"""

from collections.abc import Mapping
from typing import cast

from mikemol.importdag.cost import Measured

_PAIR = 2


def _row(item: object, repo: str) -> tuple[str, float] | None:
    """Read one result row.

    Returns:
        (target, value) when the row is this repo's and well formed, else None.

    """
    if not isinstance(item, dict):
        return None
    row = cast("dict[str, object]", item)
    metric, value = row.get("metric"), row.get("value")
    if not isinstance(metric, dict) or not isinstance(value, list):
        return None
    labels, pair = cast("dict[str, object]", metric), cast("list[object]", value)
    target = labels.get("target")
    if labels.get("repo") != repo or not isinstance(target, str) or len(pair) != _PAIR:
        return None
    try:
        return target, float(str(pair[1]))
    except ValueError:
        return None


def _values(response: Mapping[str, object], repo: str) -> dict[str, float]:
    """Pick one series' value per target for this repo.

    Returns:
        target label to value; a malformed row is skipped.

    """
    data = response.get("data")
    rows = cast("dict[str, object]", data).get("result") if isinstance(data, dict) else None
    items = cast("list[object]", rows) if isinstance(rows, list) else []
    got = (_row(item, repo) for item in items)
    return dict(pair for pair in got if pair is not None)


def test_path(target: str) -> str | None:
    """Map a bazel test label to the dist-relative test path.

    Returns:
        `tests/test_<name>.py` for `//<package>:test_<name>`, else None.

    """
    name = target.rpartition(":")[2]
    if not target.startswith("//") or not name.startswith("test_"):
        return None
    return f"tests/{name}.py"


def table(
    repo: str,
    median: Mapping[str, object],
    p90: Mapping[str, object],
    samples: Mapping[str, object],
) -> dict[str, Measured]:
    """Join the three series into the cost table.

    Returns:
        test path to `Measured`, for targets all three series name and that map to a test path.

    """
    med, top, count = _values(median, repo), _values(p90, repo), _values(samples, repo)
    out: dict[str, Measured] = {}
    for target in sorted(med.keys() & top.keys() & count.keys()):
        path = test_path(target)
        if path is not None:
            out[path] = Measured(med[target], top[target], int(count[target]))
    return out
