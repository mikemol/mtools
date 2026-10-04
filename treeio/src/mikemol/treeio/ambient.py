# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A per-invocation context variable that is WRITE-ONCE, and the scoped override that bypasses it.

Ported from paperkit's `tools/edit_snapshot.py`. Intent (apply or dry-run), snapshot state and
tenant are the same shape: a fact about THE INVOCATION that was being passed as a PARAMETER, so
anyone could address it positionally and two different propositions ended up spelled identically
("what the operator asked for" and "what this branch actually does"). A parameter is an embedded
precondition. Building a second copy of this mechanism per variable would be the derived-view
duplication this code base keeps paying for: the vocabulary differs, the machinery does not.

THE DECLARATION SITE CARRIES THE SCOPE. There is deliberately NO source field beside the value: a
hand-maintained provenance field is a derived view maintained by hand next to the real one.
`contextvars` already records where a value was set, per invocation, so the value and its origin
are written in ONE act by ONE writer, which is what keeps them from drifting.

WHAT THIS IS, PLAINLY: ENFORCEMENT AT THE WRITE, WITH A NAMED RESIDUAL. IT IS NOT A CAPABILITY.
`Ambient.set` is write-once: the first binding wins and a second RAISES, naming the site that
already bound it, and that holds without any cooperation from consumers: a consumer that never
compares anything is not a hole, because only one value was ever bound. The residual, stated
rather than glossed: a caller can still reach the private context variable, or run its work in a
context of its own making. Python has no unforgeable capability. What matters is that both are
DELIBERATE acts, and neither is what a plausible-local-fix generator produces while "fixing" a
refusal. The accidental second binding, which is the failure actually defended against, fails
loudly at the point of the write. And every refusal names its successor, because a refusal with no
named successor is an invitation to invent one locally.

THREADS AND SUBPROCESSES. `contextvars` propagates into asyncio tasks and does NOT cross a thread
boundary: a thread starts from an empty context, so an ambient bound in the parent is invisible
there. A subprocess carries no context by construction; the child re-reads its argv and binds its
own, which is correct. If a threaded writer ever lands here it must pass the context explicitly,
because the failure would be a silently unbound ambient, which reads exactly like a first write.
"""

from __future__ import annotations

import contextvars
import sys
from typing import TYPE_CHECKING, NoReturn

from mikemol.treeio.errors import AmbientVocabError, MutationContractError

if TYPE_CHECKING:
    from collections.abc import Callable

type Tokens = tuple[contextvars.Token[str | None], contextvars.Token[str | None]]

SANCTIONED_OVERRIDES = {
    ("intent", "prune_leaf_opens (dry-run writes-then-restores)"): (
        "This tool writes the file EVEN IN DRY RUN (writes, re-checks, restores at the "
        "end), so on a stated --dry-run the filesystem truth is 'apply' while the "
        "operator's request is 'dry-run'. A crash between the write and the restore "
        "leaves the damage — which is precisely the snapshot's case."
    ),
}
"""The roster of knowingly bypassed bindings, keyed by variable name and label.

