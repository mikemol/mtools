# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The vendored queue fixture is byte-identical to nemik's, pinned by git blob hash (W1620).

⚑ PIN THE CONTENT, NOT THE COMMIT (nemik-84, 2026-10-18): the fixture is nemik's, landed in its
7c4485d as `tests/fixtures/queue/alpha/paths-forward.json` and `.ledger`, and the independent
readers here (W1618) validate their own parsing against this copy so a format change fails each at
once. A gate must not read another repo's working tree, so the copy is vendored, and `git
hash-object` on the two files at that commit is the stable identifier: when nemik changes the
fixture it names the commit, and this pin is bumped with the copy, never one without the other.
"""

import hashlib
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "queue" / "alpha"
PINNED = {
    "paths-forward.json": "ae273078f16573da6edd0ab9abaab025d9481550",
    "paths-forward.ledger": "e10d8fad77bebeee17051fe484bcf36ed72eea47",
}


def blob_hash(data: bytes) -> str:
    """Compute the hash `git hash-object` gives a file with this content.

    Returns:
        the 40-hex blob id: sha1 of the header `blob <size>` and a NUL, then the bytes.

    """
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def test_the_blob_hash_of_a_known_content_is_gits() -> None:
    """The control: git's blob id of empty content and of a short line, computed here."""
    assert blob_hash(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    assert blob_hash(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_each_vendored_file_is_the_pinned_content() -> None:
    """A drift between nemik's fixture and this copy fails here, naming the file."""
    for name, expected in PINNED.items():
        assert blob_hash((FIXTURE / name).read_bytes()) == expected, name
