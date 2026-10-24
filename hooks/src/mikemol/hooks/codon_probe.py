# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Compile and run one file with the pinned Codon, fetched on first use (W1461, nemik:W631).

    mikemol-codon-probe FILE [--mtools DIR] [--cache DIR]

⚑ THE CENSUS IS STATIC, THE COMPILER IS THE PROBE. `mikemol-websubset` reads the tree and needs no
compiler; whether Codon accepts a construct is only known by running it (W1462's `X | None` was
found that way). A consumer without bazel had no pinned compiler to run, so nemik's gate refused
twice on one file it could not pre-check.

⚑ THE PIN IS READ, NEVER COPIED: the URL, the sha256 and the archive's top directory come from the
`http_archive(name = "codon")` block of the mtools checkout's `MODULE.bazel` (the operator's pin,
2026-10-15), so a repin there moves this tool and the two cannot disagree.

⚑ NOTHING IS UNPACKED UNTIL THE BYTES MATCH: the download is hashed whole against the pin's sha256
before it is opened, only https is spoken (redirects included), and the archive is extracted with
the standard library's `data` filter, which refuses absolute paths, parent steps and links that
leave the tree. The result is cached under the sha256, so a different pin is a different directory.
"""

import hashlib
import http.client
import io
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.parse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

EXIT_USAGE = 2
EXIT_REFUSED = 4
_OK = 200
_REDIRECTS = frozenset({301, 302, 303, 307, 308})
_HOPS = 5
_BLOCK = re.compile(r'http_archive\(\s*name = "codon",.*?\n\)', re.DOTALL)
_FIELDS = {
    "url": re.compile(r'\burl = "([^"]+)"'),
    "sha256": re.compile(r'\bsha256 = "([0-9a-f]{64})"'),
    "strip": re.compile(r'\bstrip_prefix = "([^"]+)"'),
}
Opener = Callable[[str], bytes]
Runner = Callable[[Sequence[str]], tuple[int, str]]


class PinError(Exception):
    """The pin cannot be read, or the bytes fetched for it are not the pinned bytes."""


@dataclass(frozen=True)
class Pin:
    """The pinned compiler: its URL, what its bytes hash to, and its archive's top directory."""

    url: str
    sha256: str
    strip: str


def read_pin(module_bazel: str) -> Pin:
    """Read the `codon` archive's pin out of a MODULE.bazel's text.

    Returns:
        the pin.

    Raises:
        PinError: when there is no codon block, a field is missing, or the URL is not https.

    """
    block = _BLOCK.search(module_bazel)
    if block is None:
        msg = 'no http_archive(name = "codon") block in MODULE.bazel'
        raise PinError(msg)
    found: dict[str, str] = {}
    for key, pattern in _FIELDS.items():
        match = pattern.search(block.group(0))
        if match is None:
            msg = f"the codon block has no {key}"
            raise PinError(msg)
        found[key] = match.group(1)
    if urllib.parse.urlsplit(found["url"]).scheme != "https":
        msg = f"the codon url is not https: {found['url']}"
        raise PinError(msg)
    return Pin(found["url"], found["sha256"], found["strip"])


def download(url: str) -> bytes:
    """Fetch a URL's bytes over https, following a few redirects, each also https.

    ⚑ NO TIMER (the avoid-wall-clock-timeouts rule): a transfer ends when the server ends it.

    Returns:
        the final response body.

    Raises:
        PinError: on a non-https hop, a status other than 200, or too many redirects.

    """
    for _hop in range(_HOPS):
        parts = urllib.parse.urlsplit(url)
        if parts.scheme != "https" or not parts.hostname:
            msg = f"refusing a non-https url: {url}"
            raise PinError(msg)
        connection = http.client.HTTPSConnection(parts.hostname, parts.port)
        target = parts.path + (f"?{parts.query}" if parts.query else "")
        connection.request("GET", target)
        response = connection.getresponse()
        if response.status in _REDIRECTS:
            url = urllib.parse.urljoin(url, response.getheader("Location") or "")
            connection.close()
            continue
        if response.status != _OK:
            msg = f"{url}: HTTP {response.status}"
            raise PinError(msg)
        body = response.read()
        connection.close()
        return body
    msg = f"more than {_HOPS} redirects from {url}"
    raise PinError(msg)