THE OVERRIDE IS DELIBERATELY EXPENSIVE TO SPELL, AND THE ROSTER IS WHY. An override as cheap as
passing a keyword is not a fix, it is the same defect with more steps: the moment a refusal is
inconvenient the next writer reaches for the escape instead of the contract. So a divergence must
ALSO be pre-registered here, with the reason it exists. It is designed for one case, not for a
population: that tool writes the file even in dry run, so on a stated dry-run the operator's
request and the filesystem truth genuinely disagree, and the disagreement is CORRECT. A roster with
one member is the honest shape; if a second lands, that is a REVIEW, which is exactly the friction
this is for. It is not a second allow-list beside a gate: it is the mechanism's own declaration of
where it is knowingly bypassed."""


def _stderr_line(message: str) -> None:
    """Write one announcement line to stderr, the default place an override says it ran."""
    sys.stderr.write(message + "\n")


class AmbientConflictError(MutationContractError):
    """A SECOND write to a write-once ambient. Names the site that already bound it.

    It joins the `MutationContractError` family, which moves it off Exception, and that is a
    BEHAVIOUR CHANGE stated rather than slipped in: as an Exception it was catchable by the
    best-effort snapshot handlers, and reaching them meant a refusal printed as "snapshot
    unavailable" while the tool wrote anyway.

    THIS FIRES AT THE WRITE, NOT AT A READ, AND THAT IS THE WHOLE DESIGN. A cut that compared a
    stated value against the ambient one at every consumer would be N checks, each of which can be
    forgotten, and forgetting one is precisely the plausible-local-fix failure this is scaled
    against. A write-once variable means THERE IS NOTHING TO DISAGREE WITH: the second write fails
    where the write happens. It is also what the tenant case needed: two functions independently
    resolving the same fact, one report reading two stores, neither routed through a comparison.
    Write-once makes the FIRST resolution the answer and the second an ERROR.
    """

    def __init__(self, amb: Ambient, label: str, stated: str, ambient: str, origin: str) -> None:
        """Record the conflict and render its message.

        Args:
            amb: The ambient that was written twice.
            label: The site attempting the second write.
            stated: The value that second write offered.
            ambient: The value already bound.
            origin: The site that bound it.

        """
        self.amb = amb
        self.label = label
        self.stated = stated
        self.ambient = ambient
        self.origin = origin
        super().__init__(str(self))

    def __str__(self) -> str:
        """Render the refusal: what is bound, by whom, what was attempted, and the successors.

        A second write of the SAME value is still a defect, and saying so is the point: it means
        two sites each believe they are the one that decides. They agree today and nothing makes
        them agree tomorrow.

        Returns:
            The multi-line refusal text.

        """
        amb = self.amb
        name = amb.kw.upper()
        head = (
            f"⚑ {self.label}: {amb.kw} is ALREADY BOUND for this invocation "
            f"({self.ambient!r}) and is WRITE-ONCE."
        )
        body = (
            f"  bound:    {self.ambient!r}  by {self.origin}\n"
            f"  attempted:{self.stated!r}  at {self.label}\n"
        )
        if self.stated == self.ambient:
            body += (
                "  ⚑ The values MATCH, which is not a reprieve: two sites each "
                "believe they are the\n    one that decides. They agree today and "
                "nothing makes them agree tomorrow — that\n    is the shape that "
                "put two stores in one report.\n"
            )
        else:
            body += f"  {amb.two_readings}\n"
        return (
            head
            + "\n"
            + body
            + "  ⚑ Successors, in the order you should try them:\n"
            + f"    1. READ IT, do not re-bind it: `mikemol.treeio.context.{name}.get()` "
            + "returns the value\n"
            + "       this invocation already established. A callee almost never needs "
            + "to write.\n"
            + "    2. BIND IT ONCE, AT ENTRY — where the operator's request is read "
            + "(`require_at_entry`),\n"
            + "       so every frame below inherits it and none has to assert anything.\n"
            + "    3. If this genuinely is a NEW invocation (a fixture, a nested run over "
            + "a different\n"
            + "       target), give it a NEW CONTEXT rather than overwriting this one:\n"
            + "           contextvars.copy_context().run(fn, ...)\n"
            + f"       or, for the one sanctioned in-tree divergence, `{name}.override(...)`,\n"
            + "       which runs the body in a copied context and must be registered in\n"
            + "       `mikemol.treeio.ambient.SANCTIONED_OVERRIDES`."
        )


AmbientConflict = AmbientConflictError
"""Paperkit's spelling of the conflict error, kept so a repointed import line is the only change."""


