# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One ADF pass through `scanimage` against a named device, behind a seam (W1423).

⚑⚑ THE SCANNER IS REACHED ONLY THROUGH `Run`, A PLAIN FUNCTION. The command is built here
(`command`) and executed by the one function that touches a process (`run_command`); every test
replaces `Run`, so no scanner and no subprocess is needed to prove what is asked of it. The device
is a name SANE's eSCL backend discovered (`scanimage -L`), passed through as the caller gave it.

⚑ A PASS NEVER MIXES WITH A PREVIOUS ONE: the output directory must hold no page files already, or
the fronts and the backs would land in one pile and `pages.order` would be handed a wrong count
that looks like a lost sheet. The pass returns its files in the order the scanner fed them.

⚑ NOT YET VERIFIED AGAINST A REAL SCANNER: that `scanimage` ends an ADF batch with exit 7 when the
feeder runs out of documents is from its manual, not from a run here. `ENDED_EMPTY` names it, and a
pass is accepted when it exits 0 or 7 AND wrote at least one page; anything else raises with the
tool's own words. The first real scan is the check (luthen-observability:W1210).
"""

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

ENDED_EMPTY = 7
# ⚑ TIFF, NOT PNM: the PDF step (W1424) joins pages with img2pdf, which reads TIFF and not PNM, and
# ocrmypdf itself takes a single image or PDF. A TIFF page costs nothing at the scanner.
PATTERN = "page-%03d.tif"
_GLOB = "page-*.tif"
Run = Callable[[Sequence[str]], tuple[int, str]]


class ScanError(RuntimeError):
    """A pass could not run, mixed with an earlier pass, or produced nothing."""


@dataclass(frozen=True, slots=True)
class Settings:
    """How a pass is asked for: the paper source, the resolution and the colour mode."""

    source: str = "ADF"
    resolution: int = 300
    mode: str = "Gray"


def command(device: str, outdir: Path, settings: Settings) -> list[str]:
    """Build the `scanimage` argv for one batch pass.

    Returns:
        the argv; the device and the directory are single words, never joined into a string.

    """
    return [
        "scanimage",
        "-d",
        device,
        "--source",
        settings.source,
        "--resolution",
        str(settings.resolution),
        "--mode",
        settings.mode,
        "--format=tiff",
        f"--batch={outdir / PATTERN}",
        "--batch-start=1",
    ]


def pages(outdir: Path) -> list[Path]:
    """List the page files of a pass in feed order.

    Returns:
        the files named `page-NNN.tif`, sorted (zero-padded, so name order is feed order).

    """
    return sorted(outdir.glob(_GLOB))


def run_pass(device: str, outdir: Path, run: Run, settings: Settings | None = None) -> list[Path]:
    """Run one ADF pass and return the page files it wrote.

    Returns:
        the page files, in feed order.

    Raises:
        ScanError: when the directory already holds pages, `scanimage` fails, or no page appears.

    """
    outdir.mkdir(parents=True, exist_ok=True)
    if pages(outdir):
        msg = f"{outdir} already holds page files; a pass needs an empty directory of its own"
        raise ScanError(msg)
    code, said = run(command(device, outdir, settings or Settings()))
    written = pages(outdir)
    if code not in {0, ENDED_EMPTY} or not written:
        msg = f"scanimage exit {code}, {len(written)} page(s) written: {said.strip()[:300]}"
        raise ScanError(msg)
    return written


def run_command(argv: Sequence[str]) -> tuple[int, str]:
    """Run a command and capture its exit code and stderr (where scanimage reports).

    Returns:
        (exit code, stderr text).

    """
    proc = subprocess.run(list(argv), capture_output=True, text=True, check=False)
    code: int = proc.returncode
    err: str = proc.stderr
    return code, err
