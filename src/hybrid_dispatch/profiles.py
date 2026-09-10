"""Deterministic representative-year load, solar and tariff profiles."""

from __future__ import annotations

import numpy as np
import pandas as pd

from hybrid_dispatch.config import ProjectConfig


DAYS_PER_MONTH = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], dtype=float)


def _daily_load_shape() -> np.ndarray:
    shape = np.array(
        [
            0.70,
            0.66,
            0.64,
            0.63,
            0.65,
            0.72,
            0.84,
            0.94,
            1.03,
            1.08,
            1.10,
            1.12,
            1.15,
            1.16,
            1.18,
            1.20,
            1.22,
            1.27,
            1.34,
            1.39,
            1.36,
            1.23,
            1.03,
            0.83,
        ]
    )
    return shape / shape.mean()


def _solar_capacity_factor(month: int, hour: int) -> float:
    seasonal_peak = np.array([0.77, 0.81, 0.86, 0.90, 0.91, 0.88, 0.84, 0.85, 0.89, 0.87, 0.81, 0.76])
    daylight_hours = np.array([10.7, 11.2, 12.0, 12.8, 13.4, 13.7, 13.5, 13.0, 12.3, 11.6, 10.9, 10.6])
    sunrise = 12.0 - daylight_hours[month - 1] / 2.0
    sunset = 12.0 + daylight_hours[month - 1] / 2.0
    midpoint = hour + 0.5
    if midpoint <= sunrise or midpoint >= sunset:
        return 0.0
    phase = (midpoint - sunrise) / (sunset - sunrise)
    return float(seasonal_peak[month - 1] * np.sin(np.pi * phase) ** 1.35)


def build_representative_year(config: ProjectConfig) -> pd.DataFrame:
    """Build 12 representative days with monthly frequency weights.

    Battery state of charge is cycled within each representative day. Each hour
    is weighted by the number of days in its month for annual energy and cost.
    """

    daily_shape = _daily_load_shape()
    cooling_multiplier = np.array([0.80, 0.82, 0.88, 0.96, 1.08, 1.20, 1.28, 1.27, 1.17, 1.02, 0.88, 0.82])
    weighted_mean = np.average(cooling_multiplier, weights=DAYS_PER_MONTH)
    cooling_multiplier = cooling_multiplier / weighted_mean
    average_hourly_load = config.daily_load_kwh / 24.0

    rows: list[dict[str, float | int | str]] = []
    for month in range(1, 13):
        for hour in range(24):
            load_kw = average_hourly_load * cooling_multiplier[month - 1] * daily_shape[hour]
            rows.append(
                {
                    "timestamp": f"2026-{month:02d}-15 {hour:02d}:00",
                    "month": month,
                    "hour": hour,
                    "weight_days": DAYS_PER_MONTH[month - 1],
                    "load_kw": load_kw,
                    "solar_capacity_factor": _solar_capacity_factor(month, hour),
                    "grid_available": 1.0,
                    "stress_case": 0,
                    "import_tariff_aed_per_kwh": config.grid_tariff_aed_per_kwh,
                    "export_tariff_aed_per_kwh": config.export_tariff_aed_per_kwh,
                }
            )
    return pd.DataFrame(rows)


def with_resilience_event(
    profile: pd.DataFrame,
    *,
    month: int = 8,
    start_hour: int = 18,
    hours: int = 6,
) -> pd.DataFrame:
    """Replace one regular day with a grid-outage stress day.

    The normal monthly representative loses one day of annual weight. A copied
    day with weight one is appended, so annual energy still represents 365 days.
    """

    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")
    if not 0 <= start_hour <= 23:
        raise ValueError("start_hour must be between 0 and 23")
    if not 1 <= hours <= 24:
        raise ValueError("hours must be between 1 and 24")

    stressed = profile.copy()
    regular_mask = stressed["month"] == month
    if not regular_mask.any() or (stressed.loc[regular_mask, "weight_days"] < 1.0).any():
        raise ValueError("profile does not contain a valid representative month")
    stressed.loc[regular_mask, "weight_days"] -= 1.0
    outage_day = stressed.loc[regular_mask].copy()
    outage_day["weight_days"] = 1.0
    outage_day["stress_case"] = 1
    outage_day["timestamp"] = outage_day["hour"].map(
        lambda hour: f"2026-{month:02d}-outage {hour:02d}:00"
    )
    outage_hours = {(start_hour + offset) % 24 for offset in range(hours)}
    outage_day.loc[outage_day["hour"].isin(outage_hours), "grid_available"] = 0.0
    return pd.concat([stressed, outage_day], ignore_index=True)