class Ambient:
    """A per-invocation context variable with REFUSE-ON-DISAGREEMENT resolution.

    `vocab` IS CLOSED. An unrecognised value REFUSES rather than passing: the escape must be at
    least as strict as the thing it bypasses, or a typo satisfies the contract silently.
    """

    def __init__(self, kw: str, vocab: tuple[str, ...], two_readings: str) -> None:
        """Declare the variable: its name, its closed vocabulary, and what its two readings are.

        Args:
            kw: The variable's name, used in every refusal.
            vocab: The only values `set` accepts.
            two_readings: The sentence a conflict message uses to say why two values differ.

        """
        self.kw = kw
        self.vocab = tuple(vocab)
        self.two_readings = two_readings
        self._var = contextvars.ContextVar[str | None](f"substrate_{kw}", default=None)
        self._origin = contextvars.ContextVar[str | None](f"substrate_{kw}_origin", default=None)

    def get(self) -> str | None:
        """Read the value this invocation bound.

        Returns:
            The bound value, or None when nothing has bound one.

        """
        return self._var.get()

    def origin(self) -> str | None:
        """Read where the bound value came from.

        Returns:
            The binder's label, or None when nothing has bound one.

        """
        return self._origin.get()

    def set(self, value: str, origin: str) -> Tokens:
        """Bind the value and its origin in ONE act. WRITE-ONCE: a second write RAISES.

        THE SINGLE ENFORCEMENT POINT. Every route by which a wrong value could enter this
        invocation passes through here, so the check lives here and NOWHERE ELSE. There is
        deliberately no public reset: a reset returns the variable to its prior value, which is
        legitimate for a scoped override and is ALSO a hole if anything may call it, since
        write-once plus an unrestricted reset is write-many with extra steps. A new binding needs
        a NEW CONTEXT, not an undo.

        These refusals RAISE; they used to exit. The message is unchanged, and the reason is not
        about this frame: no script should assume it is the sole owner of the current pid, and
        this is reached as a LIBRARY, where an exit unwinds the CALLER'S interpreter.

        Returns:
            The tokens of the two writes.

        Raises:
            AmbientVocabError: when the value is outside the vocabulary.
            AmbientConflictError: when the variable is already bound.

        """
        if value not in self.vocab:
            quoted = " / ".join(map(repr, self.vocab))
            msg = (
                f"⚑ {origin}: {self.kw}={value!r} is not one of {quoted}.\n"
                "  An unrecognised value REFUSES rather than passing — the escape "
                "must be at least as\n  strict as the contract it bypasses, or a typo "
                "satisfies it silently."
            )
            raise AmbientVocabError(msg)
        bound = self._var.get()
        if bound is not None:
            where = self._origin.get() or "<unknown>"
            raise AmbientConflictError(self, origin, value, bound, where)
        return self._var.set(value), self._origin.set(origin)

    def resolve(self, label: str, stated: str | None = None) -> str | None:
        """Give the invocation's value: bind a stated one if unbound, otherwise READ.

        A STATED VALUE THAT MATCHES THE ALREADY-BOUND ONE IS A NO-OP, NOT A REBIND. That is what
        lets a call site that hardcodes its intent keep working while the guarantee still holds:
        under a matching invocation they agree and agreement passes silently, under a disagreeing
        one the same site raises, which is the whole point. The disagreeing case routes through
        `set`, so the refusal text, the successors and the write-once semantics are stated once.

        Returns:
            The value bound for this invocation, or None when nothing is bound and none stated.

        """
        bound = self.get()
        if stated is None:
            return bound
        if bound is None:
            self.set(stated, f"stated at {label}")
            return stated
        if bound != stated:
            self.set(stated, f"stated at {label}")
        return bound

    def run_bound[T](self, value: str, origin: str, call: Callable[[], T]) -> T:
        """Run `call` in a FRESH CONTEXT where this variable holds `value`.

        A copied context gives a genuinely fresh binding scope over a COPY of the current values:
        writes do not escape outward, and existing values DO carry inward. So the variable is
        reset to unbound inside the copy and set once, which satisfies write-once honestly rather
        than bypassing it, and the outer context is UNTOUCHED.

        Returns:
            Whatever `call` returns.

        """

        def inner() -> T:
            self._var.set(value)
            self._origin.set(origin)
            return call()

        return contextvars.copy_context().run(inner)

    def override(
        self,
        value: str,
        reason: str,
        label: str = "override",
        announce_to: Callable[[str], None] | None = None,
    ) -> Override:
        """Make a SCOPED, REASONED divergence from the ambient value: the deliberate override.

        It must exist, and the one registered case proves it. A refuse-on-disagreement policy
        with NO override makes the correct behaviour unspellable, and the author deletes the
        guard instead. The reason is required and is printed: an override with no reason is a
        no-verify, a bypass leaving no trace of why. It is a SCOPE, not an assignment: a bare
        re-set leaks the divergent value past the branch that meant it, so later readers see an
        override as if it were the operator's statement.

        Returns:
            The override, which runs a callable in the copied context.

        """
        return Override(self, value, reason, label, announce_to)


