# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Draw a blind labelled sample of assistant sentences for the commitment classifiers (W1966).

Two readers of the same transcripts, this tool's regex and amr-skills' AMR classifier, are each
checked only if neither one's reading is in the other's labels (github-8f's G4 guard). So:

⚑ THE SAMPLE IS RANDOM SENTENCES PLUS THE REGEX HITS. Sampling only what the regex finds leaves
recall invisible: a commitment the regex misses could never appear. `draw` takes `n` sentences
uniformly from every assistant text sentence of the transcript and adds every sentence the regex
families match, each once. The draw is by hash rank (the `n` sentences whose `sha256(seed:index)`
is smallest), so it is reproducible from the seed alone and needs no random generator.

⚑ THE TWO FILES ARE BLIND TO EACH OTHER. `blind` is what goes to the other labeller: an id, the
place and the text, with NO family and no indication of where the sentence came from. `key` is
this side's own file: the id, whether the sentence was drawn at random or by the regex, and the
family the regex gave it. Agreement is computed afterwards from the two label sets, and the
disagreements are kept as fixtures, neither side being truth.

CONSUMED BY: the `--sample` mode of `mikemol-transcriptstruct` (W1966).
"""

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass

from mikemol.transcriptstruct import commitments
from mikemol.transcriptstruct.blocks import blocks
from mikemol.transcriptstruct.records import AssistantRecord, Record

RANDOM = "random"
REGEX = "regex"


@dataclass(frozen=True, slots=True)
class Sentence:
    """One assistant sentence: where it is, what it says and the regex family, if any."""

    line: int
    uuid: str
    text: str
    family: str | None


def sentences(records: Iterable[Record]) -> list[Sentence]:
    """List every sentence of every assistant text block, in transcript order.

    ⚑ THE SAME EXCLUSIONS AS THE EXTRACTOR, so the two see one population: sidechain records,
    non-text blocks and a sentence quoting a cross-session message are left out.

    Returns:
        one entry per sentence, its regex family or None.

    """
    found: list[Sentence] = []
    for record in records:
        if not isinstance(record, AssistantRecord) or record.is_sidechain:
            continue
        uuid = str(record.raw.get("uuid", ""))
        for block in blocks(record):
            if block.kind != "text":
                continue
            for raw in commitments.sentence_spans(block.text):
                said = raw.strip()
                if said and commitments.QUOTING not in said:
                    found.append(Sentence(record.line, uuid, said, commitments.family_of(said)))
    return found


def _rank(seed: int, index: int) -> str:
    # A sentence's place in the seeded order: the hash of the seed and its index.
    return hashlib.sha256(f"{seed}:{index}".encode()).hexdigest()


def draw(pool: list[Sentence], n: int, seed: int) -> list[tuple[Sentence, str]]:
    """Choose the sample: `n` sentences uniformly at random, plus every regex hit once.

    Returns:
        the chosen sentences in transcript order, each with its source, `RANDOM` or `REGEX`; a
        regex hit that the random draw also took is listed once, as `REGEX`.

    """
    hits = {index for index, item in enumerate(pool) if item.family is not None}
    ranked = sorted((_rank(seed, index), index) for index in range(len(pool)))
    picked = {index for _rank_value, index in ranked[: max(n, 0)]}
    return [(pool[i], REGEX if i in hits else RANDOM) for i in sorted(picked | hits)]


def blind(chosen: list[tuple[Sentence, str]]) -> list[dict[str, object]]:
    """Spell the rows that go to the other labeller, with nothing of this side's reading.

    Returns:
        one object per sentence: id, line, uuid and text.

    """
    return [
        {"id": index, "line": item.line, "uuid": item.uuid, "text": item.text}
        for index, (item, _source) in enumerate(chosen)
    ]


def key(chosen: list[tuple[Sentence, str]]) -> list[dict[str, object]]:
    """Spell this side's own file: where each sentence came from and the regex family.

    Returns:
        one object per sentence: id, source and family (empty for none).

    """
    return [
        {"id": index, "source": source, "family": item.family or ""}
        for index, (item, source) in enumerate(chosen)
    ]
