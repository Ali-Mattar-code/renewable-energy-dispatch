"""Sparse linear capacity-planning and hourly dispatch optimisation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

from hybrid_dispatch.config import ProjectConfig, TechnologySet, capital_recovery_factor


@dataclass(frozen=True)
class CapacityPlan:
    pv_kw: float
    battery_kwh: float
    battery_kw: float
    biogas_kw: float


@dataclass(frozen=True)
class OptimisationResult:
    capacities: CapacityPlan
    dispatch: pd.DataFrame
    annual: dict[str, float]
    objective_aed_per_year: float
    solver_status: str


class _Variables:
    def __init__(self, periods: int) -> None:
        self.pv_kw = 0
        self.battery_kwh = 1
        self.battery_kw = 2
        self.biogas_kw = 3
        self.offset = 4
        self.grid_import = np.arange(self.offset, self.offset + periods)
        self.offset += periods
        self.grid_export = np.arange(self.offset, self.offset + periods)
        self.offset += periods
        self.battery_charge = np.arange(self.offset, self.offset + periods)
        self.offset += periods
        self.battery_discharge = np.arange(self.offset, self.offset + periods)
        self.offset += periods
        self.state_of_charge = np.arange(self.offset, self.offset + periods)
        self.offset += periods
        self.biogas_generation = np.arange(self.offset, self.offset + periods)
        self.offset += periods
        self.unserved = np.arange(self.offset, self.offset + periods)
        self.offset += periods
        self.curtailed = np.arange(self.offset, self.offset + periods)
        self.offset += periods
        self.size = self.offset


def _bounds(
    variables: _Variables,
    profile: pd.DataFrame,
    config: ProjectConfig,
    technologies: TechnologySet,
    fixed_capacities: CapacityPlan | None,
) -> list[tuple[float, float | None]]:
    bounds: list[tuple[float, float | None]] = [(0.0, None)] * variables.size
    bounds[variables.pv_kw] = (0.0, config.pv_capacity_max_kw if technologies.solar else 0.0)
    bounds[variables.battery_kwh] = (0.0, config.battery_energy_max_kwh if technologies.battery else 0.0)
    bounds[variables.battery_kw] = (0.0, config.battery_power_max_kw if technologies.battery else 0.0)
    bounds[variables.biogas_kw] = (0.0, config.biogas_capacity_max_kw if technologies.biogas else 0.0)
    if fixed_capacities is not None:
        bounds[variables.pv_kw] = (fixed_capacities.pv_kw, fixed_capacities.pv_kw)
        bounds[variables.battery_kwh] = (fixed_capacities.battery_kwh, fixed_capacities.battery_kwh)
        bounds[variables.battery_kw] = (fixed_capacities.battery_kw, fixed_capacities.battery_kw)
        bounds[variables.biogas_kw] = (fixed_capacities.biogas_kw, fixed_capacities.biogas_kw)

    for period in range(len(profile)):
        available = float(profile.iloc[period]["grid_available"])
        bounds[variables.grid_import[period]] = (0.0, config.grid_import_limit_kw * available)
        bounds[variables.grid_export[period]] = (0.0, config.grid_export_limit_kw * available)
        if not technologies.battery:
            bounds[variables.battery_charge[period]] = (0.0, 0.0)
            bounds[variables.battery_discharge[period]] = (0.0, 0.0)
            bounds[variables.state_of_charge[period]] = (0.0, 0.0)
        if not technologies.biogas:
            bounds[variables.biogas_generation[period]] = (0.0, 0.0)
    return bounds


def _objective(
    variables: _Variables,
    profile: pd.DataFrame,
    config: ProjectConfig,
) -> np.ndarray:
    objective = np.zeros(variables.size)
    rate = config.discount_rate
    objective[variables.pv_kw] = config.pv_capex_aed_per_kw * (
        capital_recovery_factor(rate, config.pv_lifetime_years) + config.pv_fixed_om_fraction
    )
    objective[variables.battery_kwh] = config.battery_capex_aed_per_kwh * (
        capital_recovery_factor(rate, config.battery_lifetime_years) + config.battery_fixed_om_fraction
    )
    objective[variables.battery_kw] = config.battery_power_capex_aed_per_kw * (
        capital_recovery_factor(rate, config.battery_lifetime_years) + config.battery_fixed_om_fraction
    )
    objective[variables.biogas_kw] = config.biogas_capex_aed_per_kw * (
        capital_recovery_factor(rate, config.biogas_lifetime_years) + config.biogas_fixed_om_fraction
    )

    weights = profile["weight_days"].to_numpy()
    objective[variables.grid_import] = weights * profile["import_tariff_aed_per_kwh"].to_numpy()
    objective[variables.grid_export] = -weights * profile["export_tariff_aed_per_kwh"].to_numpy()
    objective[variables.battery_discharge] = weights * config.battery_degradation_aed_per_kwh
    objective[variables.biogas_generation] = weights * config.biogas_variable_cost_aed_per_kwh
    objective[variables.unserved] = weights * config.value_of_lost_load_aed_per_kwh
    return objective


def optimise_system(
    profile: pd.DataFrame,
    config: ProjectConfig,
    *,
    technologies: TechnologySet | None = None,
    fixed_capacities: CapacityPlan | None = None,
    require_resilience: bool = False,
) -> OptimisationResult:
    """Co-optimise capacities and dispatch subject to physical constraints."""

    technologies = technologies or TechnologySet()
    periods = len(profile)
    if periods == 0 or periods % 24:
        raise ValueError("profile must contain complete representative days")
    variables = _Variables(periods)
    efficiency_charge = np.sqrt(config.battery_round_trip_efficiency)
    efficiency_discharge = np.sqrt(config.battery_round_trip_efficiency)

    equality_rows = periods * 2
    equality = lil_matrix((equality_rows, variables.size), dtype=float)
    equality_rhs = np.zeros(equality_rows)

    for period in range(periods):
        equality[period, variables.pv_kw] = profile.iloc[period]["solar_capacity_factor"]
        equality[period, variables.grid_import[period]] = 1.0
        equality[period, variables.battery_discharge[period]] = 1.0
        equality[period, variables.biogas_generation[period]] = 1.0
        equality[period, variables.unserved[period]] = 1.0
        equality[period, variables.battery_charge[period]] = -1.0
        equality[period, variables.grid_export[period]] = -1.0
        equality[period, variables.curtailed[period]] = -1.0
        equality_rhs[period] = profile.iloc[period]["load_kw"]

        previous = period - 1 if period % 24 else period + 23
        row = periods + period
        equality[row, variables.state_of_charge[period]] = 1.0
        equality[row, variables.state_of_charge[previous]] = -1.0
        equality[row, variables.battery_charge[period]] = -efficiency_charge
        equality[row, variables.battery_discharge[period]] = 1.0 / efficiency_discharge

    resilience_rows = 1 if require_resilience else 0
    inequality_rows = periods * 5 + 1 + resilience_rows
    inequality = lil_matrix((inequality_rows, variables.size), dtype=float)
    inequality_rhs = np.zeros(inequality_rows)
    for period in range(periods):
        base = period * 5
        inequality[base, variables.battery_charge[period]] = 1.0
        inequality[base, variables.battery_kw] = -1.0
        inequality[base + 1, variables.battery_discharge[period]] = 1.0
        inequality[base + 1, variables.battery_kw] = -1.0
        inequality[base + 2, variables.state_of_charge[period]] = 1.0
        inequality[base + 2, variables.battery_kwh] = -config.battery_max_soc_fraction
        inequality[base + 3, variables.battery_kwh] = config.battery_min_soc_fraction
        inequality[base + 3, variables.state_of_charge[period]] = -1.0
        inequality[base + 4, variables.biogas_generation[period]] = 1.0
        inequality[base + 4, variables.biogas_kw] = -1.0

    resource_row = periods * 5
    inequality[resource_row, variables.biogas_generation] = profile["weight_days"].to_numpy()
    annual_biogas_energy = (
        config.feedstock_tonnes_per_day
        * config.specific_biogas_yield_nm3_per_tonne
        * config.methane_fraction
        * config.methane_energy_kwh_per_nm3
        * config.biogas_electrical_efficiency
        * 365.0
    )
    inequality_rhs[resource_row] = annual_biogas_energy if technologies.biogas else 0.0
    if require_resilience:
        if "stress_case" not in profile or not (profile["stress_case"] == 1).any():
            raise ValueError("require_resilience needs a profile containing a stress case")
        reliability_row = resource_row + 1
        stress_periods = np.flatnonzero(profile["stress_case"].to_numpy() == 1)
        inequality[reliability_row, variables.unserved[stress_periods]] = 1.0
        inequality_rhs[reliability_row] = 1e-7

    solution = linprog(
        _objective(variables, profile, config),
        A_ub=inequality.tocsr(),
        b_ub=inequality_rhs,
        A_eq=equality.tocsr(),
        b_eq=equality_rhs,
        bounds=_bounds(variables, profile, config, technologies, fixed_capacities),
        method="highs",
    )
    if not solution.success:
        raise RuntimeError(f"Optimisation failed: {solution.message}")

    values = solution.x
    dispatch = profile.copy()
    dispatch["pv_generation_kw"] = dispatch["solar_capacity_factor"] * values[variables.pv_kw]
    dispatch["grid_import_kw"] = values[variables.grid_import]
    dispatch["grid_export_kw"] = values[variables.grid_export]
    dispatch["battery_charge_kw"] = values[variables.battery_charge]
    dispatch["battery_discharge_kw"] = values[variables.battery_discharge]
    dispatch["state_of_charge_kwh"] = values[variables.state_of_charge]
    dispatch["biogas_generation_kw"] = values[variables.biogas_generation]
    dispatch["unserved_kw"] = values[variables.unserved]
    dispatch["curtailed_kw"] = values[variables.curtailed]
    dispatch["marginal_energy_value_aed_per_kwh"] = np.asarray(solution.eqlin.marginals[:periods])

    weights = dispatch["weight_days"].to_numpy()

    def annual_energy(column: str) -> float:
        return float(np.dot(dispatch[column].to_numpy(), weights))

    load_energy = annual_energy("load_kw")
    pv_used = annual_energy("pv_generation_kw") - annual_energy("curtailed_kw")
    biogas_energy = annual_energy("biogas_generation_kw")
    grid_energy = annual_energy("grid_import_kw")
    unserved_energy = annual_energy("unserved_kw")
    battery_charge_energy = annual_energy("battery_charge_kw")
    battery_discharge_energy = annual_energy("battery_discharge_kw")
    storage_losses = max(0.0, battery_charge_energy - battery_discharge_energy)
    grid_export_energy = annual_energy("grid_export_kw")
    renewable_to_load = max(0.0, pv_used + biogas_energy - grid_export_energy - storage_losses)
    annual = {
        "load_kwh": load_energy,
        "pv_generated_kwh": annual_energy("pv_generation_kw"),
        "pv_used_kwh": pv_used,
        "biogas_generated_kwh": biogas_energy,
        "battery_charge_kwh": battery_charge_energy,
        "battery_discharge_kwh": battery_discharge_energy,
        "storage_losses_kwh": storage_losses,
        "grid_import_kwh": grid_energy,
        "grid_export_kwh": grid_export_energy,
        "curtailed_kwh": annual_energy("curtailed_kw"),
        "unserved_kwh": unserved_energy,
        "renewable_fraction": min(1.0, renewable_to_load / max(load_energy - unserved_energy, 1.0)),
        "grid_emissions_kg": grid_energy * config.grid_emissions_kg_per_kwh,
        "biogas_operational_emissions_kg": biogas_energy * config.biogas_operational_emissions_kg_per_kwh,
    }
    return OptimisationResult(
        capacities=CapacityPlan(
            pv_kw=float(values[variables.pv_kw]),
            battery_kwh=float(values[variables.battery_kwh]),
            battery_kw=float(values[variables.battery_kw]),
            biogas_kw=float(values[variables.biogas_kw]),
        ),
        dispatch=dispatch,
        annual=annual,
        objective_aed_per_year=float(solution.fun),
        solver_status=solution.message,
    )
