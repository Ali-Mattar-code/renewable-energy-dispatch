"""Reference experiment, evidence tables and publication figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from hybrid_dispatch.config import ProjectConfig
from hybrid_dispatch.economics import financial_model
from hybrid_dispatch.scenarios import (
    compare_technologies,
    resilience_envelope,
    resilience_test,
    sensitivity_analysis,
)
from hybrid_dispatch.serialization import write_json


COLORS = {
    "navy": "#17365D",
    "solar": "#F2C94C",
    "biogas": "#4E9F6D",
    "battery": "#2F80ED",
    "grid": "#9AA5B1",
    "red": "#C84C4C",
}


def _save(figure: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _dashboard(summary: dict[str, object], path: Path) -> None:
    financial = summary["financial"]
    capacities = summary["capacities"]
    annual = summary["annual"]
    resilience = summary["resilience"]
    figure = plt.figure(figsize=(12, 6.6))
    grid = figure.add_gridspec(2, 4, hspace=0.5, wspace=0.35)
    cards = [
        ("Hybrid LCOE", financial["lcoe_aed_per_kwh"], "AED {:.3f}/kWh"),
        ("Renewable fraction", annual["renewable_fraction"], "{:.1%}"),
        ("25-year NPV", financial["npv_aed"], "AED {:,.0f}"),
        ("Outage load served", resilience["outage_load_served_fraction"], "{:.0%}"),
    ]
    for index, (label, value, template) in enumerate(cards):
        axis = figure.add_subplot(grid[0, index])
        axis.axis("off")
        axis.text(
            0.5,
            0.66,
            template.format(value),
            ha="center",
            va="center",
            fontsize=15,
            color=COLORS["navy"],
            fontweight="bold",
        )
        axis.text(0.5, 0.28, label, ha="center", va="center", fontsize=10, color="#536171")
        axis.add_patch(plt.Rectangle((0.02, 0.05), 0.96, 0.9, fill=False, edgecolor="#D8E0EA", linewidth=1.1))

    axis = figure.add_subplot(grid[1, :])
    labels = ["Solar PV", "Battery energy", "Battery power", "Biogas"]
    values = [capacities["pv_kw"], capacities["battery_kwh"], capacities["battery_kw"], capacities["biogas_kw"]]
    units = ["kW", "kWh", "kW", "kW"]
    accents = [COLORS["solar"], COLORS["battery"], "#6AA9FF", COLORS["biogas"]]
    axis.set(xlim=(0, 4), ylim=(0, 1))
    axis.axis("off")
    axis.set_title("Optimised asset sizing", color=COLORS["navy"], fontweight="bold", pad=10)
    for index, (label, value, unit, accent) in enumerate(zip(labels, values, units, accents, strict=True)):
        x = index + 0.08
        axis.add_patch(plt.Rectangle((x, 0.10), 0.84, 0.68, fill=False, edgecolor="#D8E0EA", linewidth=1.1))
        axis.add_patch(plt.Rectangle((x, 0.72), 0.84, 0.06, color=accent, linewidth=0))
        axis.text(
            x + 0.42,
            0.49,
            f"{value:,.0f} {unit}",
            ha="center",
            va="center",
            fontsize=17,
            color=COLORS["navy"],
            fontweight="bold",
        )
        axis.text(x + 0.42, 0.26, label, ha="center", va="center", fontsize=10, color="#536171")
    figure.suptitle(
        "Hybrid Renewable Energy Feasibility — Reference Case",
        fontsize=17,
        color=COLORS["navy"],
        fontweight="bold",
    )
    figure.text(
        0.01,
        0.01,
        "Illustrative assumptions; not an engineering design or investment recommendation.",
        fontsize=8,
        color="#536171",
    )
    _save(figure, path)


def _dispatch(dispatch: pd.DataFrame, path: Path) -> None:
    day = dispatch.loc[(dispatch["month"] == 8) & (dispatch["stress_case"] == 0)].copy()
    hour = day["hour"].to_numpy()
    supply = np.vstack(
        [
            np.maximum(day["pv_generation_kw"].to_numpy() - day["curtailed_kw"].to_numpy(), 0.0),
            day["biogas_generation_kw"].to_numpy(),
            day["battery_discharge_kw"].to_numpy(),
            day["grid_import_kw"].to_numpy(),
        ]
    )
    figure, axis = plt.subplots(figsize=(10.5, 4.8))
    axis.stackplot(
        hour,
        supply,
        labels=["Solar used", "Biogas", "Battery discharge", "Grid import"],
        colors=[COLORS["solar"], COLORS["biogas"], COLORS["battery"], COLORS["grid"]],
        alpha=0.9,
    )
    axis.plot(hour, day["load_kw"], color=COLORS["navy"], linewidth=2.2, label="Load")
    axis.plot(hour, -day["battery_charge_kw"], color="#7655C5", linestyle="--", label="Battery charging")
    axis.set(xlabel="Hour", ylabel="Power (kW)", xticks=np.arange(0, 24, 2))
    axis.set_title("Representative August dispatch", color=COLORS["navy"], fontweight="bold")
    axis.axhline(0, color="#CBD2D9", linewidth=0.8)
    axis.grid(alpha=0.15)
    axis.legend(ncol=3, frameon=False, loc="upper left")
    figure.tight_layout()
    _save(figure, path)


def _scenario_chart(frame: pd.DataFrame, path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    labels = frame["scenario"].str.replace("_", " ").str.title()
    palette = [COLORS["solar"], COLORS["battery"], COLORS["biogas"], COLORS["navy"], COLORS["red"]]
    axes[0].bar(labels, frame["lcoe_aed_per_kwh"], color=palette)
    axes[0].axhline(0.44, color=COLORS["red"], linestyle="--", label="Grid reference")
    axes[0].set(title="Lifecycle cost", ylabel="AED/kWh")
    axes[0].legend(frameon=False)
    axes[1].bar(labels, frame["renewable_fraction"] * 100, color=palette)
    axes[1].set(title="Renewable supply", ylabel="Share of served load (%)", ylim=(0, 105))
    for axis in axes:
        axis.tick_params(axis="x", rotation=18)
        axis.grid(axis="y", alpha=0.16)
        axis.title.set_color(COLORS["navy"])
        axis.title.set_fontweight("bold")
    figure.suptitle("Technology architecture comparison", color=COLORS["navy"], fontweight="bold")
    figure.tight_layout()
    _save(figure, path)


def _sensitivity_chart(frame: pd.DataFrame, path: Path) -> None:
    pivot = frame.pivot(index="biogas_yield_multiplier", columns="grid_tariff_multiplier", values="npv_aed") / 1_000_000
    figure, axis = plt.subplots(figsize=(6.8, 4.6))
    image = axis.imshow(pivot.to_numpy(), cmap="RdYlGn", aspect="auto")
    for row in range(pivot.shape[0]):
        for column in range(pivot.shape[1]):
            value = pivot.iloc[row, column]
            axis.text(column, row, f"{value:.1f}m", ha="center", va="center", color="#1F2933", fontweight="bold")
    axis.set_xticks(range(len(pivot.columns)), [f"{value:.0%}" for value in pivot.columns])
    axis.set_yticks(range(len(pivot.index)), [f"{value:.0%}" for value in pivot.index])
    axis.set(xlabel="Grid tariff multiplier", ylabel="Biogas yield multiplier")
    axis.set_title("25-year NPV sensitivity (AED millions)", color=COLORS["navy"], fontweight="bold")
    figure.colorbar(image, ax=axis, label="AED millions")
    figure.tight_layout()
    _save(figure, path)


def _cashflow_chart(cash_flow: pd.DataFrame, path: Path) -> None:
    cumulative = cash_flow["discounted_cash_flow_aed"].cumsum() / 1_000_000
    figure, axis = plt.subplots(figsize=(8.4, 4.3))
    axis.plot(cash_flow["year"], cumulative, color=COLORS["navy"], linewidth=2.4)
    axis.fill_between(cash_flow["year"], cumulative, 0, where=cumulative >= 0, color=COLORS["biogas"], alpha=0.2)
    axis.fill_between(cash_flow["year"], cumulative, 0, where=cumulative < 0, color=COLORS["red"], alpha=0.16)
    axis.axhline(0, color="#7B8794", linewidth=1)
    axis.set(xlabel="Project year", ylabel="Cumulative discounted cash flow (AED m)")
    axis.set_title("Discounted project cash flow", color=COLORS["navy"], fontweight="bold")
    axis.grid(alpha=0.16)
    figure.tight_layout()
    _save(figure, path)


def _resilience_envelope_chart(frame: pd.DataFrame, path: Path) -> None:
    worst = (
        frame.groupby(["duration_hours", "start_hour"], as_index=False)["served_fraction"]
        .min()
        .pivot(index="duration_hours", columns="start_hour", values="served_fraction")
    )
    values = worst.to_numpy() * 100.0
    lower = min(95.0, float(np.floor(values.min())))
    figure, axis = plt.subplots(figsize=(7.4, 4.5))
    image = axis.imshow(values, cmap="RdYlGn", vmin=lower, vmax=100.0, aspect="auto")
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            axis.text(
                column,
                row,
                f"{values[row, column]:.1f}%",
                ha="center",
                va="center",
                fontweight="bold",
            )
    axis.set_xticks(range(len(worst.columns)), [f"{int(hour):02d}:00" for hour in worst.columns])
    axis.set_yticks(range(len(worst.index)), [f"{int(hours)} h" for hours in worst.index])
    axis.set(xlabel="Outage start", ylabel="Outage duration")
    axis.set_title("Worst seasonal outage-load coverage", color=COLORS["navy"], fontweight="bold")
    figure.colorbar(image, ax=axis, label="Load served (%)")
    figure.tight_layout()
    _save(figure, path)


def run_reference(
    *,
    output_dir: str | Path = "results/reference",
    config: ProjectConfig | None = None,
) -> dict[str, object]:
    config = config or ProjectConfig()
    output = Path(output_dir)
    figures = output / "figures"
    output.mkdir(parents=True, exist_ok=True)

    comparison, results = compare_technologies(config)
    full = results["resilient_full_hybrid"]
    financial, cash_flow = financial_model(full, config)
    sensitivity = sensitivity_analysis(config)
    resilience = resilience_test(full)
    envelope = resilience_envelope(full.capacities, config)
    worst_case = envelope.sort_values(
        ["served_fraction", "duration_hours", "month", "start_hour"],
        ascending=[True, False, True, True],
    ).iloc[0]
    resilience["stress_envelope"] = {
        "cases": len(envelope),
        "months": sorted(int(value) for value in envelope["month"].unique()),
        "start_hours": sorted(int(value) for value in envelope["start_hour"].unique()),
        "durations_hours": sorted(int(value) for value in envelope["duration_hours"].unique()),
        "fully_served_cases": int(envelope["fully_served"].sum()),
        "worst_case_served_fraction": float(worst_case["served_fraction"]),
        "worst_case": {
            "month": int(worst_case["month"]),
            "start_hour": int(worst_case["start_hour"]),
            "duration_hours": int(worst_case["duration_hours"]),
            "unserved_energy_kwh": float(worst_case["unserved_energy_kwh"]),
        },
        "dispatch_assumption": "fixed capacities with perfect-foresight redispatch",
    }

    comparison.to_csv(output / "scenario_comparison.csv", index=False)
    full.dispatch.to_csv(output / "representative_dispatch.csv", index=False)
    sensitivity.to_csv(output / "sensitivity.csv", index=False)
    cash_flow.to_csv(output / "cash_flow.csv", index=False)
    envelope.to_csv(output / "resilience_envelope.csv", index=False)

    summary: dict[str, object] = {
        "evidence_scope": "illustrative feasibility benchmark using representative-day optimisation",
        "not_engineering_or_investment_advice": True,
        "legacy_concept": {
            "load_kwh_per_day": 9_000.0,
            "technologies": ["solar PV", "battery", "camel-manure anaerobic digestion and biogas generation", "grid"],
            "source_files": [
                "Solar for my house.pptx",
                "solar feasibility updated 2015.xls",
                "Solar biogas hybird system.pptx",
                "Solar and Biogas cost.pptx",
            ],
        },
        "assumptions": config.to_dict(),
        "capacities": full.capacities.__dict__,
        "annual": full.annual,
        "financial": financial,
        "resilience": resilience,
        "solver": {
            "method": "SciPy HiGHS linear programming",
            "status": full.solver_status,
            "representative_hours": len(full.dispatch),
        },
    }
    write_json(summary, output / "summary.json")
    _dashboard(summary, figures / "decision_dashboard.png")
    _dispatch(full.dispatch, figures / "dispatch.png")
    _scenario_chart(comparison, figures / "scenario_comparison.png")
    _sensitivity_chart(sensitivity, figures / "sensitivity.png")
    _cashflow_chart(cash_flow, figures / "cash_flow.png")
    _resilience_envelope_chart(envelope, figures / "resilience_envelope.png")
    return summary
