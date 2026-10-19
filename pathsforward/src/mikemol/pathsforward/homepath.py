# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Say whether a text names a path under the home directories of this host (W1606).

⚑ A TRACKED QUEUE HOLDS NO HOME-DIRECTORY PATH (github-8f, 2026-10-18): amr-skills' gate refused a
queue commit on its no-home-paths test because an evidence string cited a transcript by absolute
path, and the next reader's checkout has another home. The prefix is read from the running host
(`Path.home().parent`), not written here, so no module names a user's home.
"""

from pathlib import Path


def names_home(text: str) -> bool:
    """Say whether `text` holds a path under this host's home directories.

    Returns:
        True when the text contains the home directories' parent followed by a separator.

    """
    parent = str(Path.home().parent).rstrip("/")
    return bool(parent) and f"{parent}/" in text
