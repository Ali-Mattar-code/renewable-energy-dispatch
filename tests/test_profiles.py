from __future__ import annotations

import numpy as np
import pytest

from hybrid_dispatch.config import ProjectConfig
from hybrid_dispatch.profiles import build_representative_year, with_resilience_event


def test_profile_reconciles_to_legacy_load() -> None:
    config = ProjectConfig()
    profile = build_representative_year(config)
    annual_load = np.dot(profile["load_kw"], profile["weight_days"])
    assert len(profile) == 288
    assert abs(annual_load - config.daily_load_kwh * 365) < 1e-5


def test_resilience_day_preserves_annual_weight() -> None:
    profile = with_resilience_event(build_representative_year(ProjectConfig()))
    assert len(profile) == 312
    for hour in range(24):
        assert profile.loc[profile["hour"] == hour, "weight_days"].sum() == 365
    assert ((profile["stress_case"] == 1) & (profile["grid_available"] == 0)).sum() == 6


@pytest.mark.parametrize(
    "kwargs",
    [{"month": 0}, {"start_hour": 24}, {"hours": 0}, {"hours": 25}],
)
def test_resilience_event_rejects_invalid_windows(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        with_resilience_event(build_representative_year(ProjectConfig()), **kwargs)
