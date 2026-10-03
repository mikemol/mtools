# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-audio`: transcribe, align and diarize recordings into markdown, one stage per process.

    mikemol-audio --ledger L --workdir D --out O --model M --device cuda
        --compute-type float16 --batch-size 4 --language en --token-file F LABEL=PATH ...

PARENT MODE (no `--stage`) runs cli.orchestrate: each stage is this same command with `--stage`,
under `mikemol-membudget hold 1` on the GPU ledger L. When all three succeed, it writes one
`<O>/<LABEL>.md` per source from the diarize handoff.

CHILD MODE (`--stage NAME`) reads the previous stage's handoff from `<D>/<prev>.json`, runs that
one stage on the real pipeline (whisperx_site), and writes `<D>/<NAME>.json`.

⚑ THE LABEL, NOT THE PATH, IS WHAT RECORDS AND ERRORS CARRY (design note D2): the audio is the
operator's own calls, so a file name can say more than it should. The label names the source.

⚑⚑ THE TOKEN IS A FILE PATH ON THE COMMAND LINE, NEVER A VALUE (design note D4). Only the
diarize child reads it, when that stage begins.

⚑ The subprocess runner and the pipeline factory are parameters of `main`, so every line here
runs under fakes in the witnesses. The real ones are the defaults.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.audiostruct.cli import Plan, orchestrate
from mikemol.audiostruct.render import markdown
from mikemol.audiostruct.stages import STAGES, Pipeline, records, run_stage
from mikemol.audiostruct.whisperx_site import Settings, pipeline

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

# The settings flags, as the parent passes them through to every child.
_SETTINGS = ("model", "device", "compute_type", "batch_size", "language", "token_file")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mikemol-audio", description=__doc__.split("\n")[0])
    parser.add_argument("--stage", choices=STAGES)
    parser.add_argument("--membudget", help="the mikemol-membudget binary; required by the parent")
    parser.add_argument("--ledger", required=True, help="the shared GPU context ledger")
    parser.add_argument("--workdir", required=True, help="where the stages hand off JSON")
    parser.add_argument("--out", required=True, help="where the markdown transcripts go")
    parser.add_argument("--model", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--compute-type", required=True)
    parser.add_argument("--batch-size", required=True, type=int)
    parser.add_argument("--language", required=True)
    parser.add_argument("--token-file", required=True)
    parser.add_argument("sources", nargs="+", metavar="LABEL=PATH")
    return parser


def parse_sources(specs: Sequence[str]) -> list[tuple[str, str]]:
    """Read `LABEL=PATH` pairs, each label once.

    Returns:
        the (label, path) pairs, in the order given.

    Raises:
        ValueError: a spec with no label or no path, or a label given twice.

    """
    pairs: list[tuple[str, str]] = []
    for spec in specs:
        label, sep, path = spec.partition("=")
        if not (sep and label and path):
            msg = f"source {spec!r}: expected LABEL=PATH"
            raise ValueError(msg)
        if label in {seen for seen, _ in pairs}:
            msg = f"source label {label!r} given twice"
            raise ValueError(msg)
        pairs.append((label, path))
    return pairs


def _settings(args: argparse.Namespace) -> Settings:
    values = cast("dict[str, object]", vars(args))
    return Settings(
        model=str(values["model"]),
        device=str(values["device"]),
        compute_type=str(values["compute_type"]),
        batch_size=cast("int", values["batch_size"]),
        language=str(values["language"]),
        token_file=str(values["token_file"]),
    )


def _passthrough(args: argparse.Namespace) -> list[str]:
    """Rebuild the flags every child needs, from the parent's parsed arguments.

    Returns:
        `--ledger L --out O --model M ...`, the child's copy of the parent's settings.

    """
    values = cast("dict[str, object]", vars(args))
    flags: list[str] = []
    for key in ("ledger", "out", *_SETTINGS):
        flags += [f"--{key.replace('_', '-')}", str(values[key])]
    return flags


def _handoff(workdir: str, stage: str) -> Path:
    return Path(workdir) / f"{stage}.json"


def _child(
    stage: str,
    args: argparse.Namespace,
    sources: Sequence[tuple[str, str]],
    make: Callable[[Settings], Pipeline],
) -> int:
    """Run one stage: read the previous handoff, run the stage, write this stage's handoff.

    Returns:
        0.

    """
    workdir = str(cast("dict[str, object]", vars(args))["workdir"])
    at = STAGES.index(stage)
    previous: list[object] = []
    if at > 0:
        text = _handoff(workdir, STAGES[at - 1]).read_text(encoding="utf-8")
        previous = cast("list[object]", json.loads(text))
    results = run_stage(stage, make(_settings(args)), sources, previous)
    _handoff(workdir, stage).write_text(json.dumps(results), encoding="utf-8")
    return 0


def _run(argv: list[str], env: Mapping[str, str]) -> int:
    """Run one stage's command with the ledger variables added to this process's environment.

    Returns:
        the command's exit code.

    """
    return subprocess.run(argv, env={**os.environ, **env}, check=False).returncode


def main(
    argv: Sequence[str] | None = None,
    run: Callable[[list[str], Mapping[str, str]], int] = _run,
    make: Callable[[Settings], Pipeline] = pipeline,
    program: str | None = None,
) -> int:
    """Run the parent or one child, as `--stage` says.

    ⚑ THE PARENT RE-INVOKES ITSELF BY ITS OWN ABSOLUTE PATH (W295), `program` or else this
    process's `sys.argv[0]`. Measured: a bare `mikemol-audio` is on no PATH here, so the children
    were reachable only with audiostruct/.venv/bin put on PATH by hand.

    Returns:
        0, the first failing stage's exit code, or 2 for bad sources.

    """
    args = _parser().parse_args(sys.argv[1:] if argv is None else list(argv))
    values = cast("dict[str, object]", vars(args))
    try:
        sources = parse_sources(cast("list[str]", values["sources"]))
    except ValueError as exc:
        sys.stderr.write(f"mikemol-audio: {exc}\n")
        return 2
    stage = values["stage"]
    if isinstance(stage, str):
        return _child(stage, args, sources, make)
    membudget = values["membudget"]
    if not (isinstance(membudget, str) and os.access(membudget, os.X_OK)):
        # ⚑ REFUSED BEFORE ANY STAGE (W292): the alternative, measured, is exit 127 mid-run.
        sys.stderr.write(f"mikemol-audio: --membudget {membudget!r} is not an executable\n")
        return 2
    workdir = str(values["workdir"])
    # ⚑ CREATED BEFORE ANY STAGE, AS --out IS (W522). Measured on the real GPU: a missing workdir
    # let the transcribe child load its model and transcribe, then die writing its handoff.
    Path(workdir).mkdir(parents=True, exist_ok=True)
    plan = Plan(
        membudget=membudget,
        ledger=str(values["ledger"]),
        program=[str(Path(program or sys.argv[0]).absolute()), *_passthrough(args)],
        workdir=workdir,
        sources=[f"{label}={path}" for label, path in sources],
    )
    code = orchestrate(plan, run)
    if code != 0:
        return code
    final = cast("list[object]", json.loads(_handoff(workdir, STAGES[-1]).read_text("utf-8")))
    out = Path(str(values["out"]))
    out.mkdir(parents=True, exist_ok=True)
    for label, found in records(sources, final):
        (out / f"{label}.md").write_text(markdown(label, found), encoding="utf-8")
    return 0
