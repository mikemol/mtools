# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Replay every case of one mode through this directory's reference adapter, printing each result.

`peek.py MODE` reads `MODE.cases.json` and calls the conftest's own `reference`, so it measures
exactly what `pytest MODE.rego --impl reference` will. Promoted to the session scratchpad (W413),
then to this tracked home (W471) once the differential stopped living under `.claude/`.

Run with the differential's reference venv and `PYTHONPATH=<substrate>/scratch`.
"""

import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

CASES = Path(__file__).resolve().parent

Reference = Callable[[object, object], object]

# ⚑ THE FAILURES A REPLAY REPORTS AS A ROW ARE NAMED, NOT CAUGHT BLIND. An origin call raising one
# of these is a finding about that case; anything else (an interrupt, an unknown class) stops the
# probe loudly rather than reading as one more row.
REPLAY_FAILURES: tuple[type[Exception], ...] = (
    ArithmeticError,
    AttributeError,
    ImportError,
    LookupError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


def load_reference() -> Reference:
    """Load the conftest beside this file and return its `reference` adapter.

    Returns:
        the adapter.

    Raises:
        ImportError: the conftest cannot be loaded.

    """
    spec = importlib.util.spec_from_file_location("w206_conftest", CASES / "conftest.py")
    if spec is None or spec.loader is None:
        msg = f"cannot load {CASES / 'conftest.py'}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("Reference", module.reference)


def main(mode: str) -> int:
    """Replay `mode`'s cases and print one result per case.

    Returns:
        0.

    """
    reference = load_reference()
    raw = cast("object", json.loads((CASES / f"{mode}.cases.json").read_text(encoding="utf-8")))
    cases = cast("list[dict[str, object]]", raw)
    sys.stdout.write(f"{len(cases)} cases\n")
    for case in cases:
        try:
            result = reference(case["fixture"], case.get("operands"))
        except REPLAY_FAILURES as exc:
            result = f"ERROR {type(exc).__name__}: {exc}"
        sys.stdout.write(f"--- {case['case']}\n{json.dumps(result, sort_keys=True)[:900]}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
