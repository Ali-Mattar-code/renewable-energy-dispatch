"""FastAPI surface for parameterised feasibility runs."""

from __future__ import annotations

from dataclasses import replace

from fastapi import FastAPI
from pydantic import BaseModel, Field

from hybrid_dispatch.config import ProjectConfig
from hybrid_dispatch.economics import financial_model
from hybrid_dispatch.optimizer import optimise_system
from hybrid_dispatch.profiles import build_representative_year


app = FastAPI(title="Hybrid Energy Optimiser", version="1.0.0")


class FeasibilityRequest(BaseModel):
    daily_load_kwh: float = Field(default=9_000.0, gt=0, le=100_000)
    grid_tariff_aed_per_kwh: float = Field(default=0.44, gt=0, le=5)
    feedstock_tonnes_per_day: float = Field(default=34.5, ge=0, le=1_000)
    discount_rate: float = Field(default=0.07, ge=0, le=0.5)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/optimise")
def optimise(request: FeasibilityRequest) -> dict[str, object]:
    config = replace(ProjectConfig(), **request.model_dump())
    result = optimise_system(build_representative_year(config), config)
    financial, _ = financial_model(result, config)
    return {
        "capacities": result.capacities.__dict__,
        "annual": result.annual,
        "financial": financial,
        "scope": "illustrative feasibility result; not engineering or investment advice",
    }
