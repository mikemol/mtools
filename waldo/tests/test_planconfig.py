# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The plan-admission config reproduces luthen's constants and fails closed for others (W1844).

⚑ THE DEFAULT IS THE SAFE ONE: a config that names no switches has privilege drop and root custody
on, so a consumer that forgets them is protected, and only an explicit config turns either off.
"""

from pathlib import Path

from mikemol.waldo import planconfig
from mikemol.waldo.planconfig import PlanConfig

_ROOT = Path("/r")


def _bare() -> PlanConfig:
    return PlanConfig(
        root=_ROOT,
        terraform=_ROOT / "tf",
        policy=_ROOT / "pol",
        rego_package="estate",
        opa_pin="1.20.2",
        user_state=_ROOT / "st",
    )


def test_the_luthen_config_is_todays_constants_over_the_repo_root() -> None:
    """Terraform, policy, state, package, pin, host roots and prefix are opa_plan's constants."""
    cfg = planconfig.luthen(_ROOT)
    assert cfg.terraform == _ROOT / "terraform"
    assert cfg.policy == _ROOT / "policy"
    assert cfg.user_state == _ROOT / ".claude" / "opa_plan"
    assert cfg.root_state == Path("/var/lib/luthen/opa_plan")
    assert (cfg.rego_package, cfg.opa_pin, cfg.temp_prefix) == ("luthen", "1.20.2", "luthen.")
    assert cfg.root_planned == frozenset({"host"})


def test_the_queries_are_luthens_for_luthen_and_the_consumers_for_a_consumer() -> None:
    """data.luthen.plan and data.luthen.interlocks.<kind>.defer, with the package swapped."""
    cfg = planconfig.luthen(_ROOT)
    assert cfg.plan_query() == "data.luthen.plan"
    assert cfg.interlock_query("tier_compact") == "data.luthen.interlocks.tier_compact.defer"
    assert _bare().plan_query() == "data.estate.plan"
    assert cfg.interlocks() == _ROOT / "policy" / "interlocks"


def test_a_host_root_keeps_its_records_in_the_root_owned_directory() -> None:
    """The root-planned root uses the root state, any other root the user's."""
    cfg = planconfig.luthen(_ROOT)
    assert cfg.state_dir("host") == Path("/var/lib/luthen/opa_plan")
    assert cfg.state_dir("stage2") == _ROOT / ".claude" / "opa_plan"


def test_a_config_that_names_no_switches_has_both_security_rules_on() -> None:
    """Fail closed: privilege drop and root custody default ON."""
    cfg = _bare()
    assert cfg.drop_privileges is True
    assert cfg.root_custody is True


def test_custody_off_sends_every_root_to_the_users_state() -> None:
    """A consumer without root turns custody off and has no root-owned directory to use."""
    cfg = planconfig.luthen(_ROOT)
    open_cfg = PlanConfig(
        root=cfg.root,
        terraform=cfg.terraform,
        policy=cfg.policy,
        rego_package=cfg.rego_package,
        opa_pin=cfg.opa_pin,
        user_state=cfg.user_state,
        root_state=cfg.root_state,
        root_planned=cfg.root_planned,
        root_custody=False,
    )
    assert open_cfg.state_dir("host") == cfg.user_state
