# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""What a repo supplies to plan admission, in one frozen value (W1844, of W1842).

luthen's `checks/opa_plan.py` gates a `tofu apply` on a policy verdict bound to the planfile's hash.
Its repo-specific names are module constants (the terraform and policy directories, the rego
package `luthen`, the roots it applies as root and the root-owned state directory), which a second
repo cannot reuse without editing the file. This is that set as a value a consumer builds once, and
`luthen()` is the value that reproduces luthen's constants exactly (census: W1843).

⚑ THE TWO SECURITY SWITCHES DEFAULT ON, FAIL CLOSED (estate-dd and luthen-observability-ab agreed,
2026-10-22): `drop_privileges` and `root_custody` are the rules luthen runs as root under (the
euid check, root-owned verdict directories). A consumer that does not run as root, estate, switches
them off by saying so in its own config after the operator rules; a consumer that merely forgets to
configure custody gets the protection. Turning either off is never the dist's default.

⚑ THE PLANFILE-HASH BINDING IS NOT A SWITCH: a verdict is bound to the sha256 of the planfile it
judged for every consumer, so there is no field for it.

⚑ NOTHING HERE READS THE DISK OR THE ENVIRONMENT: a config is a value, and building one has no side
effect, so a test can make any number of them.
"""

from dataclasses import dataclass, field
from pathlib import Path

LUTHEN_PACKAGE = "luthen"
LUTHEN_ROOT_STATE = Path("/var/lib/luthen/opa_plan")
LUTHEN_OPA_PIN = "1.20.2"
LUTHEN_TEMP_PREFIX = "luthen."
LUTHEN_ROOT_PLANNED = frozenset({"host"})


@dataclass(frozen=True, slots=True)
class PlanConfig:
    """Everything repo-specific that plan admission needs, with the security switches closed."""

    root: Path
    terraform: Path
    policy: Path
    rego_package: str
    opa_pin: str
    user_state: Path
    root_state: Path | None = None
    root_planned: frozenset[str] = field(default_factory=frozenset)
    temp_prefix: str = "plan."
    drop_privileges: bool = True
    root_custody: bool = True
    trusted_uid: int = 0
    preconditions_required: bool = True

    def plan_query(self) -> str:
        """Name the rego rule set the plan is judged by.

        Returns:
            `data.<package>.plan`.

        """
        return f"data.{self.rego_package}.plan"

    def interlock_query(self, kind: str) -> str:
        """Name the rego rule that lists an activation's unmet preconditions.

        Returns:
            `data.<package>.interlocks.<kind>.defer`.

        """
        return f"data.{self.rego_package}.interlocks.{kind}.defer"

    def interlocks(self) -> Path:
        """Name the directory the interlock policies live in.

        Returns:
            `<policy>/interlocks`.

        """
        return self.policy / "interlocks"

    def witness_data(self) -> Path:
        """Name the file that declares each root's post-apply witness.

        ⚑ CENTRAL, UNDER THE POLICY, so the policy digest hashes it into every verdict (W259).

        Returns:
            `<policy>/witnesses/data.json`.

        """
        return self.policy / "witnesses" / "data.json"

    def preconditions_data(self) -> Path:
        """Name the file that declares the cross-apply ordering rules (W263).

        Returns:
            `<policy>/preconditions/data.json`.

        """
        return self.policy / "preconditions" / "data.json"

    def allowed_destroys(self) -> Path:
        """Name the file that lists the destroys the policy allows.

        Returns:
            `<policy>/allowed_destroys/data.json`; a verdict records its digest when it exists.

        """
        return self.policy / "allowed_destroys" / "data.json"

    def state_dir(self, root_name: str) -> Path:
        """Name the verdict, witness and ledger directory for a terraform root.

        ⚑ A ROOT-PLANNED ROOT'S STATE IS ROOT-OWNED, THE REST IS THE USER'S: with custody on and a
        root state directory configured, a root named in `root_planned` keeps its records in the
        root-owned directory, where the unprivileged planner can neither write nor replace one.

        Returns:
            the root-owned directory for a root-planned root under custody, else the user's.

        """
        held = self.root_custody and self.root_state is not None
        if held and root_name in self.root_planned and self.root_state is not None:
            return self.root_state
        return self.user_state


def luthen(root: Path) -> PlanConfig:
    """Give luthen's configuration over the repo at `root`, today's constants exactly.

    Returns:
        the config `checks/opa_plan.py` and `checks/interlock.py` hard-code (census: W1843).

    """
    return PlanConfig(
        root=root,
        terraform=root / "terraform",
        policy=root / "policy",
        rego_package=LUTHEN_PACKAGE,
        opa_pin=LUTHEN_OPA_PIN,
        user_state=root / ".claude" / "opa_plan",
        root_state=LUTHEN_ROOT_STATE,
        root_planned=LUTHEN_ROOT_PLANNED,
        temp_prefix=LUTHEN_TEMP_PREFIX,
    )
