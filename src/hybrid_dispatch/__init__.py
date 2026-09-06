"""Hybrid solar, battery and biogas feasibility optimiser."""

from hybrid_dispatch.config import ProjectConfig
from hybrid_dispatch.optimizer import OptimisationResult, optimise_system
from hybrid_dispatch.profiles import build_representative_year

__all__ = ["OptimisationResult", "ProjectConfig", "build_representative_year", "optimise_system"]
__version__ = "1.0.0"
