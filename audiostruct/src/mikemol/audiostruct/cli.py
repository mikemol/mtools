# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-audio`: run the three stages, each in its own process, each holding one GPU context.

⚑⚑ ONE PROCESS PER STAGE, ONE CONTEXT PER PROCESS (design note D3/O1). The orchestrator re-invokes
this program as `--stage NAME` under `mikemol-membudget hold 1 LABEL -- ...`, so a stage holds the
GPU only while it runs, and a crashed stage releases its lease through the kernel, as every
membudget claim does. The stages hand off through JSON files in a work directory (run_stage, W281).

⚑⚑ THE SHARED GPU LEDGER COUNTS CUDA CONTEXTS, NOT MiB (luthen, answering mtools:W285). It is
amr-transcripts' `work/gpu-contexts.ledger`, TOTAL 3: the 3070 Ti's GSP refused new contexts after
about 3 foreign ones (luthen W77). Its other user, amr-transcripts/scripts/run-corpus.sh, holds 1
per process with MEMBUDGET_MAXLOAD=0, because host load must not hold back a GPU slot. So each stage
holds exactly 1, and nothing here sizes a lease in MiB. VRAM in MiB would be a second ledger, and
amr-skills' to create (W283 measures whether one is needed).

⚑ THE LEDGER PATH IS A REQUIRED INPUT, NEVER A DEFAULT: holding on the wrong ledger means never
contending with the GPU's other users. amr-transcripts owns the file and announces any move.

This module is the orchestrator side only. The child side, `--stage NAME`, which builds the real
whisperx pipeline, is W284.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.audiostruct.stages import STAGES

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

# What membudget reads (fence/admit.py): the ledger's path, and the load gate, turned off as the
# ledger's other user turns it off.
LEDGER_ENV = "MEMBUDGET_FILE"
MAXLOAD_ENV = "MEMBUDGET_MAXLOAD"

# Each stage process creates one CUDA context, so it holds one unit of the context ledger.
CONTEXTS_PER_STAGE = 1


@dataclass(frozen=True, slots=True)
class Plan:
    """One run: membudget and its ledger, the program to re-invoke, and its inputs.

    ⚑ `membudget` IS A PATH THE CALLER STATES (W292), like the ledger. Measured on the real GPU:
    a bare `mikemol-membudget` is on no PATH here (mtools' own is bazel-bin/fence/.venv/bin/), so
    the first stage died with exit 127 after the run had begun.
    """

    membudget: str
    ledger: str
    program: Sequence[str]
    workdir: str
    sources: Sequence[str]


def child_argv(stage: str, plan: Plan) -> list[str]:
    """Build the command that runs one stage holding one GPU context.

    Returns:
        `MEMBUDGET hold 1 audiostruct-STAGE -- PROGRAM --stage STAGE --workdir DIR SRC...`.

    """
    return [
        plan.membudget,
        "hold",
        str(CONTEXTS_PER_STAGE),
        f"audiostruct-{stage}",
        "--",
        *plan.program,
        "--stage",
        stage,
        "--workdir",
        plan.workdir,
        *plan.sources,
    ]


def orchestrate(plan: Plan, run: Callable[[list[str], Mapping[str, str]], int]) -> int:
    """Run each stage in order, each in its own process, each holding one context.

    ⚑ The first stage that exits nonzero stops the run: the next stage's input would be missing,
    and a refused lease (membudget's 3 or 4) is not something a later stage can make up for.

    Returns:
        0, or the first nonzero exit code.

    """
    env = {LEDGER_ENV: plan.ledger, MAXLOAD_ENV: "0"}
    for stage in STAGES:
        code = run(child_argv(stage, plan), env)
        if code != 0:
            return code
    return 0
