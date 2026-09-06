from __future__ import annotations

from hybrid_dispatch.config import ProjectConfig
from hybrid_dispatch.economics import financial_model
from hybrid_dispatch.optimizer import optimise_system
from hybrid_dispatch.profiles import build_representative_year, with_resilience_event


def test_financial_model_reconciles_and_is_finite() -> None:
    config = ProjectConfig()
    profile = with_resilience_event(build_representative_year(config))
    result = optimise_system(profile, config, require_resilience=True)
    financial, cash_flow = financial_model(result, config)
    component_capex = financial["pv_capex_aed"] + financial["battery_capex_aed"] + financial["biogas_capex_aed"]
    assert abs(financial["initial_capex_aed"] - component_capex) < 1e-5
    assert len(cash_flow) == config.analysis_years + 1
    assert financial["lcoe_aed_per_kwh"] > 0
    assert 0 <= financial["emissions_reduction_fraction"] <= 1