class Override:
    """A registered, reasoned divergence from an ambient, run as a callable and never as a block."""

    def __init__(
        self,
        amb: Ambient,
        value: str,
        reason: str,
        label: str,
        announce_to: Callable[[str], None] | None,
    ) -> None:
        """Validate the override and keep what `run` needs.

        An UNREGISTERED override refuses, and the refusal names its successor: a refusal with no
        named successor is an invitation to invent one locally, which is the route-around this
        whole mechanism is trying not to provoke.

        Args:
            amb: The ambient to diverge from.
            value: The divergent value, which must be inside the vocabulary.
            reason: Why this branch knows better than the invocation; required.
            label: The registered site.
            announce_to: Where to say the override ran; stderr when omitted.

        Raises:
            ValueError: when the value, the reason or the registration is not acceptable.

        """
        if value not in amb.vocab:
            quoted = " / ".join(map(repr, amb.vocab))
            msg = (
                f"{amb.kw}.override({value!r}): not one of {quoted}. An override is at least "
                "as strict as the contract it diverges from."
            )
            raise ValueError(msg)
        if not reason or not str(reason).strip():
            msg = (
                f"{amb.kw}.override(...) requires a REASON. An override with no reason "
                "is `--no-verify` — a bypass that leaves no trace of why."
            )
            raise ValueError(msg)
        if (amb.kw, label) not in SANCTIONED_OVERRIDES:
            raise ValueError(_unregistered(amb.kw, label))
        self.amb = amb
        self.value = value
        self.reason = str(reason).strip()
        self.label = label
        self._out = announce_to

    def run[T](self, fn: Callable[[], T]) -> T:
        """Run `fn` in a FRESH CONTEXT where this ambient holds the divergent value.

        A NEW CONTEXT, NOT AN ASSIGNMENT, which is what makes it structurally costly to spell. The
        caller must hand over a CALLABLE and accept that the divergent binding cannot outlive it.
        When it displaces a bound value the divergence is announced with its reason. The callable
        takes no arguments: paperkit's version forwarded positional and keyword arguments, which
        a strictly typed signature cannot carry, so bind them with a lambda or a partial.

        Returns:
            Whatever `fn` returns.

        """
        out = self._out or _stderr_line
        bound, origin = self.amb.get(), self.amb.origin()
        if bound is not None and bound != self.value:
            out(
                f"   ⚑ {self.label}: {self.amb.kw} OVERRIDE {bound!r} → {self.value!r} "
                f"in a copied context (outer binding by {origin} is unchanged)\n"
                f"     reason: {self.reason}"
            )
        return self.amb.run_bound(self.value, f"override at {self.label}: {self.reason}", fn)

    def __enter__(self, *_exc: object) -> NoReturn:
        """Refuse a with block, deliberately, and name the callable successor.

        A with block would mutate the CURRENT context and undo it afterwards: the write-then-reset
        hole that write-once exists to close. Both halves of the protocol must exist so the
        refusal is the one a reader sees; with only an enter, Python raises its own protocol
        complaint BEFORE calling anything here, a correct refusal with no named successor. The
        exit is the same function, so there is no separate def that nothing ever calls.

        Raises:
            TypeError: always.

        """
        msg = (
            f"{self.amb.kw}.override(...) is not a context manager, deliberately.\n"
            "  A `with` block would mutate the CURRENT context and undo it afterwards — "
            "the\n  write-then-reset hole that write-once exists to close.\n"
            "  ⚑ Successor: pass the body as a CALLABLE, which runs it in a copied "
            "context:\n"
            f"      {self.amb.kw.upper()}.override({self.value!r}, reason=…, label=…) \\\n"
            "          .run(lambda: <the work>)"
        )
        raise TypeError(msg)

    __exit__ = __enter__


def _unregistered(kw: str, label: str) -> str:
    """Compose the refusal for an override that is not in the roster.

    Returns:
        The message, naming the three successors in the order to try them.

    """
    return (
        f"{kw}.override(...) at label {label!r} is NOT REGISTERED.\n"
        f"  A divergence from the ambient {kw} is a claim that this branch "
        "knows something\n"
        "  the invocation does not — which is true exactly once in this tree "
        "and is otherwise\n"
        "  the defect this mechanism exists to catch.\n"
        "  ⚑ Successors, in the order you should try them:\n"
        f"    1. DO NOT DIVERGE — let the ambient {kw} stand. This is right "
        "almost always;\n"
        "       a local branch that 'knows better' than the invocation is the "
        "failing shape.\n"
        "    2. State it at the ENTRY point instead, so it IS the ambient "
        "value and nothing\n"
        "       downstream has to disagree with anything "
        "(`require_at_entry`).\n"
        "    3. If the divergence is genuinely real — the tool's effect differs "
        "from the\n"
        "       operator's request, as with a dry run that writes then restores "
        "— register it\n"
        "       in `mikemol.treeio.ambient.SANCTIONED_OVERRIDES` under "
        f"({kw!r}, {label!r})\n"
        "       with the reason. That edit is REVIEWABLE, which is the point of "
        "the friction."
    )
