"""Technology, sensitivity and resilience scenario orchestration."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from hybrid_dispatch.config import ProjectConfig, TechnologySet
from hybrid_dispatch.economics import financial_model
from hybrid_dispatch.optimizer import OptimisationResult, optimise_system
from hybrid_dispatch.profiles import build_representative_year, with_resilience_event


SCENARIOS = {
    "solar_only": TechnologySet(solar=True, battery=False, biogas=False),
    "solar_battery": TechnologySet(solar=True, battery=True, biogas=False),
    "solar_biogas": TechnologySet(solar=True, battery=False, biogas=True),
    "full_hybrid": TechnologySet(solar=True, battery=True, biogas=True),
}


def compare_technologies(config: ProjectConfig) -> tuple[pd.DataFrame, dict[str, OptimisationResult]]:
    profile = build_representative_year(config)
    rows: list[dict[str, float | str | None]] = []
    results: dict[str, OptimisationResult] = {}
    for name, technologies in SCENARIOS.items():
        result = optimise_system(profile, config, technologies=technologies)
        financial, _ = financial_model(result, config)
        results[name] = result
        rows.append(
            {
                "scenario": name,
                "pv_kw": result.capacities.pv_kw,
                "battery_kwh": result.capacities.battery_kwh,
                "battery_kw": result.capacities.battery_kw,
                "biogas_kw": result.capacities.biogas_kw,
                "renewable_fraction": result.annual["renewable_fraction"],
                "grid_import_kwh": result.annual["grid_import_kwh"],
                "unserved_kwh": result.annual["unserved_kwh"],
                "lcoe_aed_per_kwh": financial["lcoe_aed_per_kwh"],
                "npv_aed": financial["npv_aed"],
                "irr": financial["irr"],
                "annual_emissions_avoided_kg": financial["annual_emissions_avoided_kg"],
            }
        )
    resilience_profile = with_resilience_event(profile)
    resilient = optimise_system(resilience_profile, config, require_resilience=True)
    resilient_financial, _ = financial_model(resilient, config)
    results["resilient_full_hybrid"] = resilient
    rows.append(
        {
            "scenario": "resilient_full_hybrid",
            "pv_kw": resilient.capacities.pv_kw,
            "battery_kwh": resilient.capacities.battery_kwh,
            "battery_kw": resilient.capacities.battery_kw,
            "biogas_kw": resilient.capacities.biogas_kw,
            "renewable_fraction": resilient.annual["renewable_fraction"],
            "grid_import_kwh": resilient.annual["grid_import_kwh"],
            "unserved_kwh": resilient.annual["unserved_kwh"],
            "lcoe_aed_per_kwh": resilient_financial["lcoe_aed_per_kwh"],
            "npv_aed": resilient_financial["npv_aed"],
            "irr": resilient_financial["irr"],
            "annual_emissions_avoided_kg": resilient_financial["annual_emissions_avoided_kg"],
        }
    )
    return pd.DataFrame(rows), results


def sensitivity_analysis(config: ProjectConfig) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    for tariff_multiplier in [0.8, 1.0, 1.2]:
        for yield_multiplier in [0.6, 1.0, 1.4]:
            scenario = replace(
                config,
                grid_tariff_aed_per_kwh=config.grid_tariff_aed_per_kwh * tariff_multiplier,
                specific_biogas_yield_nm3_per_tonne=(
                    config.specific_biogas_yield_nm3_per_tonne * yield_multiplier
                ),
            )
            result = optimise_system(build_representative_year(scenario), scenario)
            financial, _ = financial_model(result, scenario)
            rows.append(
                {
                    "grid_tariff_multiplier": tariff_multiplier,
                    "biogas_yield_multiplier": yield_multiplier,
                    "pv_kw": result.capacities.pv_kw,
                    "battery_kwh": result.capacities.battery_kwh,
                    "biogas_kw": result.capacities.biogas_kw,
                    "renewable_fraction": result.annual["renewable_fraction"],
                    "lcoe_aed_per_kwh": float(financial["lcoe_aed_per_kwh"]),
                    "npv_aed": float(financial["npv_aed"]),
                }
            )
    return pd.DataFrame(rows)


def resilience_test(result: OptimisationResult) -> dict[str, float]:
    """Summarise service during the embedded annual outage day."""

    mask = (result.dispatch["stress_case"] == 1) & (result.dispatch["grid_available"] == 0)
    outage_load = float((result.dispatch.loc[mask, "load_kw"] * result.dispatch.loc[mask, "weight_days"]).sum())
    outage_unserved = float(
        (result.dispatch.loc[mask, "unserved_kw"] * result.dispatch.loc[mask, "weight_days"]).sum()
    )
    return {
        "representative_outage_hours": int(mask.sum()),
        "outage_load_kwh_weighted": outage_load,
        "outage_unserved_kwh_weighted": outage_unserved,
        "outage_load_served_fraction": 1.0 - outage_unserved / max(outage_load, 1.0),
    }