def fetch(pin: Pin, cache: Path, opener: Opener = download) -> Path:
    """Return the pinned compiler's binary, downloading and verifying it when not cached.

    Returns:
        the path of `bin/codon` under `<cache>/<sha256>/`.

    Raises:
        PinError: when the downloaded bytes do not hash to the pin; nothing is unpacked then.

    """
    home = cache / pin.sha256
    binary = home / "bin" / "codon"
    if binary.is_file():
        return binary
    data = opener(pin.url)
    got = hashlib.sha256(data).hexdigest()
    if got != pin.sha256:
        msg = f"the download hashes to {got}, not the pinned {pin.sha256}: nothing unpacked"
        raise PinError(msg)
    staging = cache / f"{pin.sha256}.partial"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            archive.extractall(staging, filter="data")
    except tarfile.TarError as refusal:
        shutil.rmtree(staging, ignore_errors=True)
        msg = f"the pinned archive was refused on extraction: {refusal}"
        raise PinError(msg) from refusal
    shutil.rmtree(home, ignore_errors=True)
    (staging / pin.strip).rename(home)
    shutil.rmtree(staging, ignore_errors=True)
    return binary


def run_codon(argv: Sequence[str]) -> tuple[int, str]:
    """Run the compiler and give back its status and everything it printed.

    ⚑ BOTH STREAMS: Codon reports a rejection on standard error, which is the answer a probe wants.

    Returns:
        (exit code, standard output then standard error).

    """
    # ⚑ NO CORE FILE, NO JOURNAL ENTRY (W1891, W1892): a rejected construct can abort the compiler,
    # and systemd-coredump logs the abort, which pages a host watcher. The limit is 1, NOT 0: with
    # core_pattern piped to the handler the kernel still invokes it at 0 (measured 2026-10-24).
    quiet = ["/bin/sh", "-c", 'ulimit -Sc 1 2>/dev/null; exec "$@"', "sh", *argv]
    done = subprocess.run(quiet, capture_output=True, text=True, check=False)
    return done.returncode, done.stdout + done.stderr


def _options(args: list[str]) -> tuple[list[str], Path, Path]:
    """Split the command line into files, the mtools checkout and the cache directory.

    Returns:
        (the positional arguments, mtools, cache).

    """
    mtools = Path.home() / "github" / "mtools"
    cache = Path.home() / ".cache" / "mikemol" / "codon"
    files: list[str] = []
    while args:
        name = args.pop(0)
        if name == "--mtools" and args:
            mtools = Path(args.pop(0))
        elif name == "--cache" and args:
            cache = Path(args.pop(0))
        else:
            files.append(name)
    return files, mtools, cache


def main(
    argv: Sequence[str] | None = None, opener: Opener = download, runner: Runner = run_codon
) -> int:
    """Run the pinned Codon on one file and print what it said.

    Returns:
        the compiler's exit code, EXIT_USAGE for bad arguments, EXIT_REFUSED when the pin cannot be
        read or the download is not the pinned bytes.

    """
    files, mtools, cache = _options(list(sys.argv[1:] if argv is None else argv))
    if len(files) != 1 or not Path(files[0]).is_file():
        sys.stderr.write("usage: mikemol-codon-probe FILE [--mtools DIR] [--cache DIR]\n")
        return EXIT_USAGE
    try:
        pin = read_pin((mtools / "MODULE.bazel").read_text(encoding="utf-8"))
        binary = fetch(pin, cache, opener)
    except (PinError, OSError) as refusal:
        sys.stderr.write(f"mikemol-codon-probe: {refusal}\n")
        return EXIT_REFUSED
    code, said = runner([str(binary), "run", files[0]])
    sys.stdout.write(said)
    return code


if __name__ == "__main__":
    sys.exit(main())
