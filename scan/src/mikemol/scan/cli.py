# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-scan DEVICE OUT.pdf`: scan both sides of a stack and make one searchable PDF (W1425).

⚑⚑ THE WHOLE JOB IS THE FOUR STEPS ALREADY BUILT, IN ORDER: the fronts pass (`adf.run_pass`), a wait
while the operator flips the stack and refeeds it, the backs pass, `pages.order` and `pdf.build`.
Nothing here is new logic; the scanner, the wait and the converters are all seams (`Run`, `Wait`),
so the sequence is tested with planted pages and a recording prompt, and no scanner starts.

⚑ THE WAIT IS A SEAM, NOT AN `input()` IN THE FLOW: a test that must not block passes a function
that records it was asked. The real one writes the instruction to stderr and reads one line.

⚑ A FAILURE NAMES ITS STEP AND LEAVES THE PAGES: the work directory keeps `front/` and `back/`, so a
failed PDF step does not cost the operator a rescan. Exit 0 on a PDF, 1 on any `ScanError`,
`PageCountError` or `PdfError` (their words on stderr), 2 on a usage error.

⚑ NOT YET RUN AGAINST A REAL SCANNER OR THE REAL PDF PROGRAMS: the first real scan is the check
(luthen-observability:W1210).
"""

import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.scan import adf, pages, pdf

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
FRONT = "front"
BACK = "back"
FLIP = "Flip the stack over and put it back in the feeder, then press Enter."
USAGE = "usage: mikemol-scan DEVICE OUT.pdf [--work DIR] [--resolution DPI] [--mode MODE]\n"
_POSITIONALS = 2
_KNOWN = {"--work", "--resolution", "--mode"}
Wait = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class Job:
    """What one invocation asks for: device, output PDF, page directory and scan settings."""

    device: str
    out: Path
    work: Path
    settings: adf.Settings


def _split(args: Sequence[str]) -> tuple[list[str], dict[str, str]] | None:
    """Split the arguments into positionals and the three `--name value` options.

    Returns:
        (positionals, options), or None when an option is unknown or has no value.

    """
    positional: list[str] = []
    options: dict[str, str] = {}
    index = 0
    while index < len(args):
        word = args[index]
        if not word.startswith("-"):
            positional.append(word)
            index += 1
        elif word in _KNOWN and index + 1 < len(args):
            options[word] = args[index + 1]
            index += 2
        else:
            return None
    return positional, options


def _work_dir(options: dict[str, str]) -> Path:
    """Pick the page directory: `--work`, else a fresh temporary one.

    Returns:
        the directory path.

    """
    if "--work" in options:
        return Path(options["--work"])
    return Path(tempfile.mkdtemp(prefix="scan-"))


def parse(args: Sequence[str]) -> Job | None:
    """Read the command line into a job.

    Returns:
        the job, or None for anything but two positionals, known options and a positive whole
        `--resolution`.

    """
    split = _split(args)
    if split is None or len(split[0]) != _POSITIONALS:
        return None
    (device, target), options = split
    defaults = adf.Settings()
    given = options.get("--resolution")
    if given is not None and not (given.isdigit() and int(given) > 0):
        return None
    settings = adf.Settings(
        resolution=int(given) if given is not None else defaults.resolution,
        mode=options.get("--mode", defaults.mode),
    )
    return Job(device, Path(target), _work_dir(options), settings)


def scan(job: Job, run: adf.Run, wait: Wait) -> Path:
    """Scan fronts, wait for the flip, scan backs and build the PDF.

    Returns:
        the PDF path.

    """
    fronts = adf.run_pass(job.device, job.work / FRONT, run, job.settings)
    wait(FLIP)
    backs = adf.run_pass(job.device, job.work / BACK, run, job.settings)
    return pdf.build(pages.order(fronts, backs), job.work, job.out, run)


def wait_on_operator(message: str) -> None:
    """Ask the operator to flip the stack and block for one line."""
    sys.stderr.write(f"{message}\n")
    sys.stdin.readline()


def main(argv: Sequence[str], run: adf.Run, wait: Wait) -> int:
    """Run the command.

    Returns:
        EXIT_OK on a PDF, EXIT_FAILED on a named step's failure, EXIT_USAGE on bad arguments.

    """
    job = parse(argv)
    if job is None:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    try:
        scan(job, run, wait)
    except (adf.ScanError, pages.PageCountError, pdf.PdfError) as failure:
        sys.stderr.write(f"mikemol-scan: {failure}\n  pages kept in {job.work}\n")
        return EXIT_FAILED
    return EXIT_OK


def entry() -> None:
    """Run the console script with the real scanner programs and the real operator prompt."""
    sys.exit(main(sys.argv[1:], adf.run_command, wait_on_operator))
