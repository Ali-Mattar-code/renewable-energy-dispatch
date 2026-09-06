"""Typed assumptions and technology contracts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProjectConfig:
    """All economic and engineering assumptions for one feasibility case.

    Defaults describe an illustrative Dubai industrial load. They are editable
    scenario inputs, not vendor quotations or investment advice.
    """

    location: str = "Dubai, UAE — illustrative"
    analysis_years: int = 25
    discount_rate: float = 0.07
    daily_load_kwh: float = 9_000.0

    grid_import_limit_kw: float = 1_500.0
    grid_export_limit_kw: float = 600.0
    grid_tariff_aed_per_kwh: float = 0.44
    export_tariff_aed_per_kwh: float = 0.05
    grid_emissions_kg_per_kwh: float = 0.404
    value_of_lost_load_aed_per_kwh: float = 20.0

    pv_capex_aed_per_kw: float = 2_500.0
    pv_fixed_om_fraction: float = 0.015
    pv_lifetime_years: int = 25
    pv_capacity_max_kw: float = 3_000.0
    pv_degradation_fraction: float = 0.0045

    battery_capex_aed_per_kwh: float = 900.0
    battery_power_capex_aed_per_kw: float = 350.0
    battery_fixed_om_fraction: float = 0.02
    battery_lifetime_years: int = 12
    battery_energy_max_kwh: float = 7_500.0
    battery_power_max_kw: float = 2_000.0
    battery_round_trip_efficiency: float = 0.90
    battery_min_soc_fraction: float = 0.10
    battery_max_soc_fraction: float = 0.95
    battery_degradation_aed_per_kwh: float = 0.035

    biogas_capex_aed_per_kw: float = 14_000.0
    biogas_fixed_om_fraction: float = 0.055
    biogas_variable_cost_aed_per_kwh: float = 0.045
    biogas_lifetime_years: int = 20
    biogas_capacity_max_kw: float = 750.0
    biogas_electrical_efficiency: float = 0.35
    feedstock_tonnes_per_day: float = 34.5
    specific_biogas_yield_nm3_per_tonne: float = 60.0
    methane_fraction: float = 0.60
    methane_energy_kwh_per_nm3: float = 9.97
    biogas_operational_emissions_kg_per_kwh: float = 0.05

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TechnologySet:
    solar: bool = True
    battery: bool = True
    biogas: bool = True


def capital_recovery_factor(rate: float, years: int) -> float:
    if years <= 0:
        raise ValueError("years must be positive")
    if rate == 0:
        return 1.0 / years
    factor = (1.0 + rate) ** years
    return rate * factor / (factor - 1.0)


def load_config(path: str | Path) -> ProjectConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    allowed = {field.name for field in fields(ProjectConfig)}
    unknown = set(payload).difference(allowed)
    if unknown:
        raise ValueError(f"Unknown configuration fields: {sorted(unknown)}")
    return ProjectConfig(**payload)
