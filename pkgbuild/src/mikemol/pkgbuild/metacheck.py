# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read the core metadata out of a wheel or an sdist and say what PyPI would refuse (mtools:W1187).

⚑ THIS IS NOT `twine check`. It reads the metadata a build wrote (`*.dist-info/METADATA` in a wheel,
`PKG-INFO` in an sdist) with the standard library and tests the properties an upload depends on.
`twine check` also RENDERS the long description with `readme_renderer`, which no stdlib check can
do; that is its own card (W1189), and a publish preflight that only ran this one says so.

What is tested, each by name:

- `Metadata-Version` is present and at least 2.1;
- `Name` is a valid project name;
- `Version` is a PUBLIC PEP 440 version with no local part (PyPI rejects `0.0.1+g<sha>`, the form
  the sha-pinned wheels carry today, and W803's `0.0.<n>` scheme replaces it);
- `Summary` is present;
- the long description is present and its `Description-Content-Type` is one PyPI renders
  (`text/markdown`, `text/x-rst`, `text/plain`);
- `Requires-Python` is declared;
- a license is declared (`License-Expression`, `License` or a `License-File`);
- the license TEXT is shipped (W1205): a `License-File` header, and that file in the artifact.

CONSUMED BY: `mikemol-wheel check` and the publish preflight (W1151).
"""

import re
import tarfile
import zipfile
from collections.abc import Mapping, Sequence
from email.parser import Parser
from pathlib import Path

NAME = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$")
PUBLIC_VERSION = re.compile(r"^\d+(\.\d+)*((a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?$")
CONTENT_TYPES = ("text/markdown", "text/x-rst", "text/plain")
MIN_METADATA = (2, 1)
LICENSE_FIELDS = ("License-Expression", "License", "License-File")


def _wheel_metadata(path: Path) -> str:
    """Read `*.dist-info/METADATA` from a wheel.

    Returns:
        the metadata text.

    Raises:
        ValueError: when the wheel does not hold exactly one.

    """
    with zipfile.ZipFile(path) as wheel:
        found = [n for n in wheel.namelist() if n.endswith(".dist-info/METADATA")]
        if len(found) != 1:
            msg = f"{path.name}: expected one .dist-info/METADATA, found {len(found)}"
            raise ValueError(msg)
        return wheel.read(found[0]).decode("utf-8")


def _sdist_metadata(path: Path) -> str:
    """Read the top-level `PKG-INFO` from an sdist.

    Returns:
        the metadata text.

    Raises:
        ValueError: when the sdist does not hold exactly one regular top-level PKG-INFO.

    """
    with tarfile.open(path) as sdist:
        members = [m for m in sdist.getnames() if m.count("/") == 1 and m.endswith("/PKG-INFO")]
        handle = sdist.extractfile(members[0]) if len(members) == 1 else None
        if handle is None:
            msg = f"{path.name}: expected one top-level regular PKG-INFO, found {len(members)}"
            raise ValueError(msg)
        return handle.read().decode("utf-8")


def read_metadata(path: Path) -> str:
    """Read the core metadata text of a built artifact.

    Returns:
        the `METADATA` of a wheel or the `PKG-INFO` of an sdist.

    Raises:
        ValueError: when the file is neither a wheel nor an sdist, or holds no such file.

    """
    if path.name.endswith(".whl"):
        return _wheel_metadata(path)
    if path.name.endswith(".tar.gz"):
        return _sdist_metadata(path)
    msg = f"{path.name}: not a wheel (.whl) or an sdist (.tar.gz)"
    raise ValueError(msg)


def parse(text: str) -> tuple[dict[str, list[str]], str]:
    """Split core metadata into its fields and its body.

    Returns:
        every header as a list of values (a header may repeat), and the message body.

    """
    message = Parser().parsestr(text)
    fields: dict[str, list[str]] = {}
    for key, value in message.items():
        fields.setdefault(key, []).append(str(value))
    return fields, str(message.get_payload())


def _first(fields: Mapping[str, Sequence[str]], key: str) -> str:
    values = fields.get(key, [])
    return values[0].strip() if values else ""


def _metadata_version(fields: Mapping[str, Sequence[str]]) -> list[str]:
    """Check `Metadata-Version`.

    Returns:
        the problem, or nothing.

    """
    raw = _first(fields, "Metadata-Version")
    parts = raw.split(".")
    if not raw or not all(p.isdecimal() for p in parts):
        return ["Metadata-Version is missing or not a version"]
    if tuple(int(p) for p in parts[:2]) < MIN_METADATA:
        return [f"Metadata-Version {raw} is older than 2.1"]
    return []


def _identity(fields: Mapping[str, Sequence[str]]) -> list[str]:
    """Check `Name` and `Version`.

    Returns:
        the problems.

    """
    problems: list[str] = []
    name = _first(fields, "Name")
    if not NAME.match(name):
        problems.append(f"Name {name!r} is missing or not a valid project name")
    version = _first(fields, "Version")
    if "+" in version:
        problems.append(f"Version {version!r} has a local part, which PyPI rejects")
    elif not PUBLIC_VERSION.match(version):
        problems.append(f"Version {version!r} is missing or not a public PEP 440 version")
    return problems


def _description(fields: Mapping[str, Sequence[str]], body: str) -> list[str]:
    """Check the summary and the long description with its content type.

    Returns:
        the problems.

    """
    problems = [] if _first(fields, "Summary") else ["Summary is missing"]
    text = body.strip() or _first(fields, "Description")
    kind = _first(fields, "Description-Content-Type").split(";")[0].strip().lower()
    if not text:
        problems.append("the long description is missing")
    elif kind not in CONTENT_TYPES:
        problems.append(f"Description-Content-Type {kind!r} is not one of {CONTENT_TYPES}")
    return problems


def check(fields: Mapping[str, Sequence[str]], body: str) -> list[str]:
    """Name every property of the metadata that PyPI would refuse or that is missing.

    Returns:
        the problems, empty when the metadata is clean.

    """
    problems = [*_metadata_version(fields), *_identity(fields), *_description(fields, body)]
    if not _first(fields, "Requires-Python"):
        problems.append("Requires-Python is missing")
    # ⚑ PyPI REJECTS A DIRECT-URL DEPENDENCY (W1216): `name @ https://...` is a PEP 508 form an
    # index cannot serve, and the upload fails after every other check passed.
    problems.extend(
        f"Requires-Dist {dep.strip()!r} is a direct URL, which PyPI rejects"
        for dep in fields.get("Requires-Dist", [])
        if " @ " in dep or dep.strip().startswith("@")
    )
    if not any(_first(fields, key) for key in LICENSE_FIELDS):
        problems.append("no license: none of License-Expression, License or License-File")
    return problems


def _member_names(path: Path) -> list[str]:
    """List the names of the files a wheel or an sdist carries.

    Returns:
        the member names.

    """
    if path.name.endswith(".whl"):
        with zipfile.ZipFile(path) as wheel:
            return wheel.namelist()
    with tarfile.open(path) as sdist:
        return sdist.getnames()


def license_files(path: Path, fields: Mapping[str, Sequence[str]]) -> list[str]:
    """Check that the artifact SHIPS its license text, not only a license name (W1205).

    ⚑ A `License-Expression` says which license; the text is what a redistributor must keep. PEP
    639 names each shipped file in a `License-File` header, and the file must be in the artifact
    (a wheel puts it under `.dist-info/licenses/`, an sdist at its top level).

    Returns:
        the problems: no `License-File` header, or a declared file the artifact does not carry.

    """
    declared = [value.strip() for value in fields.get("License-File", [])]
    if not declared:
        return ["no License-File: the license text is not shipped in the artifact"]
    names = _member_names(path)
    return [
        f"License-File {name!r} is declared but the artifact does not carry it"
        for name in declared
        if not any(member == name or member.endswith("/" + name) for member in names)
    ]


def verdict(path: Path) -> dict[str, object]:
    """Check one artifact.

    Returns:
        `artifact`, `name`, `version`, `ok` and `problems`; an artifact that cannot be read is
        `ok` false with the reason as its one problem.

    """
    try:
        fields, body = parse(read_metadata(path))
        shipped = license_files(path, fields)
    except Exception as exc:
        if not isinstance(exc, (OSError, ValueError, zipfile.BadZipFile, tarfile.TarError)):
            raise
        reason = [str(exc)]
        return {"artifact": path.name, "name": "", "version": "", "ok": False, "problems": reason}
    problems = [*check(fields, body), *shipped]
    return {
        "artifact": path.name,
        "name": _first(fields, "Name"),
        "version": _first(fields, "Version"),
        "ok": not problems,
        "problems": problems,
    }
