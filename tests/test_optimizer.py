from __future__ import annotations

import numpy as np

from hybrid_dispatch.config import ProjectConfig, TechnologySet
from hybrid_dispatch.optimizer import optimise_system
from hybrid_dispatch.profiles import build_representative_year, with_resilience_event
from hybrid_dispatch.scenarios import resilience_envelope


def test_power_balance_and_biogas_resource() -> None:
    config = ProjectConfig()
    result = optimise_system(build_representative_year(config), config)
    dispatch = result.dispatch
    supply = (
        dispatch["pv_generation_kw"]
        + dispatch["grid_import_kw"]
        + dispatch["battery_discharge_kw"]
        + dispatch["biogas_generation_kw"]
        + dispatch["unserved_kw"]
    )
    demand = (
        dispatch["load_kw"]
        + dispatch["battery_charge_kw"]
        + dispatch["grid_export_kw"]
        + dispatch["curtailed_kw"]
    )
    assert np.max(np.abs(supply - demand)) < 1e-5

    available_biogas = (
        config.feedstock_tonnes_per_day
        * config.specific_biogas_yield_nm3_per_tonne
        * config.methane_fraction
        * config.methane_energy_kwh_per_nm3
        * config.biogas_electrical_efficiency
        * 365
    )
    assert result.annual["biogas_generated_kwh"] <= available_biogas + 1e-4


def test_disabled_technologies_have_zero_capacity() -> None:
    config = ProjectConfig()
    result = optimise_system(
        build_representative_year(config),
        config,
        technologies=TechnologySet(solar=True, battery=False, biogas=False),
    )
    assert abs(result.capacities.battery_kwh) < 1e-8
    assert abs(result.capacities.biogas_kw) < 1e-8


def test_resilient_design_serves_outage() -> None:
    config = ProjectConfig()
    profile = with_resilience_event(build_representative_year(config))
    result = optimise_system(profile, config, require_resilience=True)
    outage = (result.dispatch["stress_case"] == 1) & (result.dispatch["grid_available"] == 0)
    assert result.dispatch.loc[outage, "unserved_kw"].sum() < 1e-5
    assert result.capacities.battery_kwh > 0


def test_fixed_design_resilience_envelope_is_bounded_and_complete() -> None:
    config = ProjectConfig()
    design_profile = with_resilience_event(build_representative_year(config))
    design = optimise_system(design_profile, config, require_resilience=True)
    envelope = resilience_envelope(
        design.capacities,
        config,
        months=(8,),
        start_hours=(12, 18),
        durations=(2, 6),
    )
    assert len(envelope) == 4
    assert set(envelope["duration_hours"]) == {2, 6}
    assert envelope["served_fraction"].between(0.0, 1.0).all()
    assert (envelope["unserved_energy_kwh"] >= 0.0).all()


def test_renewable_fraction_reconciles_with_grid_supply() -> None:
    config = ProjectConfig()
    result = optimise_system(build_representative_year(config), config)
    served_load = result.annual["load_kwh"] - result.annual["unserved_kwh"]
    expected = 1.0 - result.annual["grid_import_kwh"] / served_load
    assert np.isclose(result.annual["renewable_fraction"], expected)
    assert result.annual["storage_losses_kwh"] >= 0
