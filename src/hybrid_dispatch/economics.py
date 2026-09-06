"""Lifecycle cash flow, LCOE and emissions accounting."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from hybrid_dispatch.config import ProjectConfig
from hybrid_dispatch.optimizer import OptimisationResult


def _irr(cash_flows: list[float]) -> float | None:
    def npv(rate: float) -> float:
        return sum(value / (1.0 + rate) ** year for year, value in enumerate(cash_flows))

    low, high = -0.95, 3.0
    if npv(low) * npv(high) > 0:
        return None
    for _ in range(120):
        middle = (low + high) / 2.0
        if npv(low) * npv(middle) <= 0:
            high = middle
        else:
            low = middle
    return (low + high) / 2.0


def financial_model(result: OptimisationResult, config: ProjectConfig) -> tuple[dict[str, float | None], pd.DataFrame]:
    """Convert a one-year dispatch plan into a transparent lifecycle case."""

    capacity = result.capacities
    pv_capex = capacity.pv_kw * config.pv_capex_aed_per_kw
    battery_capex = (
        capacity.battery_kwh * config.battery_capex_aed_per_kwh
        + capacity.battery_kw * config.battery_power_capex_aed_per_kw
    )
    biogas_capex = capacity.biogas_kw * config.biogas_capex_aed_per_kw
    total_capex = pv_capex + battery_capex + biogas_capex

    dispatch = result.dispatch
    weights = dispatch["weight_days"].to_numpy()
    grid_cost = float(
        np.dot(
            dispatch["grid_import_kw"].to_numpy() * dispatch["import_tariff_aed_per_kwh"].to_numpy(),
            weights,
        )
    )
    export_revenue = float(
        np.dot(
            dispatch["grid_export_kw"].to_numpy() * dispatch["export_tariff_aed_per_kwh"].to_numpy(),
            weights,
        )
    )
    biogas_variable = result.annual["biogas_generated_kwh"] * config.biogas_variable_cost_aed_per_kwh
    battery_variable = result.annual["battery_discharge_kwh"] * config.battery_degradation_aed_per_kwh
    fixed_om = (
        pv_capex * config.pv_fixed_om_fraction
        + battery_capex * config.battery_fixed_om_fraction
        + biogas_capex * config.biogas_fixed_om_fraction
    )
    annual_operating_cost = grid_cost - export_revenue + biogas_variable + battery_variable + fixed_om
    baseline_grid_cost = result.annual["load_kwh"] * config.grid_tariff_aed_per_kwh
    first_year_saving = baseline_grid_cost - annual_operating_cost

    cash_flows = [-total_capex]
    records = [{"year": 0, "net_cash_flow_aed": -total_capex, "discounted_cash_flow_aed": -total_capex}]
    cumulative_discounted = -total_capex
    discounted_costs = total_capex
    discounted_energy = 0.0
    payback_year: float | None = None

    for year in range(1, config.analysis_years + 1):
        pv_factor = (1.0 - config.pv_degradation_fraction) ** (year - 1)
        pv_shortfall_kwh = result.annual["pv_used_kwh"] * (1.0 - pv_factor)
        annual_saving = first_year_saving - pv_shortfall_kwh * config.grid_tariff_aed_per_kwh
        replacement = battery_capex if battery_capex > 0 and year % config.battery_lifetime_years == 0 else 0.0
        net_cash_flow = annual_saving - replacement
        discount_factor = (1.0 + config.discount_rate) ** year
        discounted_cash_flow = net_cash_flow / discount_factor
        previous_cumulative = cumulative_discounted
        cumulative_discounted += discounted_cash_flow
        if payback_year is None and cumulative_discounted >= 0 and discounted_cash_flow > 0:
            payback_year = year - 1 + max(0.0, -previous_cumulative / discounted_cash_flow)
        cash_flows.append(net_cash_flow)
        records.append(
            {
                "year": year,
                "net_cash_flow_aed": net_cash_flow,
                "discounted_cash_flow_aed": discounted_cash_flow,
            }
        )
        discounted_costs += (annual_operating_cost + replacement) / discount_factor
        discounted_energy += result.annual["load_kwh"] / discount_factor

    npv = sum(record["discounted_cash_flow_aed"] for record in records)
    irr = _irr(cash_flows)
    baseline_emissions = result.annual["load_kwh"] * config.grid_emissions_kg_per_kwh
    project_emissions = result.annual["grid_emissions_kg"] + result.annual["biogas_operational_emissions_kg"]
    summary: dict[str, float | None] = {
        "initial_capex_aed": total_capex,
        "pv_capex_aed": pv_capex,
        "battery_capex_aed": battery_capex,
        "biogas_capex_aed": biogas_capex,
        "annual_operating_cost_aed": annual_operating_cost,
        "baseline_grid_cost_aed": baseline_grid_cost,
        "first_year_saving_aed": first_year_saving,
        "npv_aed": npv,
        "irr": irr,
        "discounted_payback_years": payback_year,
        "lcoe_aed_per_kwh": discounted_costs / max(discounted_energy, 1.0),
        "baseline_lcoe_aed_per_kwh": config.grid_tariff_aed_per_kwh,
        "annual_emissions_avoided_kg": max(0.0, baseline_emissions - project_emissions),
        "emissions_reduction_fraction": max(0.0, 1.0 - project_emissions / max(baseline_emissions, 1.0)),
    }
    for key, value in summary.items():
        if isinstance(value, float) and not math.isfinite(value):
            summary[key] = None
    return summary, pd.DataFrame(records)
